# WSL Setup Guide for Ollama Integration

This guide helps you connect your WSL development environment to Ollama running on Windows.

## Option 1: Configure Ollama on Windows to Accept WSL Connections

By default, Ollama on Windows only listens on localhost, which WSL can't access. You need to configure it to listen on all interfaces.

### Steps:

1. **Stop Ollama on Windows** (right-click system tray icon → Quit)

2. **Set Environment Variable** to make Ollama listen on all interfaces:
   - Open Windows Command Prompt as Administrator
   - Run: `setx OLLAMA_HOST "0.0.0.0:11434" /M`
   - Alternatively, set it in System Environment Variables:
     - Windows Settings → System → About → Advanced system settings
     - Environment Variables → System variables → New
     - Variable name: `OLLAMA_HOST`
     - Variable value: `0.0.0.0:11434`

3. **Restart Ollama** on Windows

4. **Find your Windows IP** (from Windows Command Prompt):
   ```cmd
   ipconfig
   ```
   Look for your IPv4 address (usually starts with 192.168.x.x)

5. **In WSL, set the OLLAMA_HOST**:
   ```bash
   export OLLAMA_HOST=http://192.168.x.x:11434  # Replace with your IP
   ```

6. **Test the connection**:
   ```bash
   curl http://192.168.x.x:11434/api/tags
   ```

## Option 2: Run Ollama Directly in WSL

If you can't get the Windows connection working, you can run Ollama directly in WSL:

```bash
# Install Ollama in WSL
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull llama3.2:3b
```

## Testing Your Setup

Once you have Ollama accessible from WSL:

```bash
# Test the connection
python simple_test.py

# Run the interactive agent
python test_agent.py
```

## Troubleshooting

### Windows Firewall
If you can't connect from WSL to Windows Ollama:
1. Open Windows Defender Firewall
2. Click "Allow an app or feature..."
3. Find Ollama and ensure it's allowed for Private networks

### Finding the Right IP
Try these commands in WSL to find your Windows host:
```bash
# Method 1: From resolv.conf
cat /etc/resolv.conf | grep nameserver

# Method 2: Using PowerShell
powershell.exe -Command "Get-NetIPAddress -AddressFamily IPv4 | Select-Object -ExpandProperty IPAddress"

# Method 3: Check WSL network
ip route | grep default
```

### Permanent Configuration
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
# For Ollama on Windows
export OLLAMA_HOST=http://192.168.x.x:11434  # Replace with your IP
```