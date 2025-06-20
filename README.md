# Universal Homelab MCP Server

A Model Context Protocol (MCP) server that provides AI agents with intelligent homelab infrastructure management capabilities.

**Platform Support**: Linux-first design optimized for homelab environments (Proxmox, Ubuntu, Debian). Windows users should use WSL2 for development.

## 📚 Documentation

Our documentation is organized into logical categories:

- **[📖 User Guides](docs/user-guides/)** - Getting started and usage guides
- **[⚙️ Setup & Installation](docs/setup/)** - Installation and testing procedures  
- **[🏗️ Architecture](docs/architecture/)** - Technical design and implementation
- **[✨ Features](docs/features/)** - Core functionality documentation
- **[🤖 AI Context](docs/context/)** - AI context system and examples
- **[📋 Project Management](docs/project/)** - Status, roadmap, and strategy

**New to the project?** Start with the [Core Overview](docs/user-guides/README_MCP_CORE.md).

## Quick Start

### Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Prerequisites for Local Testing

1. **Install Ollama** (for local LLM):
   
   **On Linux/macOS:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama serve
   ollama pull llama3.2:3b
   ```
   
   **On Windows (with WSL development):**
   - Install Ollama on Windows from https://ollama.com/download
   - Start Ollama on Windows (it runs in the system tray)
   - Pull a model in Windows: `ollama pull llama3.2:3b`
   
   **For WSL users:**
   ```bash
   # Edit .env file and set OLLAMA_HOST to your Windows IP:
   # OLLAMA_HOST=http://192.168.x.x:11434
   
   # Or run our setup script to help find the right address
   ./setup_wsl.sh
   ```
   
   See [WSL_SETUP.md](./WSL_SETUP.md) for detailed WSL configuration instructions.

### Running the Server

The MCP server supports multiple transport modes:

```bash
# Run with interactive chat interface (default)
uv run python main.py

# Stdio transport (for Claude Desktop)
uv run python main.py --mode stdio

# WebSocket transport
uv run python main.py --mode websocket --port 8765

# Streamable HTTP transport (NEW)
uv run python main.py --mode http --host localhost --port 3000

# Server-Sent Events (SSE) transport (NEW)
uv run python main.py --mode sse --host localhost --port 3000
```

See [HTTP_TRANSPORT.md](docs/architecture/HTTP_TRANSPORT.md) for details on the new HTTP transport options.

## 🌐 Web Client

A React/TypeScript web client that demonstrates the HTTP transport capabilities:

```bash
# Start the MCP server with HTTP transport
uv run python main.py --mode http --port 3000

# In another terminal, start the web client
cd web-client
npm install
npm run dev
```

**Features:**
- **HTTP Transport Integration** - Uses the new streamable HTTP transport
- **Claude & Ollama Support** - Multiple LLM provider support
- **Real-time Tool Execution** - Execute all 52+ MCP tools via web interface
- **Server Context Management** - Switch between different homelab servers
- **Streaming Responses** - Real-time chat with tool integration

Open http://localhost:5173 to access the web interface.

See [web-client/CLAUDE.md](web-client/CLAUDE.md) for detailed setup and usage instructions.

## 🐳 Docker Setup (Recommended)

The easiest way to run the complete stack locally is using Docker:

```bash
# Start everything with Docker Compose
docker-compose up -d

# Access the services
# - Web Client: http://localhost:5173
# - MCP Server: http://localhost:3000

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Benefits:**
- No need to install Python, Node.js, or manage dependencies
- Isolated environment with proper networking
- Production-ready configuration
- Automatic service dependencies and health checks

See [DOCKER.md](DOCKER.md) for complete Docker setup instructions.

### Testing with Local AI Agent

We provide a complete local testing setup using Ollama:

1. **Simple Integration Test**:
   ```bash
   # Verify everything is working
   python simple_test.py
   ```

2. **Interactive AI Agent**:
   ```bash
   # Start the MCP server (in one terminal)
   uv run python main.py
   
   # Run the interactive agent (in another terminal)
   uv run python -m src.agents.websocket_agent
   ```

   This creates a chat interface where you can ask the AI to use the MCP tools.

3. **Protocol Test** (shows raw MCP messages):
   ```bash
   # View the test protocol messages
   python test_server.py
   ```

## MCP Tools

Currently implemented:
- `hello_world` - A simple tool that returns "Hello, World!"

## Testing Example

When running `test_agent.py`, you can interact with the AI:

```
You: Please call the hello world tool
AI: I'll call the hello_world tool for you.

Calling tool: hello_world
Tool result: Hello, World!
```

## Configuration

All configuration is managed through the `.env` file. Key settings include:

- `OLLAMA_HOST` - URL for Ollama API (important for WSL users)
- `OLLAMA_MODEL` - Default AI model to use
- `PROXMOX_*` - Proxmox server credentials (for future features)
- `ANSIBLE_*` - Ansible configuration options
- `DEBUG` - Enable debug logging

See `.env.example` for all available options.

## Project Structure

```
mcp_python_server/
├── main.py              # Entry point
├── config.py            # Configuration management
├── src/
│   ├── server/         # MCP server implementations
│   │   ├── server.py   # stdio transport
│   │   └── websocket_server.py
│   ├── client/         # MCP client libraries
│   │   └── websocket_client.py
│   └── agents/         # AI agent implementations
│       └── websocket_agent.py
├── tests/              # Test files
├── examples/           # Example implementations
├── scripts/            # Utility scripts
├── docs/               # Documentation
├── tools/              # MCP tools (future)
└── utils/              # Utilities (future)
```

The server supports multiple transports:
- **WebSocket transport** - Real-time bidirectional communication
- **stdio transport** - For Claude Desktop compatibility
- **HTTP transport** - RESTful API with streaming support (NEW)
- **SSE transport** - Server-Sent Events for real-time updates (NEW)

All transports implement the same MCP protocol (JSON-RPC 2.0).

## Development

This is a Python-based MCP server that will provide tools for:
- Infrastructure discovery (Proxmox, bare metal, network devices)
- Ansible playbook execution
- Template management
- Standard Operating Procedures (SOPs)
- Security scanning