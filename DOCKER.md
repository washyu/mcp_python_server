# Docker Setup for Universal Homelab MCP Server

Complete Docker Compose setup for running the MCP server and web client locally.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Ollama running locally (for AI features)

### Start Everything
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Access Points
- **Web Client**: http://localhost:5173
- **MCP Server API**: http://localhost:3000
- **MCP Health Check**: http://localhost:3000/health

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │    │   MCP Server     │    │   Ollama        │
│   (Nginx)       │◄──►│   (Python)       │◄──►│   (Local)       │
│   Port 5173     │    │   Port 3000      │    │   Port 11434    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 Services

### MCP Server (`mcp-server`)
- **Image**: Built from local Dockerfile
- **Port**: 3000
- **Features**: 
  - HTTP transport for MCP protocol
  - 52+ homelab management tools
  - Proxmox, LXD, Ansible integration
  - Health checks enabled

### Web Client (`web-client`)
- **Image**: Built from Nginx + React/TypeScript
- **Port**: 5173 (mapped to container port 80)
- **Features**:
  - HTTP transport integration
  - Claude & Ollama support
  - Real-time tool execution
  - Proxied API calls to MCP server

## 🛠️ Development

### Build and Test
```bash
# Rebuild specific service
docker-compose build mcp-server
docker-compose build web-client

# Start with build
docker-compose up --build

# View service logs
docker-compose logs mcp-server
docker-compose logs web-client
```

### Environment Configuration
Copy `.env.example` to `.env` and configure:
```env
# Core settings
DEBUG=true
OLLAMA_HOST=http://host.docker.internal:11434

# Proxmox (optional)
PROXMOX_HOST=192.168.10.200
PROXMOX_USERNAME=root@pam
PROXMOX_PASSWORD=your_password
```

### Volumes
- `./inventory` → `/app/inventory` (persistent MCP data)
- `./.env` → `/app/.env` (configuration)

## 🔗 API Integration

### Test MCP Connection
```bash
# Test tools list
curl -X POST http://localhost:3000/mcp/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-session" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}'
```

### Web Client Integration
The web client automatically connects to the MCP server through nginx proxy:
- Client requests: `http://localhost:5173/mcp/v1/messages`
- Proxied to: `http://mcp-server:3000/mcp/v1/messages`

## 🐛 Troubleshooting

### Check Service Status
```bash
docker-compose ps
docker-compose logs --tail=50 mcp-server
```

### Common Issues
1. **Port Conflicts**: Ensure ports 3000 and 5173 are available
2. **Ollama Connection**: Verify Ollama is running on host
3. **Permissions**: Check `.env` file permissions and content

### Health Checks
```bash
# MCP Server health
curl http://localhost:3000/health

# Web client health  
curl http://localhost:5173/
```

## 🚀 Production Deployment

For production, consider:
1. Using proper secrets management
2. Adding SSL/TLS termination
3. Using environment-specific compose files
4. Setting up proper logging and monitoring

## 🔄 Optional: Include Ollama

To run Ollama in Docker (uncomment in docker-compose.yml):
```bash
# Uncomment ollama service in docker-compose.yml
docker-compose up -d ollama

# Pull a model
docker-compose exec ollama ollama pull llama3.2:3b
```