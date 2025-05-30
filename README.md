# Ansible MCP Server

A Model Context Protocol (MCP) server for managing homelab infrastructure with Ansible.

**Platform Support**: Linux-first design optimized for homelab environments (Proxmox, Ubuntu, Debian). Windows users should use WSL2 for development.

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

```bash
# Run the MCP server with WebSocket transport (default)
uv run python main.py

# Or with specific port
uv run python main.py --port 8765

# For Claude Desktop compatibility (stdio transport)
uv run python main.py --transport stdio
```

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

The server supports both:
- **WebSocket transport** (default) - Better for testing and web integrations
- **stdio transport** - For Claude Desktop compatibility

Both transports implement the same MCP protocol (JSON-RPC 2.0).

## Development

This is a Python-based MCP server that will provide tools for:
- Infrastructure discovery (Proxmox, bare metal, network devices)
- Ansible playbook execution
- Template management
- Standard Operating Procedures (SOPs)
- Security scanning