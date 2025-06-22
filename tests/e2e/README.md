# End-to-End Tests

This directory contains end-to-end tests for the MCP server, focusing on testing the complete system including the chat interface, tool execution, and AI behavior.

## Test Structure

### Core Tests

- **`test_system.py`** - Basic system health check
  - Verifies chat server is running
  - Checks tool availability
  - Tests basic chat functionality

- **`test_hardware_discovery_ui.py`** - Comprehensive hardware discovery testing
  - Tests multiple query scenarios
  - Verifies correct tool usage
  - Detects hallucination patterns
  - Validates template format execution

- **`test_quick_hardware_discovery.py`** - Quick hardware discovery validation
  - Single test case for rapid testing
  - Checks tool execution and AI response
  - Identifies hallucination issues

### Running Tests

#### Run All E2E Tests
```bash
python tests/e2e/run_tests.py
```

#### Run Individual Tests
```bash
# Quick system health check
python tests/e2e/test_system.py

# Test hardware discovery functionality
python tests/e2e/test_quick_hardware_discovery.py

# Comprehensive UI test suite
python tests/e2e/test_hardware_discovery_ui.py
```

## Test Requirements

1. **MCP Server Running**: The server must be running on localhost:3001
   ```bash
   docker-compose up -d
   ```

2. **Ollama Available**: Ollama must be accessible (default: localhost:11434)

3. **Python Dependencies**: Tests use standard library + aiohttp
   ```bash
   pip install aiohttp
   ```

## Adding New E2E Tests

1. Create a new test file in this directory
2. Follow the naming convention: `test_<feature>.py`
3. Add the test to `run_tests.py` if it should be part of the suite
4. Document any special requirements

## Test Patterns

### Testing AI Tool Usage
```python
# Check if AI uses correct tool format
tool_pattern = r'EXECUTE_TOOL:\s*(\w+)'
tool_matches = re.findall(tool_pattern, response)
```

### Testing for Hallucinations
```python
# Check for known hallucination patterns
hallucination_indicators = ["intel i9-9900k", "msi motherboard", ...]
hallucinations = [ind for ind in hallucination_indicators if ind in response.lower()]
```

### Streaming Response Handling
```python
async for line in response.content:
    if line.startswith('data: '):
        data = json.loads(line[6:])
        # Process streaming data
```

## Common Issues

1. **"Chat server unreachable"**: Ensure Docker containers are running
2. **"Non-streaming chat not implemented"**: Use `stream: true` in requests
3. **Tool execution timeouts**: Increase timeout values in test code