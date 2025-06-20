const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// Proxy endpoint for Claude API
app.post('/api/claude', async (req, res) => {
  try {
    // Using dynamic import for node-fetch v3 ESM module
    const fetch = (await import('node-fetch')).default;
    
    console.log('Received request to Claude API proxy');
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
    console.log('Response headers:', response.headers.raw());

    // Handle streaming response
    if (req.body.stream) {
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*'
      });

      // For node-fetch v3, we need to handle the stream differently
      const stream = response.body;
      for await (const chunk of stream) {
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