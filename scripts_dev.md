# Development Helper Commands

## Switch Ollama Endpoints

### Use Local Ollama (Development)
```bash
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama3.2:1b
uv run pytest tests/service/test_ollama.py -v
```

### Use Pi5 Ollama (Production Testing)  
```bash
export OLLAMA_HOST=http://192.168.10.185:11434
export OLLAMA_MODEL=llama2
uv run pytest tests/service/test_ollama.py -v
```

## Test Different Scenarios

### Fast Local Testing
```bash
# Local Ollama + Mock Proxmox
cd ../testing/mock-api && docker-compose up -d
export OLLAMA_HOST=http://localhost:11434
uv run pytest tests/service/ tests/integration/ -v
```

### Full Integration Testing
```bash  
# Pi5 Ollama + Real Proxmox
export OLLAMA_HOST=http://192.168.10.185:11434
export PROXMOX_HOST=192.168.10.200
uv run pytest tests/integration/ -v
```