# How the AI Sysadmin Uses Homelab Context

## Example Conversation: Pi with Confusing Name

### ❌ Without Homelab Context (What Happened Before):
```
User: "I have a pi5 called proxmoxpi.local and want to setup a vm on it to host a react site"

AI: "I'll help you create a VM on your Proxmox host..."
[Tries to use Proxmox/LXD commands that don't exist on Raspbian]
[FAILS because it assumed based on hostname]
```

### ✅ With Homelab Context (What Happens Now):
```
User: "My homelab consists of just my pi5 called proxmoxpi.local running Raspbian"

AI: Let me add that to the homelab context so I understand your setup correctly...

**EXECUTE_TOOL:** add-homelab-device {
  "ip_address": "192.168.10.50",
  "hostname": "proxmoxpi.local", 
  "role": "service_host",
  "device_type": "raspberry_pi",
  "cpu_cores": 4,
  "memory_gb": 8,
  "notes": "Pi 5 running Raspbian - NOT Proxmox despite the name"
}

Result: ✅ Device added successfully
- Hostname: proxmoxpi.local
- Role: service_host (can deploy services)
- Type: Raspberry Pi running Raspbian

Now I understand - despite the name "proxmoxpi", this is actually a Raspberry Pi 5 running Raspbian OS, not Proxmox!

For hosting a React site on Raspbian, we have better options than VMs:

1. **Docker Container** (Recommended)
   - Easy deployment and management
   - Good resource efficiency on Pi
   - Simple updates

2. **Direct Node.js + PM2**
   - Run React dev server or built app
   - Process management with PM2

3. **Nginx Static Hosting**
   - For production React builds
   - Most efficient option

Since this is Raspbian, not a hypervisor, I'll help you set up Docker. Shall I proceed?

User: "Yes, use Docker"

AI: Perfect! Let me install Docker on your Pi...

**EXECUTE_TOOL:** install-docker-raspbian {"host": "proxmoxpi.local"}

[Now the AI uses the CORRECT tools for Raspbian, not Proxmox!]
```

## How It Works

### 1. User Describes Infrastructure
```
"My homelab is:
- Pi 5 called proxmoxpi running Raspbian  
- Old laptop as dev machine
- Synology NAS for storage"
```

### 2. AI Records Context
```
**EXECUTE_TOOL:** add-homelab-device {"hostname": "proxmoxpi.local", "role": "service_host", "device_type": "raspberry_pi", "os": "raspbian"}
**EXECUTE_TOOL:** add-homelab-device {"hostname": "dev-laptop", "role": "development", "exclude_from_homelab": true}
**EXECUTE_TOOL:** add-homelab-device {"hostname": "synology-nas", "role": "storage_device", "device_type": "nas"}
```

### 3. AI Makes Smart Decisions
- Won't try to deploy to dev laptop (excluded)
- Uses Docker/containers on Pi (not VMs)
- Suggests appropriate services for Pi specs
- Remembers this context for future conversations

## Key Benefits

1. **No Assumptions** - AI learns what's actually running
2. **Persistent Knowledge** - Context survives between chats
3. **Appropriate Actions** - Right tools for right systems
4. **Smart Validation** - "Can my Pi handle Nextcloud?"

## Available Context Commands

- `list-homelab-devices` - Show all devices and roles
- `add-homelab-device` - Add new device with details
- `validate-device-for-service` - Check if device can run service
- `get-deployable-hosts` - Find suitable deployment targets
- `update-device-role` - Change device classification

The AI now acts like a real sysadmin who knows YOUR specific infrastructure!