# Minimal MCP Hello World Setup

A minimal Model Context Protocol (MCP) implementation with a Hello World tool integrated with Ollama AI and a React web client.

## 🚀 Quick Start

1. **Start the services:**
   ```bash
   docker-compose -f docker-compose.minimal.yml up -d
   ```

2. **Start the React web client:**
   ```bash
   cd web-client/minimal-chat
   npm install
   npm run dev
   ```

3. **Open your browser:**
   - Navigate to http://localhost:5175
   - Type "hello" to trigger the MCP tool
   - Watch Ollama AI respond with the MCP tool output

## 🏗️ Architecture

- **🤖 Ollama (Docker)**: `localhost:11434` with llama3 model
- **🔧 MCP Server**: `localhost:3001` with hello_world tool
- **💻 React Web Client**: `localhost:5175` with proxy to MCP server

## 🔧 Components

### MCP Server (`chat_server_direct.py`)
- Direct implementation of `hello_world_tool()` function
- Starlette web server with streaming chat endpoint
- Detects "hello" in messages and calls MCP tool
- Integrates tool response into Ollama prompt

### Docker Setup (`docker-compose.minimal.yml`)
- **ollama**: Runs ollama/ollama with llama3 model
- **mcp-minimal**: Python server with MCP integration
- **Networking**: Bridge network for service communication

### React Web Client (`web-client/minimal-chat/`)
- TypeScript React app with streaming chat interface
- Vite proxy configuration for MCP server integration
- Server-Sent Events (SSE) for real-time responses
- Violet chat bubbles for AI responses

## 🧪 Test the Flow

1. User types: "hello there!"
2. MCP server detects "hello" → calls `hello_world_tool()`
3. Tool returns: "Hello from the Homelab MCP server"
4. Ollama AI receives prompt with tool response
5. AI generates response mentioning the MCP tool output
6. Web client displays streaming response

## 📁 Project Structure

```
mcp_python_server/
├── chat_server_direct.py           # MCP server with hello_world tool
├── docker-compose.minimal.yml      # Docker services
├── pyproject.toml                  # Python dependencies
└── web-client/minimal-chat/        # React web client
    ├── src/App.tsx                 # Main React component
    ├── src/App.css                 # Styling (violet bubbles)
    └── vite.config.ts              # Proxy configuration
```

## ✅ Working Features

- ✅ **MCP Tool Integration**: hello_world tool called automatically
- ✅ **Ollama AI Integration**: AI uses tool output in responses  
- ✅ **Streaming Responses**: Real-time chat with SSE
- ✅ **Docker Deployment**: Containerized Ollama and MCP server
- ✅ **Web Interface**: Clean React UI with proper styling
- ✅ **End-to-End Flow**: Complete Ollama ↔ MCP ↔ Web Client flow

Perfect for learning MCP concepts and building more complex integrations!