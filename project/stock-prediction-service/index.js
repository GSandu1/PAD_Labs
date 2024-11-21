const express = require('express');
const { MongoClient } = require('mongodb');
const axios = require('axios');
const async = require('async'); // Import async for concurrency control
const { v4: uuidv4 } = require('uuid'); // For generating unique transaction IDs

const app = express();
app.use(express.json());


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
});

// Alpha Vantage API Configuration
const API_KEY = '3FPIPAPG6QSFPTQW'; 
const BASE_URL = 'https://www.alphavantage.co/query';

//G7AVN9FRKTQCFPCW
//N59FA06OB6979AGJ
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

const PORT = 5000;
app.listen(PORT, () => {
  console.log(`Stock Prediction Service is running on port ${PORT}`);
});
