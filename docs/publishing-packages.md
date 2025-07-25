# Publishing Your Own Homelab Package Repository

## Quick Start: Fork and Publish

1. **Fork or Create a Repository**
   ```bash
   # Create a new repo on GitHub called "my-homelab-packages"
   # Clone it locally
   git clone https://github.com/yourusername/my-homelab-packages
   cd my-homelab-packages
   ```

2. **Create the Repository Structure**
   ```bash
   mkdir -p packages/pihole packages/jellyfin packages/nginx-proxy
   touch registry.json
   ```

3. **Add Your Registry Index**
   ```json
   {
     "packages": {
       "pihole": {
         "latest": "2024.07.0",
         "versions": ["2024.07.0"],
         "description": "Network-wide ad blocker",
         "tags": ["dns", "adblock", "network"],
         "manifest": "packages/pihole/manifest.yaml"
       },
       "nginx-proxy": {
         "latest": "1.0.0",
         "versions": ["1.0.0"],
         "description": "Reverse proxy with automatic SSL",
         "tags": ["proxy", "ssl", "web"],
         "manifest": "packages/nginx-proxy/manifest.yaml"
       }
     },
     "updated": "2024-01-25T12:00:00Z",
     "version": "1.0.0"
   }
   ```

4. **Create Your Package Manifests**
   
   Example: `packages/nginx-proxy/manifest.yaml`
   ```yaml
   name: nginx-proxy
   version: "1.0.0"
   description: "Automated nginx proxy with Let's Encrypt SSL"
   homepage: https://github.com/nginx-proxy/nginx-proxy
   maintainer: yourusername
   tags:
     - proxy
     - ssl
     - web
     - reverse-proxy

   requirements:
     ports: [80, 443]
     memory_gb: 0.5
     disk_gb: 1

   variables:
     - name: default_email
       type: string
       description: "Email for Let's Encrypt certificates"
       required: true

   install:
     method: docker-compose
     compose:
       version: "3.8"
       services:
         nginx-proxy:
           image: nginxproxy/nginx-proxy
           container_name: nginx-proxy
           ports:
             - "80:80"
             - "443:443"
           volumes:
             - /var/run/docker.sock:/tmp/docker.sock:ro
             - nginx-certs:/etc/nginx/certs
             - nginx-vhost:/etc/nginx/vhost.d
             - nginx-html:/usr/share/nginx/html
           restart: unless-stopped

         nginx-proxy-acme:
           image: nginxproxy/acme-companion
           container_name: nginx-proxy-acme
           volumes_from:
             - nginx-proxy
           volumes:
             - /var/run/docker.sock:/var/run/docker.sock:ro
             - acme:/etc/acme.sh
           environment:
             DEFAULT_EMAIL: "{{default_email}}"
           restart: unless-stopped

       volumes:
         nginx-certs:
         nginx-vhost:
         nginx-html:
         acme:

   post_install:
     - message: "Nginx proxy installed! Add VIRTUAL_HOST env to your containers."
     - message: "SSL certificates will be automatically generated."
   ```

5. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add homelab packages"
   git push origin main
   ```

## How Others Use Your Repository

### For Human Users:

1. **Add Your Repository**
   ```bash
   mcp package_source_add shaun https://github.com/yourusername/my-homelab-packages
   ```

2. **Search Your Packages**
   ```bash
   mcp package_search --query proxy --source shaun
   ```

3. **Install Your Packages**
   ```bash
   mcp package_install --name nginx-proxy --hostname myserver --source shaun \
     --config '{"default_email": "admin@example.com"}'
   ```

### For AI Assistants Using Your MCP:

The AI can discover and use your packages:
```
Human: "Install a reverse proxy on my server"

AI: Let me search for available proxy packages...
[Searches all sources including yours]
Found nginx-proxy from shaun's repository. Installing...
```

## Advanced Publishing Patterns

### 1. **Curated Stack Repository**
Create a repository with your preferred homelab stack:

```yaml
# packages/shaun-media-stack/manifest.yaml
name: shaun-media-stack
version: "1.0.0"
description: "Shaun's complete media server stack"
dependencies:
  - jellyfin
  - sonarr
  - radarr
  - transmission
  - nginx-proxy
```

### 2. **Company/Team Repository**
For internal use:
```bash
# Private repository
mcp package_source_add company https://github.com/mycompany/internal-homelab-packages \
  --auth-token $GITHUB_TOKEN
```

### 3. **Version-Specific Manifests**
Support multiple versions:
```
packages/jellyfin/
├── manifest.yaml          # Latest version
├── versions/
│   ├── 10.8.13.yaml
│   ├── 10.8.12.yaml
│   └── 10.8.11.yaml
```

## Best Practices for Package Publishers

1. **Test Your Packages**
   - Always test on a clean system
   - Verify all dependencies are declared
   - Test upgrade paths between versions

2. **Documentation**
   - Include clear descriptions
   - Document all variables
   - Provide post-install instructions

3. **Security**
   - Never hardcode passwords
   - Use variable generation for secrets
   - Keep images/versions updated

4. **Versioning**
   - Follow semantic versioning
   - Document breaking changes
   - Maintain compatibility when possible

## Example: Complete Custom Repository

Here's a real example you could publish today:

```bash
# Your repository structure
my-homelab-packages/
├── README.md
├── registry.json
├── packages/
│   ├── pihole-unbound/        # Pi-hole with Unbound DNS
│   │   └── manifest.yaml
│   ├── authentik/              # Modern authentication
│   │   └── manifest.yaml
│   ├── uptime-kuma/           # Status monitoring
│   │   └── manifest.yaml
│   └── tailscale-exit/        # Tailscale exit node
│       └── manifest.yaml
```

Then anyone (human or AI) can:
```bash
# Add your repository
mcp package_source_add custom https://github.com/yourusername/my-homelab-packages

# See what you offer
mcp package_list --source custom

# Install your curated services
mcp package_install --name pihole-unbound --hostname dns-server --source custom
```

## Collaborative Benefits

1. **Share Your Expertise**: Your optimized configurations help others
2. **Build on Others' Work**: Fork and improve existing packages
3. **AI Learning**: AIs can discover and recommend your packages
4. **Community Growth**: More packages = better homelab ecosystem

## Getting Started Today

1. Copy the example repository structure from this MCP
2. Add your favorite service configurations
3. Push to GitHub
4. Share your repository URL

Your packages are immediately available to anyone using this MCP!