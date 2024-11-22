const express = require('express');
const { MongoClient } = require('mongodb');
const axios = require('axios');
const async = require('async'); 
const { v4: uuidv4 } = require('uuid'); 
const client = require('prom-client'); 

const app = express();
app.use(express.json());

// Prometheus Metrics
const collectDefaultMetrics = client.collectDefaultMetrics;
collectDefaultMetrics();

const requestCounter = new client.Counter({
  name: 'stock_prediction_requests_total',
  help: 'Total number of requests',
  labelNames: ['endpoint', 'method', 'status']
});

const requestHistogram = new client.Histogram({
  name: 'stock_prediction_request_latency_seconds',
  help: 'Request latency in seconds',
  labelNames: ['endpoint', 'method']
});

// MongoDB Configuration
const mongoClient = new MongoClient('mongodb://mongo:27017', { useUnifiedTopology: true });
let stockCollection;
let predictionCollection;
let transactionHistoryCollection;

mongoClient.connect().then((client) => {
  const db = client.db('stock_database');
  stockCollection = db.collection('stocks');
  predictionCollection = db.collection('predictions');
  transactionHistoryCollection = db.collection('transaction_history');
  console.log('Connected to MongoDB');
}).catch(err => {
  console.error('Failed to connect to MongoDB', err);
});

// Alpha Vantage API Configuration
const API_KEY = '3FPIPAPG6QSFPTQW'; 
const BASE_URL = 'https://www.alphavantage.co/query';

// Task queue with concurrency limit
const taskQueue = async.queue(async (task) => task(), 5); 

async function fetchRealStockData(symbol) {
  const params = {
    function: 'TIME_SERIES_INTRADAY',
    symbol,
    interval: '5min',
    apikey: API_KEY,
  };
  const response = await axios.get(BASE_URL, { params });
  const data = response.data;

  if (data['Time Series (5min)']) {
    const lastRefreshed = Object.keys(data['Time Series (5min)'])[0];
    const stockInfo = data['Time Series (5min)'][lastRefreshed];
    const stockData = {
      symbol,
      price: parseFloat(stockInfo['1. open']),
      currency: 'USD',
      timestamp: lastRefreshed,
    };
    await stockCollection.insertOne(stockData); // Cache stock data in MongoDB
    return stockData;
  } else {
    throw new Error('Failed to fetch stock data from Alpha Vantage');
  }
}

async function getStockData(symbol) {
  const cachedData = await stockCollection.findOne({ symbol }, { sort: { timestamp: -1 } });
  if (cachedData) {
    return cachedData;
  } else {
    return await fetchRealStockData(symbol);
  }
}

// Middleware to measure metrics
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const latency = (Date.now() - start) / 1000;
    const endpoint = req.path;
    const method = req.method;
    const status = res.statusCode.toString();

    requestCounter.labels(endpoint, method, status).inc();
    requestHistogram.labels(endpoint, method).observe(latency);
  });
  next();
});

// ----------- Endpoints -----------

app.get('/status', (req, res) => {
  res.json({ message: 'Stock Prediction Service is running!' });
});

app.get('/api/stocks/:symbol/details', async (req, res) => {
  const { symbol } = req.params;
  try {
    const stockData = await getStockData(symbol);
    res.json({
      id: uuidv4(),
      symbol: stockData.symbol,
      price: stockData.price,
      currency: stockData.currency,
      timestamp: stockData.timestamp,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});


app.get('/api/predict/:symbol', async (req, res) => {
  const { symbol } = req.params;
  try {
    const stockData = await getStockData(symbol);
    const predictionValue = Math.random() * 2 - 1; 
    const action = predictionValue > 0 ? 'buy' : 'sell'; // "buy" if positive, else "sell"

    const prediction = {
      id: uuidv4(),
      symbol: stockData.symbol,
      prediction: predictionValue,
      action,
      timestamp: new Date().toISOString(),
    };

    await predictionCollection.insertOne(prediction); 
    res.json(prediction);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/transactions/store', async (req, res) => {
  const transactionData = req.body;
  try {
    transactionData.id = uuidv4(); 
    await transactionHistoryCollection.insertOne(transactionData);
    res.status(201).json({ message: 'Transaction stored successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to store transaction data' });
  }
});



// ----------- Prometheus Metrics Endpoint -----------

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

const PORT = 5000;
app.listen(PORT, () => {
  console.log(`Stock Prediction Service is running on port ${PORT}`);
});
