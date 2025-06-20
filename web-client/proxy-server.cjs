const express = require('express');
const cors = require('cors');
const http = require('http');
const https = require('https');

const app = express();
const PORT = 3001;

// Enable CORS for all origins during development
app.use(cors({
  origin: true,
  credentials: true
}));

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Proxy server is running' });
});

// Proxy endpoint for Claude API
app.post('/api/claude', async (req, res) => {
  console.log('Received request to /api/claude');
  console.log('API Key present:', !!req.headers['x-api-key']);
  console.log('Request body:', JSON.stringify(req.body, null, 2));
  
  if (!req.headers['x-api-key']) {
    return res.status(401).json({ error: 'API key is required' });
  }

  const requestBody = JSON.stringify(req.body);
  
  const options = {
    hostname: 'api.anthropic.com',
    port: 443,
    path: '/v1/messages',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(requestBody),
      'x-api-key': req.headers['x-api-key'],
      'anthropic-version': '2023-06-01'
    }
  };

  if (req.body.stream) {
    // Set up SSE headers for streaming
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });

    const request = https.request(options, (response) => {
      console.log('Anthropic API response status:', response.statusCode);
      
      if (response.statusCode !== 200) {
        let errorData = '';
        response.on('data', (chunk) => {
          errorData += chunk;
        });
        response.on('end', () => {
          console.error('Anthropic API error response:', errorData);
          res.status(response.statusCode).end(errorData);
        });
      } else {
        response.on('data', (chunk) => {
          res.write(chunk);
        });

        response.on('end', () => {
          res.end();
        });

        response.on('error', (error) => {
          console.error('Response error:', error);
          res.end();
        });
      }
    });

    request.on('error', (error) => {
      console.error('Request error:', error);
      res.status(500).json({ error: error.message });
    });

    request.write(requestBody);
    request.end();
  } else {
    // Non-streaming request
    const request = https.request(options, (response) => {
      let data = '';

      response.on('data', (chunk) => {
        data += chunk;
      });

      response.on('end', () => {
        try {
          const jsonData = JSON.parse(data);
          res.status(response.statusCode).json(jsonData);
        } catch (error) {
          res.status(500).json({ error: 'Failed to parse response' });
        }
      });
    });

    request.on('error', (error) => {
      console.error('Request error:', error);
      res.status(500).json({ error: error.message });
    });

    request.write(requestBody);
    request.end();
  }
});

app.listen(PORT, () => {
  console.log(`Claude API proxy server running on http://localhost:${PORT}`);
  console.log(`Health check available at http://localhost:${PORT}/health`);
});