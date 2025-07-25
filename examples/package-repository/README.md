# Homelab MCP Package Repository

This is an example package repository for the Homelab MCP package manager.

## Structure

```
.
├── registry.json                    # Package index
├── packages/
│   ├── pihole/
│   │   ├── manifest.yaml           # Main package manifest
│   │   ├── versions/               # Version-specific manifests
│   │   │   ├── 2024.07.0.yaml
│   │   │   └── 2024.06.0.yaml
│   │   └── assets/                 # Additional files
│   │       └── custom-blocklist.txt
│   └── jellyfin/
│       └── manifest.yaml
```

## Usage

### Add this repository as a package source:
```bash
mcp package-source-add myrepo https://github.com/yourusername/homelab-packages
```

### Search for packages:
```bash
mcp package-search "ad blocker"
mcp package-search --tags network,security
```

### Install a package:
```bash
mcp package-install pihole --host 192.168.1.100
mcp package-install jellyfin --host media-server --version 10.8.12
```

### Update packages:
```bash
mcp package-update pihole --host 192.168.1.100
```

## Creating Your Own Packages

1. Fork this repository
2. Add your package manifest to `packages/yourpackage/manifest.yaml`
3. Update `registry.json` with your package information
4. Commit and push your changes
5. Share your repository URL with others

## Package Manifest Format

See `packages/pihole/manifest.yaml` for a complete example.

### Required Fields:
- `name`: Package identifier
- `version`: Current version
- `description`: Brief description
- `install`: Installation configuration

### Optional Fields:
- `homepage`: Project homepage
- `license`: License identifier
- `maintainer`: Package maintainer
- `tags`: Search tags
- `requirements`: System requirements
- `variables`: Configurable options
- `variants`: Pre-configured variants
- `post_install`: Post-installation steps
- `health_check`: Service health monitoring
- `backup`: Backup configuration

## Best Practices

1. **Versioning**: Use semantic versioning (e.g., 1.2.3)
2. **Testing**: Test your packages before publishing
3. **Documentation**: Include clear descriptions and examples
4. **Security**: Never include secrets or passwords in manifests
5. **Updates**: Keep packages updated with upstream releases

## Contributing

1. Submit packages via pull request
2. Follow the existing structure and format
3. Test your packages thoroughly
4. Include documentation for complex configurations