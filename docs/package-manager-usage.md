# Homelab MCP Package Manager Usage Guide

This guide shows how to use the new Scoop-like package manager functionality in the Homelab MCP.

## Overview

The package manager allows you to:
- Search for homelab services in online repositories
- Install services from GitHub-hosted package repositories
- Update installed services to newer versions
- Manage multiple package sources
- Deploy the same configuration to multiple devices

## Basic Usage

### 1. Search for Packages

Search for packages by name or description:
```
# Search for ad blockers
mcp package_search --query "ad blocker"

# Search by tags
mcp package_search --query "dns" --tags network,security
```

### 2. Get Package Information

View detailed information about a package:
```
# Get info about Pi-hole
mcp package_info --name pihole

# Get info about a specific version
mcp package_info --name pihole --version 2024.06.0
```

### 3. Install a Package

Install a package on a target device:
```
# Basic installation
mcp package_install --name pihole --hostname 192.168.1.100

# Install with custom configuration
mcp package_install --name pihole --hostname 192.168.1.100 --config '{"timezone": "America/New_York", "upstream_dns": ["8.8.8.8", "8.8.4.4"]}'

# Install specific version
mcp package_install --name jellyfin --hostname media-server --version 10.8.12
```

### 4. List Installed Packages

View installed packages:
```
# List all installed packages across all hosts
mcp package_list

# List packages on a specific host
mcp package_list --hostname 192.168.1.100
```

### 5. Update Packages

Update installed packages to the latest version:
```
# Update Pi-hole
mcp package_update --name pihole --hostname 192.168.1.100
```

### 6. Remove Packages

Remove an installed package:
```
mcp package_remove --name pihole --hostname 192.168.1.100
```

## Managing Package Sources

### Add a Custom Repository

Add your own or community package repositories:
```
# Add a community repository
mcp package_source_add --name community --url https://github.com/homelab-community/packages

# Add a private repository
mcp package_source_add --name mycompany --url https://github.com/mycompany/homelab-packages
```

### List Package Sources

View all configured package sources:
```
mcp package_source_list
```

### Remove a Package Source

Remove a package source:
```
mcp package_source_remove --name community
```

## Deploying to Multiple Devices

### Example: Deploy Pi-hole to Multiple Devices

1. Create a configuration file for your Pi-hole setup:
```yaml
# pihole-config.yaml
timezone: "America/New_York"
upstream_dns:
  - "1.1.1.1"
  - "1.0.0.1"
webpassword: "SecurePassword123"
dhcp_enabled: false
```

2. Deploy to multiple devices:
```bash
# Deploy to home network
mcp package_install --name pihole --hostname home-pihole --config @pihole-config.yaml

# Deploy to travel router with hotspot variant
mcp package_install --name pihole --hostname travel-pihole --config @pihole-config.yaml --variant hotspot
```

## Creating Your Own Packages

### Package Repository Structure

Create a GitHub repository with this structure:
```
my-homelab-packages/
├── registry.json
├── packages/
│   └── myservice/
│       ├── manifest.yaml
│       └── assets/
│           └── docker-compose.yml
```

### Example Manifest

```yaml
name: myservice
version: "1.0.0"
description: "My custom homelab service"
homepage: https://example.com
tags:
  - custom
  - service

requirements:
  ports: [8080]
  memory_gb: 2
  disk_gb: 10

install:
  method: docker-compose
  compose:
    version: "3.8"
    services:
      myservice:
        image: myimage:latest
        ports:
          - "8080:80"

post_install:
  - message: "Service installed at http://{{hostname}}:8080"
```

### Publishing Your Package

1. Create your package manifest
2. Update registry.json with your package info
3. Push to GitHub
4. Share your repository URL

Users can then add your repository:
```
mcp package_source_add --name custom --url https://github.com/yourusername/my-homelab-packages
mcp package_install --name myservice --hostname myserver --source custom
```

## Advanced Features

### Using Package Variants

Some packages offer pre-configured variants:
```
# Install Pi-hole in hotspot mode for travel router
mcp package_install --name pihole --hostname travel-router --variant hotspot

# Install minimal variant without HTTPS
mcp package_install --name pihole --hostname test-server --variant minimal
```

### Batch Operations

Deploy multiple services to a new server:
```bash
#!/bin/bash
HOST="192.168.1.100"

# Install core services
mcp package_install --name pihole --hostname $HOST
mcp package_install --name jellyfin --hostname $HOST
mcp package_install --name homeassistant --hostname $HOST
mcp package_install --name nextcloud --hostname $HOST
```

### Configuration Templates

Use environment variables in configurations:
```bash
export HOMELAB_TIMEZONE="America/New_York"
export HOMELAB_DOMAIN="home.local"

mcp package_install --name pihole --hostname pihole.$HOMELAB_DOMAIN \
  --config "{\"timezone\": \"$HOMELAB_TIMEZONE\"}"
```

## Best Practices

1. **Test Before Production**: Always test package installations on a test device first
2. **Use Version Pinning**: Pin specific versions for production deployments
3. **Backup Configurations**: Keep backups of your custom configurations
4. **Monitor Updates**: Regularly check for package updates but test before applying
5. **Custom Sources**: Only add package sources from trusted repositories

## Troubleshooting

### Package Not Found
- Verify the package name with `package_search`
- Check if the source repository is added
- Ensure the repository is accessible

### Installation Fails
- Check service requirements with the package info
- Verify the target device meets requirements
- Check SSH connectivity to the target device
- Review error messages for specific issues

### Updates Not Working
- Ensure the package source is accessible
- Check if a newer version actually exists
- Verify the service can be safely updated

## Example Workflow

Here's a complete example of setting up a new homelab server:

```bash
# 1. Setup MCP admin access
mcp setup_mcp_admin --hostname 192.168.1.200 --admin_user myuser --admin_password mypass

# 2. Search for services
mcp package_search --query "media" --tags streaming

# 3. Get package details
mcp package_info --name jellyfin

# 4. Install services
mcp package_install --name pihole --hostname 192.168.1.200
mcp package_install --name jellyfin --hostname 192.168.1.200
mcp package_install --name nextcloud --hostname 192.168.1.200

# 5. List installed packages
mcp package_list --hostname 192.168.1.200

# 6. Check for updates periodically
mcp package_update --name pihole --hostname 192.168.1.200
mcp package_update --name jellyfin --hostname 192.168.1.200
```

This package manager makes it easy to deploy and manage homelab services across multiple devices with consistent configurations!