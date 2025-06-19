# AI Sysadmin Guide - How the Homelab Context Works

## The Problem You Just Hit

Your Pi is named "proxmoxpi.local" but runs Raspbian. The AI got confused and tried to use Proxmox/LXD commands on a system that doesn't have them installed. This is exactly what the homelab context system prevents!

## How the AI Sysadmin Should Work

### 1. **Initial Discovery Phase**
When you first mention a new host, the AI should:
```
User: "I have a pi5 called proxmoxpi.local"

AI: Let me discover what's actually running on proxmoxpi.local...
[Runs: setup-homelab-wizard or discover-homelab-topology]

AI: I found proxmoxpi.local but need to understand its setup:
- What OS is it running? (Raspbian, Ubuntu, etc.)
- What services are already installed?
- What role should it have in your homelab?
```

### 2. **Device Classification**
The AI uses homelab context tools to properly classify devices:
```
[AI runs: add-homelab-device ip_address="192.168.10.xxx" hostname="proxmoxpi.local" 
         role="service_host" device_type="raspberry_pi" cpu_cores=4 memory_gb=8 
         notes="Pi 5 running Raspbian - NOT Proxmox despite name"]
```

### 3. **Smart Service Recommendations**
Based on the device's actual capabilities:
```
AI: Your Pi 5 with Raspbian can host React sites in several ways:
1. Docker containers (recommended) - Easy deployment
2. Node.js + PM2 - Direct hosting
3. Nginx + static files - For built React apps

Since it's NOT running Proxmox, we won't create VMs. Instead, let's use Docker.
```

## The Proper Workflow

### Step 1: Setup Homelab Context
```bash
# AI discovers your network
setup-homelab-wizard

# AI asks about each device found
"I found 192.168.10.50 - what is this device?"
> "That's my Pi 5 called proxmoxpi.local running Raspbian"

# AI classifies it correctly
add-homelab-device ip_address="192.168.10.50" hostname="proxmoxpi.local" 
                   role="service_host" device_type="raspberry_pi" 
                   os="raspbian" cpu_cores=4 memory_gb=8
```

### Step 2: Validate Before Actions
```bash
# Before suggesting services, AI checks capabilities
validate-device-for-service ip_address="192.168.10.50" service_name="docker"

# AI knows it's Raspbian, not Proxmox
"This is a Raspbian system, so I'll install Docker directly, not create VMs"
```

### Step 3: Execute Appropriate Commands
```bash
# AI uses the right tools for the right system
[For Raspbian Pi]: install-docker-on-pi, deploy-react-container
[For Proxmox host]: create_vm, configure-proxmox-network
[For Ubuntu server]: install-service-ubuntu, configure-nginx
```

## Making It Work in Chat

The AI should act like a real sysadmin who:

1. **Asks Questions First**
   - "What OS is running on proxmoxpi.local?"
   - "Should I rename it to avoid confusion?"
   - "What's your goal for this Pi?"

2. **Discovers Before Acting**
   - Uses `discover-homelab-topology` to scan
   - Validates assumptions with user
   - Updates context with accurate info

3. **Explains Decisions**
   - "Since this is Raspbian, not Proxmox, we'll use Docker instead of VMs"
   - "Your Pi 5 has 8GB RAM, perfect for multiple containers"
   - "I recommend Docker because it's easier to manage than VMs on a Pi"

## Example Conversation Flow

```
User: "I have pi5 called proxmoxpi.local and want to host a React site"

AI: I see you have a device called proxmoxpi.local. Despite the name, let me check what's actually running on it...

[AI runs: discover-hardware on proxmoxpi.local]

AI: I discovered it's a Raspberry Pi 5 running Raspbian, not Proxmox. Should we:
1. Rename it to avoid confusion (e.g., "pi5-services.local")?
2. Keep the name but note it's not actually running Proxmox?

Also, for hosting your React site on Raspbian, I recommend:
- Docker container with Nginx
- Port 80 for the site
- Automated deployment with Docker Compose

Shall I proceed with the Docker setup?

User: Yes, and let's rename it to pi5-web.local

AI: Perfect! Let me update the homelab context and set up Docker...

[AI runs: update-device-role ip_address="192.168.10.50" hostname="pi5-web.local"]
[AI runs: install-docker-raspbian host="pi5-web.local"]
[AI runs: create-react-container host="pi5-web.local"]

AI: ✅ Done! Your React site is now running at http://pi5-web.local
    I've also updated the homelab topology to correctly identify this as a Raspbian Pi.
```

## Key Benefits

1. **No More Confusion** - AI knows exactly what each device runs
2. **Appropriate Tools** - Uses Docker on Pi, VMs on Proxmox
3. **Persistent Knowledge** - Context survives between conversations
4. **Smart Recommendations** - Based on actual hardware/OS capabilities
5. **Prevention of Errors** - Won't try Proxmox commands on Raspbian

## Implementation Requirements

For this to work, the AI needs to:
1. **Always run discovery first** when encountering new hosts
2. **Update homelab context** with accurate device information
3. **Check context before executing** any infrastructure commands
4. **Ask for clarification** when device names don't match reality
5. **Explain its reasoning** so users understand decisions

This turns the AI into a true sysadmin who understands your specific infrastructure!