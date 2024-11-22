// const express = require('express');
// const { Pool } = require('pg'); 
// const redis = require('redis');
// const { v4: uuidv4 } = require('uuid'); 
// const async = require('async'); 
// const jwt = require('jsonwebtoken');
// const axios = require('axios');
// const WebSocket = require('ws');
// const app = express();

// const API_GATEWAY_URL = process.env.API_GATEWAY_URL || "http://api-gateway:3000";
// const SECRET_KEY = process.env.SECRET_KEY || 'your_secret_key';

// const pool = new Pool({
//   user: process.env.POSTGRES_USER,
//   host: 'postgres',
//   database: process.env.POSTGRES_DB,
//   password: process.env.POSTGRES_PASSWORD,
//   port: 5432,
// });

// const redisClient = redis.createClient({ url: 'redis://redis:6379' });
// redisClient.connect(); 

// app.use(express.json());

// function hashPassword(password) {
//   return require('crypto').createHash('sha256').update(password).digest('hex');
// }

// async function verifyToken(token) {
//   try {
//     const decoded = jwt.verify(token, SECRET_KEY);
//     const tokenKey = `jwt_${decoded.email}`;
//     const storedToken = await redisClient.get(tokenKey);
//     return storedToken && storedToken === token ? decoded : null;
//   } catch (err) {
//     return null;
//   }
// }

// // Concurrency control
// const taskQueue = async.queue(async (task) => task(), 2);

// app.post('/api/users/register', async (req, res) => {
//   const { name, email, password } = req.body;

//   if (!name || !email || !password) {
//     return res.status(400).json({ error: "Missing required fields" });
//   }

//   const hashedPassword = hashPassword(password);

//   try {
//     await pool.query("INSERT INTO users (name, email, password) VALUES ($1, $2, $3)", [
//       name,
//       email,
//       hashedPassword,
//     ]);
//     res.status(201).json({ message: "User registered successfully" });
//   } catch (err) {
//     console.error(err.message);
//     res.status(500).json({ error: "Failed to register user" });
//   }
// });

// app.post('/api/users/login', async (req, res) => {
//   const { email, password } = req.body;
//   const hashedPassword = hashPassword(password);

//   try {
//     const result = await pool.query("SELECT * FROM users WHERE email = $1 AND password = $2", [
//       email,
//       hashedPassword,
//     ]);

//     if (result.rows.length === 0) {
//       return res.status(401).json({ error: "Invalid email or password" });
//     }

//     const token = jwt.sign({ email }, SECRET_KEY, { expiresIn: '1h' });
//     const tokenKey = `jwt_${email}`;
//     await redisClient.setEx(tokenKey, 3600, token); // Token expires in 1 hour

//     res.json({ token });
//   } catch (err) {
//     console.error(err.message);
//     res.status(500).json({ error: "Failed to log in user" });
//   }
// });

// app.get('/api/users/profile', async (req, res) => {
//   const token = req.headers.authorization;

//   if (!token) {
//     return res.status(401).json({ error: "Token missing" });
//   }

//   const decoded = await verifyToken(token);
//   if (!decoded) {
//     return res.status(401).json({ error: "Invalid or expired token" });
//   }

//   try {
//     const result = await pool.query("SELECT name, email FROM users WHERE email = $1", [decoded.email]);

//     if (result.rows.length === 0) {
//       return res.status(404).json({ error: "User not found" });
//     }

//     res.json(result.rows[0]);
//   } catch (err) {
//     console.error(err.message);
//     res.status(500).json({ error: "Failed to fetch user profile" });
//   }
// });

// app.post('/api/users/profile/update', async (req, res) => {
//   const token = req.headers.authorization;
//   const { name } = req.body;

//   if (!token || !name) {
//     return res.status(400).json({ error: "Token or name missing" });
//   }

//   const decoded = await verifyToken(token);
//   if (!decoded) {
//     return res.status(401).json({ error: "Invalid or expired token" });
//   }

