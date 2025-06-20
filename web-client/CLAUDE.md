# MCP Web Client

This is a React/TypeScript web client for the Universal Homelab MCP Server that demonstrates the new **HTTP transport** capabilities.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server (runs on http://localhost:5173)
npm run dev

# Start MCP server with HTTP transport (in another terminal)
cd .. && python main.py --mode http --port 3000
```

## 🌟 Features

- **HTTP Transport**: Uses the new streamable HTTP transport instead of WebSocket
- **Claude Integration**: Connect to Claude API for AI responses
- **Ollama Support**: Local LLM integration (planned)
- **MCP Tool Integration**: Direct access to all 52+ MCP tools
- **Real-time Chat**: Streaming responses with tool execution
- **Server Context**: Switch between different homelab servers

## 🏗️ Architecture

### HTTP-Based MCP Client
- **Session Management**: Uses UUID-based sessions with X-Session-ID headers
- **Tool Discovery**: Automatically fetches available tools on connection
- **Streaming Support**: Real-time tool execution with streaming responses
- **Error Handling**: Comprehensive error handling for HTTP requests

### Chat Interface
- **Markdown Rendering**: Full markdown support with syntax highlighting
- **Tool Integration**: Tools are automatically suggested and executed
- **Message History**: Persistent chat history with storage
- **Settings Modal**: Configure API keys and preferences

## 🔧 Configuration

### MCP Server Connection
The client connects to the MCP server via HTTP:
- **Default URL**: `http://localhost:3000`
- **Endpoint**: `/mcp/v1/messages`
- **Transport**: HTTP with session management

### LLM Providers
- **Claude**: Requires API key, supports all Claude models
- **Ollama**: Local deployment, no API key required

## 📁 Project Structure

```
src/
├── mcp/
│   └── client.ts          # HTTP-based MCP client
├── api/
│   └── claude.ts          # Claude API integration
├── ui/
│   ├── ChatInput.ts       # Chat input component
│   └── ChatMessage.ts     # Message rendering with markdown
├── types/
│   └── index.ts           # TypeScript type definitions
├── utils/
│   └── storage.ts         # Local storage utilities
├── ChatApp.ts             # Main application logic
└── main.ts                # Application entry point
```

## 🌐 HTTP Transport Benefits

1. **Universal Compatibility**: Works with any HTTP client
2. **Web Integration**: Easy integration with web applications
3. **Firewall Friendly**: Uses standard HTTP ports
4. **Scalable**: Can be deployed behind load balancers
5. **Stateless**: Better for cloud deployment

## 🛠️ Development

### Code Quality
```bash
# Format code with Prettier
npx prettier --write .

# Check TypeScript types
npx tsc --noEmit

# Build for production
npm run build
```

### Testing the HTTP Transport
1. Start the MCP server: `python main.py --mode http --port 3000`
2. Start the web client: `npm run dev`
3. Open http://localhost:5173
4. Select a server and connect
5. Chat with AI and watch tool execution

## 🔗 Integration Examples

### Tool Execution
The client can execute any MCP tool:
```typescript
// List available tools
const tools = mcpClient.getTools();

// Execute a tool
const result = await mcpClient.callTool('list_nodes', {});

// Execute with streaming
await mcpClient.executeToolWithStream('create_vm', 
  { name: 'web-server', cores: 4 },
  (chunk) => console.log(chunk)
);
```

### AI + MCP Integration
When connected to an MCP server, the AI automatically has access to infrastructure tools and can:
- List and manage VMs
- Create and configure containers
- Deploy services
- Monitor resources
- Execute complex homelab operations

## 🎯 Use Cases

- **Homelab Management**: Web interface for infrastructure automation
- **Development**: Test and debug MCP tools via web interface  
- **Demonstrations**: Show HTTP transport capabilities
- **Integration**: Example for building web apps with MCP
- **Mobile**: Foundation for mobile app development

This web client showcases how the new HTTP transport makes MCP servers accessible to any web application, mobile app, or HTTP-capable client!