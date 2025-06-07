# Test Suite Organization

This directory contains a comprehensive test suite organized by test type and scope.

## 📁 Test Structure

```
tests/
├── unit/                    # 🔬 Unit Tests (2 files, 20 tests)
│   ├── test_credential_manager.py
│   └── test_proxmox_api.py
├── feature/                 # 🎯 Feature Tests (7 files, 60 tests)
│   ├── test_hardware_discovery.py
│   ├── test_infrastructure_visualizer.py
│   ├── test_deployment_suggestions.py
│   ├── test_filtering_edge_cases.py
│   ├── test_ai_vs_explicit_filtering.py
│   ├── test_nonsensical_behavior.py
│   └── test_nonexistent_queries.py
├── integration/             # 🔗 Integration Tests (3 files, 3 tests)
│   ├── test_proxmox_integration.py
│   ├── test_simple_integration.py
│   └── test_mcp_client.py
├── e2e/                     # 🌐 End-to-End Tests (2 files, 2 tests)
│   ├── test_websocket.py
│   └── test_subprocess.py
├── service/                 # 🔌 Service Tests (2 files, 2 tests)
│   ├── test_ollama.py
│   └── test_token_creation.py
├── communication/           # 📡 Communication Tests (2 files, 2 tests)
│   ├── test_server.py
│   └── test_direct.py
├── manual/                  # 📝 Manual Test Scenarios (2 files, 9 scenarios)
│   ├── test_wizard_integration.py    # Web UI wizard workflows
│   └── test_websocket_integration.py # WebSocket communication
└── conftest.py              # ⚙️ Shared test configuration
```

## 🎯 Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions/classes in isolation
- **Dependencies**: Heavy use of mocks, no external services
- **Speed**: Very fast (< 1 second each)
- **Scope**: Single function or class method

### Feature Tests (`tests/feature/`)
- **Purpose**: Test complete feature workflows end-to-end
- **Dependencies**: May use mock fixtures, some external data
- **Speed**: Fast to medium (1-5 seconds each)
- **Scope**: Complete user-facing features
- **Examples**: Hardware discovery, deployment suggestions, visualization

### Integration Tests (`tests/integration/`)
- **Purpose**: Test interaction between multiple components
- **Dependencies**: May require mock API or real services
- **Speed**: Medium (2-10 seconds each)
- **Scope**: Cross-component workflows
- **Examples**: MCP client ↔ server, Proxmox API integration

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user scenarios from start to finish
- **Dependencies**: Real network communication, subprocess spawning
- **Speed**: Slower (5-30 seconds each)
- **Scope**: Full application workflows
- **Examples**: WebSocket communication, subprocess IPC

### Service Tests (`tests/service/`)
- **Purpose**: Test connectivity and integration with external services
- **Dependencies**: External services (Ollama, Proxmox API)
- **Speed**: Variable (depends on service)
- **Scope**: External service integration
- **Examples**: Ollama connectivity, API token validation

### Communication Tests (`tests/communication/`)
- **Purpose**: Test protocols, message formats, and transport layers
- **Dependencies**: Minimal, focused on protocol correctness
- **Speed**: Fast to medium
- **Scope**: Protocol and transport testing
- **Examples**: MCP protocol messages, direct function calls

## 🚀 Running Tests

### By Category
```bash
# Run all tests
uv run pytest

# Run specific categories
uv run pytest tests/unit/           # Fastest
uv run pytest tests/feature/        # Core functionality 
uv run pytest tests/integration/    # Component interaction
uv run pytest tests/e2e/            # Full scenarios
uv run pytest tests/service/        # External services
uv run pytest tests/communication/  # Protocol testing
```

### By Markers
```bash
# Using pytest markers (defined in pytest.ini)
uv run pytest -m unit              # Unit tests only
uv run pytest -m feature           # Feature tests only
uv run pytest -m "not slow"        # Skip slow tests
uv run pytest -m requires_mock_api # Tests needing mock API
```

### By Pattern
```bash
# Run specific test patterns
uv run pytest -k hardware          # All hardware-related tests
uv run pytest -k "gpu or cpu"      # Hardware discovery tests
uv run pytest -k "not integration" # Skip integration tests
```

## 📊 Test Metrics

- **Total Tests**: 100
- **Unit Tests**: 11 (fast, isolated)
- **Feature Tests**: 67 (core functionality)
- **Integration Tests**: 10 (component interaction)
- **E2E Tests**: 2 (full scenarios)
- **Service Tests**: 2 (external services)
- **Communication Tests**: 2 (protocols)

## 🛠️ Test Development Guidelines

### Adding New Tests

1. **Determine test type** based on scope:
   - Testing a single function? → `unit/`
   - Testing a complete feature? → `feature/`
   - Testing component interaction? → `integration/`
   - Testing full user scenario? → `e2e/`
   - Testing external service? → `service/`
   - Testing protocol/transport? → `communication/`

2. **Follow naming convention**: `test_[feature_name].py`

3. **Use appropriate fixtures** from `conftest.py`

4. **Add markers** if needed:
   ```python
   @pytest.mark.slow
   @pytest.mark.requires_mock_api
   async def test_my_feature():
       ...
   ```

### Best Practices

- **Unit tests**: Mock all external dependencies
- **Feature tests**: Test realistic workflows with sample data
- **Integration tests**: Use minimal real services or comprehensive mocks
- **E2E tests**: Test actual user scenarios
- **Keep tests focused**: One test should verify one behavior
- **Use descriptive names**: Test name should explain what's being verified

## 🔧 Configuration

- **pytest.ini**: Main pytest configuration
- **conftest.py**: Shared fixtures and test utilities
- **Coverage**: Configured to report on `src/` directory
- **Async support**: Automatic async test detection

## 📈 Running Performance

The test suite is optimized for development workflow:

- **Unit tests**: < 10 seconds total
- **Feature tests**: < 30 seconds total  
- **Full suite**: < 2 minutes total
- **Parallel execution**: Tests can run in parallel with `pytest-xdist`

## 🎯 Continuous Integration

The test structure supports different CI strategies:

```bash
# Fast feedback (PR checks)
uv run pytest tests/unit/ tests/feature/

# Full validation (main branch)
uv run pytest tests/

# Service validation (nightly)
uv run pytest tests/service/ tests/integration/
```

This organization makes it easy to run the right tests at the right time while maintaining comprehensive coverage of the MCP infrastructure management platform.