//   try {
//     await pool.query("UPDATE users SET name = $1 WHERE email = $2", [name, decoded.email]);
//     res.json({ message: "Profile updated successfully" });
//   } catch (err) {
//     console.error(err.message);
//     res.status(500).json({ error: "Failed to update profile" });
//   }
// });

// app.post('/api/users/buy', async (req, res) => {
//   const transactionData = { ...req.body, operation: "buy" };

//   try {
//     const response = await axios.post(`${API_GATEWAY_URL}/api/transactions/store`, transactionData);
//     res.status(response.status).json(response.data);
//   } catch (err) {
//     console.error(err.message);
//     res.status(500).json({ error: "Failed to buy stock" });
//   }
// });

// app.post('/api/users/sell', async (req, res) => {
//   const transactionData = { ...req.body, operation: "sell" };

//   try {
//     const response = await axios.post(`${API_GATEWAY_URL}/api/transactions/store`, transactionData);
//     res.status(response.status).json(response.data);
//   } catch (err) {
//     console.error(err.message);
//     res.status(500).json({ error: "Failed to sell stock" });
//   }
// });

// app.get('/status', (req, res) => {
//   res.json({ message: "User Management Service is running!" });
// });

// app.listen(5002, () => {
//   console.log("User Management Service is running on port 5002");
// });

// user-management-service/index.js

const express = require('express');
const { Pool } = require('pg'); 
const redis = require('redis');
const { v4: uuidv4 } = require('uuid'); 
const async = require('async'); 
const jwt = require('jsonwebtoken');
const axios = require('axios');
const WebSocket = require('ws');
const client = require('prom-client'); // Import prom-client

const app = express();

// Prometheus Metrics
const collectDefaultMetrics = client.collectDefaultMetrics;
collectDefaultMetrics();

const requestCounter = new client.Counter({
  name: 'user_management_requests_total',
  help: 'Total number of requests',
  labelNames: ['endpoint', 'method', 'status']
});

const requestHistogram = new client.Histogram({
  name: 'user_management_request_latency_seconds',
  help: 'Request latency in seconds',
  labelNames: ['endpoint', 'method']
});

const API_GATEWAY_URL = process.env.API_GATEWAY_URL || "http://api-gateway:3000";
const SECRET_KEY = process.env.SECRET_KEY || 'your_secret_key';

const pool = new Pool({
  user: process.env.POSTGRES_USER,
  host: 'postgres',
  database: process.env.POSTGRES_DB,
  password: process.env.POSTGRES_PASSWORD,
  port: 5432,
});

const redisClient = redis.createClient({ url: 'redis://redis:6379' });
redisClient.connect().catch(err => {
  console.error('Redis connection error:', err);
});

app.use(express.json());

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

function hashPassword(password) {
  return require('crypto').createHash('sha256').update(password).digest('hex');
}

async function verifyToken(token) {
  try {
    const decoded = jwt.verify(token, SECRET_KEY);
    const tokenKey = `jwt_${decoded.email}`;
    const storedToken = await redisClient.get(tokenKey);
    return storedToken && storedToken === token ? decoded : null;
  } catch (err) {
    return null;
  }
}

// Concurrency control
const taskQueue = async.queue(async (task) => task(), 2);

app.post('/api/users/register', async (req, res) => {
  const { name, email, password } = req.body;

  if (!name || !email || !password) {
    requestCounter.labels('/api/users/register', 'POST', '400').inc();
    return res.status(400).json({ error: "Missing required fields" });
  }

  const hashedPassword = hashPassword(password);

  try {
    await pool.query("INSERT INTO users (name, email, password) VALUES ($1, $2, $3)", [
      name,
      email,
      hashedPassword,
    ]);
    requestCounter.labels('/api/users/register', 'POST', '201').inc();
    res.status(201).json({ message: "User registered successfully" });
  } catch (err) {
    console.error(err.message);
    requestCounter.labels('/api/users/register', 'POST', '500').inc();
    res.status(500).json({ error: "Failed to register user" });
  }
});

