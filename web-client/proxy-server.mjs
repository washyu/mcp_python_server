import express from 'express';
import cors from 'cors';
import fetch from 'node-fetch';

const app = express();
const PORT = 3001;

// Configure CORS to allow requests from Vite dev server
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:5174', 'http://127.0.0.1:5173'],
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'x-api-key']
}));
app.use(express.json());

// Handle preflight requests
app.options('/api/claude', (req, res) => {
  res.header('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, x-api-key');
  res.header('Access-Control-Max-Age', '86400');
  res.sendStatus(200);
});

// Proxy endpoint for Claude API
app.post('/api/claude', async (req, res) => {
  try {
    console.log('Received request to Claude API proxy');
    console.log('Headers:', req.headers);
    console.log('Request body:', JSON.stringify(req.body, null, 2));
    
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': req.headers['x-api-key'],
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify(req.body)
    });

    console.log('Response status:', response.status);

    // Handle streaming response
    if (req.body.stream) {
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
      });

      // Handle the stream
      for await (const chunk of response.body) {
        res.write(chunk);
      }
      res.end();
    } else {
      const data = await response.json();
      res.json(data);
    }
  } catch (error) {
    console.error('Proxy error:', error);
    console.error('Error stack:', error.stack);
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Claude API proxy server running on http://localhost:${PORT}`);
});