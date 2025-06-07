# Manual Test Scenarios

This folder contains test scenarios that should be executed manually through the web UI chat client rather than automated pytest runs.

## 📁 Contents

- `test_wizard_integration.py` - Wizard workflow test scenarios for manual validation
- `test_websocket_integration.py` - WebSocket connection and communication tests

## 🎯 Purpose

These files serve as:
1. **Test documentation** - What needs to be tested manually
2. **Expected behavior** - How the system should respond
3. **Test data** - Sample inputs and configurations
4. **Reference implementation** - How the feature should work

## ⚠️ Important

**These tests are NOT run by pytest!** They are excluded from automated test discovery.

To run automated tests:
```bash
# This will NOT include tests/manual/
uv run pytest
```

To view manual test scenarios:
```bash
# Read the test files for scenarios
cat tests/manual/test_wizard_integration.py
```

## 🧪 Manual Testing Process

1. Start the MCP server and web UI chat client
2. Reference these test files for scenarios to execute
3. Follow the test methods as guides for what to validate
4. Record results in MANUAL_TESTING.md

## 📝 Converting Back to Automated Tests

If you implement automated testing for these features (e.g., with Playwright for web UI):
1. Move the test back to `tests/integration/`
2. Update the test to use real automation
3. Remove from this manual folder