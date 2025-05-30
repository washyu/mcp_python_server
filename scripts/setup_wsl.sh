#!/bin/bash
# Helper script for WSL users to connect to Ollama running on Windows

echo "WSL Ollama Setup Helper"
echo "======================"
echo

# Try different methods to find Ollama on Windows
METHODS=(
    "host.docker.internal"
    "$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')"
    "$(powershell.exe -Command 'hostname' 2>/dev/null | tr -d '\r\n').local"
    "localhost"
)

echo "Trying to connect to Ollama on Windows..."
echo

WORKING_HOST=""

for host in "${METHODS[@]}"; do
    echo -n "Testing http://$host:11434 ... "
    if curl -s "http://$host:11434/api/tags" > /dev/null 2>&1; then
        echo "✓ Success!"
        WORKING_HOST="http://$host:11434"
        break
    else
        echo "✗ Failed"
    fi
done

echo

if [ -n "$WORKING_HOST" ]; then
    echo "✓ Successfully connected to Ollama at $WORKING_HOST"
    echo
    echo "To use Ollama from WSL, run:"
    echo "  export OLLAMA_HOST=$WORKING_HOST"
    echo
    echo "To make this permanent, add it to your ~/.bashrc or ~/.zshrc:"
    echo "  echo 'export OLLAMA_HOST=$WORKING_HOST' >> ~/.bashrc"
    echo
    echo "You can now run the test scripts:"
    echo "  python simple_test.py"
    echo "  python test_agent.py"
else
    echo "✗ Could not connect to Ollama on any known address"
    echo
    echo "Please make sure:"
    echo "1. Ollama is running on Windows (check system tray)"
    echo "2. Windows Firewall allows connections from WSL"
    echo
    echo "You can also try manually with your Windows IP:"
    echo "  1. Find your Windows IP in Command Prompt: ipconfig"
    echo "  2. Export: export OLLAMA_HOST=http://<your-ip>:11434"
    echo
    echo "Alternative: Run Ollama directly in WSL:"
    echo "  curl -fsSL https://ollama.com/install.sh | sh"
    echo "  ollama serve"
fi