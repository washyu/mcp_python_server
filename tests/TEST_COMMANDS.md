# Test Command Reference

## 🚀 Quick Test Commands (No External Services Needed)

### Fast Development Testing
```bash
# Unit + Feature tests only (fastest, 60+ tests)
uv run pytest tests/unit/ tests/feature/ -v

# All standalone tests (no external services)
uv run pytest -m "not requires_ollama and not requires_proxmox" -v

# Specific feature categories
uv run pytest tests/feature/test_hardware_discovery.py -v
uv run pytest tests/feature/test_infrastructure_visualizer.py -v
```

### Integration Testing (Mostly Standalone)
```bash
# Safe integration tests (use mocks)
uv run pytest tests/integration/test_proxmox_integration.py -v
uv run pytest tests/integration/test_websocket_integration.py -v  
uv run pytest tests/integration/test_wizard_integration.py -v
uv run pytest tests/integration/test_mcp_client.py -v

# E2E tests (start their own servers)
uv run pytest tests/e2e/ -v
```

## ⚠️ Tests Requiring External Services

### Tests Needing Ollama (3 tests)
```bash
# When Pi5 Ollama is available at 192.168.10.185:11434
export OLLAMA_HOST=http://192.168.10.185:11434
uv run pytest -m requires_ollama -v

# Specific Ollama tests:
# - tests/service/test_ollama.py
# - tests/integration/test_simple_integration.py
```

### Tests Needing Real Proxmox (1 test)
```bash
# When real Proxmox is available
uv run pytest -m requires_proxmox -v

# Specific test:
# - tests/service/test_token_creation.py
```

## 📊 Test Breakdown

**Total Tests**: 100
- **Standalone**: 96 tests (no external services needed)
- **Need Ollama**: 2 tests  
- **Need Proxmox**: 1 test
- **Need WebUI**: 0 tests (none require web UI)

## 🎯 Development Workflow

### Daily Development (No Services)
```bash
# Run the 96 standalone tests
uv run pytest -m "not requires_ollama and not requires_proxmox" -v
```

### With Mock API (Optional) 
```bash
# Start mock Proxmox API
cd ../testing/mock-api && docker-compose up -d

# Run integration tests
cd ../../mcp_python_server
uv run pytest tests/integration/ -v

# Stop mock API
cd ../testing/mock-api && docker-compose down
```

### Full Testing (When Services Available)
```bash
# Ensure Pi5 services are up
# Ollama: http://192.168.10.185:11434
# Proxmox: http://192.168.10.200:8006

# Run all 100 tests
uv run pytest -v
```

## 🏃‍♂️ Speed Reference

- **Unit tests**: < 5 seconds (11 tests)
- **Feature tests**: < 20 seconds (60 tests)  
- **Integration tests**: < 10 seconds (10 tests)
- **E2E tests**: < 10 seconds (2 tests)
- **Service tests**: Variable (depends on service)

## 💡 Pro Tips

1. **VSCode Testing Tab**: Should show all 100 tests after reload
2. **Coverage**: Add `--cov=src` to any command for coverage report
3. **Parallel**: Add `-n auto` if you install pytest-xdist
4. **Verbose**: Use `-vv` for more detailed output
5. **Failed Only**: Use `--lf` to run only last failed tests