app.post('/api/users/login', async (req, res) => {
  const { email, password } = req.body;
  const hashedPassword = hashPassword(password);

  try {
    const result = await pool.query("SELECT * FROM users WHERE email = $1 AND password = $2", [
      email,
      hashedPassword,
    ]);

    if (result.rows.length === 0) {
      requestCounter.labels('/api/users/login', 'POST', '401').inc();
      return res.status(401).json({ error: "Invalid email or password" });
    }

    const token = jwt.sign({ email }, SECRET_KEY, { expiresIn: '1h' });
    const tokenKey = `jwt_${email}`;
    await redisClient.setEx(tokenKey, 3600, token); // Token expires in 1 hour

    requestCounter.labels('/api/users/login', 'POST', '200').inc();
    res.json({ token });
  } catch (err) {
    console.error(err.message);
    requestCounter.labels('/api/users/login', 'POST', '500').inc();
    res.status(500).json({ error: "Failed to log in user" });
  }
});

app.get('/api/users/profile', async (req, res) => {
  const token = req.headers.authorization;

  if (!token) {
    requestCounter.labels('/api/users/profile', 'GET', '401').inc();
    return res.status(401).json({ error: "Token missing" });
  }

  const decoded = await verifyToken(token);
  if (!decoded) {
    requestCounter.labels('/api/users/profile', 'GET', '401').inc();
    return res.status(401).json({ error: "Invalid or expired token" });
  }

  try {
    const result = await pool.query("SELECT name, email FROM users WHERE email = $1", [decoded.email]);

    if (result.rows.length === 0) {
      requestCounter.labels('/api/users/profile', 'GET', '404').inc();
      return res.status(404).json({ error: "User not found" });
    }

    requestCounter.labels('/api/users/profile', 'GET', '200').inc();
    res.json(result.rows[0]);
  } catch (err) {
    console.error(err.message);
    requestCounter.labels('/api/users/profile', 'GET', '500').inc();
    res.status(500).json({ error: "Failed to fetch user profile" });
  }
});

app.post('/api/users/profile/update', async (req, res) => {
  const token = req.headers.authorization;
  const { name } = req.body;

  if (!token || !name) {
    requestCounter.labels('/api/users/profile/update', 'POST', '400').inc();
    return res.status(400).json({ error: "Token or name missing" });
  }

  const decoded = await verifyToken(token);
  if (!decoded) {
    requestCounter.labels('/api/users/profile/update', 'POST', '401').inc();
    return res.status(401).json({ error: "Invalid or expired token" });
  }

  try {
    await pool.query("UPDATE users SET name = $1 WHERE email = $2", [name, decoded.email]);
    requestCounter.labels('/api/users/profile/update', 'POST', '200').inc();
    res.json({ message: "Profile updated successfully" });
  } catch (err) {
    console.error(err.message);
    requestCounter.labels('/api/users/profile/update', 'POST', '500').inc();
    res.status(500).json({ error: "Failed to update profile" });
  }
});

app.post('/api/users/buy', async (req, res) => {
  const transactionData = { ...req.body, operation: "buy" };

  try {
    const response = await axios.post(`${API_GATEWAY_URL}/api/transactions/store`, transactionData);
    requestCounter.labels('/api/users/buy', 'POST', response.status.toString()).inc();
    res.status(response.status).json(response.data);
  } catch (err) {
    console.error(err.message);
    requestCounter.labels('/api/users/buy', 'POST', '500').inc();
    res.status(500).json({ error: "Failed to buy stock" });
  }
});

app.post('/api/users/sell', async (req, res) => {
  const transactionData = { ...req.body, operation: "sell" };

  try {
    const response = await axios.post(`${API_GATEWAY_URL}/api/transactions/store`, transactionData);
    requestCounter.labels('/api/users/sell', 'POST', response.status.toString()).inc();
    res.status(response.status).json(response.data);
  } catch (err) {
    console.error(err.message);
    requestCounter.labels('/api/users/sell', 'POST', '500').inc();
    res.status(500).json({ error: "Failed to sell stock" });
  }
});

// ----------- Prometheus Metrics Endpoint -----------

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

app.get('/status', (req, res) => {
  res.json({ message: "User Management Service is running!" });
});

app.listen(5002, () => {
  console.log("User Management Service is running on port 5002");
});
