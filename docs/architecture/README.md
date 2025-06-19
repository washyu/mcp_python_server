# Architecture Documentation

This section contains technical architecture and design documentation for developers and system architects.

## 🌐 Communication & Transport

### [HTTP Transport](HTTP_TRANSPORT.md)
**NEW!** Streamable HTTP transport protocol for universal MCP server access. Covers:
- REST API endpoints and usage
- Session management and authentication
- Integration examples (web apps, CI/CD, mobile)
- Benefits over WebSocket transport

## 📦 Container Integration

### [LXD Integration Design](LXD_INTEGRATION_DESIGN.md)
Architecture and design patterns for LXD container platform integration.

### [LXD MCP Tool Specifications](LXD_MCP_TOOL_SPECIFICATIONS.md)
Detailed specifications for all LXD-related MCP tools and their implementations.

## 🏗️ Design Principles

The architecture follows these key principles:

1. **Provider Agnostic** - Works with any infrastructure (Proxmox, AWS, GCP, etc.)
2. **Transport Flexible** - Supports multiple communication methods
3. **AI-First Design** - Optimized for AI agent interactions
4. **Modular Components** - Each tool and feature is independently usable
5. **Security Focused** - Secure credential management and access control

## 🔄 Data Flow

```
User/AI → Transport Layer → MCP Server → Tool Handlers → Infrastructure APIs
   ↓           ↓               ↓            ↓              ↓
Input     HTTP/WebSocket   Tool Router   Proxmox/LXD    Results
```

## 🔗 Related Documentation

- [Features](../features/) - What the architecture enables
- [Project](../project/) - Development roadmap and status
- [Setup](../setup/) - Implementation and testing details