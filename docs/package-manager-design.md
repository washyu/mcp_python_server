# Homelab MCP Package Manager Design

## Overview

Transform the current MCP service installer into a Scoop-like package manager for homelab services, enabling:
- GitHub-based package repositories
- Simple `mcp install pihole` style commands
- Version management and updates
- Dependency resolution
- Multiple package sources/registries

## Core Concepts

### 1. Package Manifest Format
Similar to Scoop's JSON manifests, but using YAML for consistency with current MCP:

```yaml
# pihole/manifest.yaml
name: pihole
version: "2024.07.0"
description: "Network-wide ad blocker"
homepage: https://pi-hole.net
license: EUPL-1.2
source:
  url: https://github.com/pi-hole/docker-pi-hole/releases/download/2024.07.0/docker-compose.yml
  hash: sha256:abc123...
dependencies:
  - docker
  - docker-compose
requirements:
  ports: [80, 53, 443, 67]
  memory_gb: 1
  disk_gb: 2
install:
  method: docker-compose
  compose_file: docker-compose.yml
  env:
    WEBPASSWORD: "{{generated_password}}"
    TZ: "{{user_timezone}}"
post_install:
  - message: "Access Pi-hole at http://{{hostname}}/admin"
  - message: "Default password: {{generated_password}}"
```

### 2. Repository Structure
```
homelab-packages/
├── README.md
├── registry.json          # Package index
├── packages/
│   ├── pihole/
│   │   ├── manifest.yaml
│   │   ├── versions/
│   │   │   ├── 2024.07.0.yaml
│   │   │   └── 2024.06.0.yaml
│   │   └── assets/
│   │       └── docker-compose.yml
│   ├── jellyfin/
│   │   └── manifest.yaml
│   └── homeassistant/
│       └── manifest.yaml
```

### 3. Package Sources
Support multiple package sources:
- Official: `https://github.com/homelab-mcp/packages`
- Community: `https://github.com/community/homelab-packages`
- Private: `https://github.com/myorg/internal-packages`

## Implementation Plan

### Phase 1: Core Package Manager
1. **Package Repository Client**
   - Fetch manifests from GitHub
   - Cache packages locally
   - Handle authentication for private repos

2. **Manifest Parser**
   - Parse YAML manifests
   - Validate package structure
   - Handle versioning

3. **Package Installer**
   - Download package assets
   - Execute installation steps
   - Handle rollback on failure

### Phase 2: Enhanced Features
1. **Dependency Resolution**
   - Check system dependencies
   - Install required packages
   - Handle version conflicts

2. **Version Management**
   - List available versions
   - Upgrade/downgrade packages
   - Pin specific versions

3. **Package Search & Discovery**
   - Search packages by name/tag
   - Show package details
   - List installed packages

### Phase 3: Advanced Features
1. **Package Creation Tools**
   - Scaffold new packages
   - Validate manifests
   - Test installations

2. **Registry Management**
   - Publish packages
   - Sign packages
   - Mirror registries

## API Design

### New MCP Tools

```python
# Search for packages
await package_search(query="ad blocker", tags=["network", "security"])

# Get package info
await package_info(name="pihole", version="latest")

# Install package
await package_install(
    name="pihole",
    hostname="192.168.1.100",
    version="2024.07.0",
    config={
        "timezone": "America/New_York",
        "upstream_dns": ["1.1.1.1", "1.0.0.1"]
    }
)

# List installed packages
await package_list(hostname="192.168.1.100")

# Update package
await package_update(name="pihole", hostname="192.168.1.100")

# Remove package
await package_remove(name="pihole", hostname="192.168.1.100")

# Add package source
await package_source_add(
    name="community",
    url="https://github.com/community/homelab-packages"
)
```

## Example Package Repository

### Registry Index (registry.json)
```json
{
  "packages": {
    "pihole": {
      "latest": "2024.07.0",
      "versions": ["2024.07.0", "2024.06.0", "2024.05.0"],
      "tags": ["dns", "adblock", "network"],
      "manifest": "packages/pihole/manifest.yaml"
    },
    "jellyfin": {
      "latest": "10.8.13",
      "versions": ["10.8.13", "10.8.12"],
      "tags": ["media", "streaming"],
      "manifest": "packages/jellyfin/manifest.yaml"
    }
  },
  "updated": "2024-01-25T12:00:00Z"
}
```

### Enhanced Manifest Features
```yaml
# Advanced manifest example
name: nextcloud
version: "28.0.1"
description: "Self-hosted cloud storage"
maintainer: "homelab-mcp"
source:
  github: nextcloud/docker
  ref: "28.0.1"
  files:
    - docker-compose.yml
    - .env.example
variants:
  minimal:
    description: "Basic Nextcloud without office"
    exclude: ["collabora", "onlyoffice"]
  full:
    description: "Nextcloud with Collabora Office"
    include: ["collabora"]
install:
  pre_install:
    - check: "port_available:443"
    - check: "disk_space:10GB"
  method: docker-compose
  variables:
    - name: admin_password
      type: password
      generate: true
    - name: database_password
      type: password
      generate: true
  templates:
    - src: .env.example
      dest: .env
      vars:
        ADMIN_PASSWORD: "{{admin_password}}"
        DB_PASSWORD: "{{database_password}}"
health_check:
  endpoint: "https://{{hostname}}/status.php"
  interval: 60
  timeout: 10
backup:
  paths:
    - /var/www/html/data
    - /var/www/html/config
  schedule: "0 2 * * *"  # Daily at 2 AM
```

## Migration Strategy

1. **Wrap Existing Templates**
   - Convert current YAML templates to package manifests
   - Maintain backward compatibility
   - Gradual migration path

2. **Dual-mode Operation**
   - Support both old and new installation methods
   - Provide migration tools
   - Document conversion process

## Benefits

1. **For Users**
   - Simple installation: `mcp install pihole`
   - Easy updates: `mcp update pihole`
   - Package discovery: `mcp search media`
   - Version control: `mcp install jellyfin@10.8.12`

2. **For Developers**
   - Standard package format
   - Easy distribution via GitHub
   - Version management
   - Community contributions

3. **For Organizations**
   - Private package registries
   - Approved package lists
   - Compliance tracking
   - Automated deployments

## Security Considerations

1. **Package Signing**
   - GPG signatures for packages
   - Verify package integrity
   - Trust chain management

2. **Sandboxed Execution**
   - Limited permissions during install
   - Rollback capabilities
   - Audit logging

3. **Registry Security**
   - HTTPS only for registries
   - Authentication for private repos
   - Rate limiting

## Next Steps

1. Create proof-of-concept package repository
2. Implement basic package fetching from GitHub
3. Add manifest parsing and validation
4. Integrate with existing service installer
5. Build CLI-style interface for MCP tools