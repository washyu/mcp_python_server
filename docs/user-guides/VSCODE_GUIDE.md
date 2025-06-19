# VS Code Development Guide

## 🚀 Quick Start

### One-Click Launch
1. Press **F5** - Launches the chat interface with all services
2. Or use Command Palette: `Cmd+Shift+P` → "Debug: Start Debugging"

### Alternative Launch Methods
- **Run & Debug Panel**: Click the play button next to "💬 Chat Interface (Default)"
- **Multi-Process Debug**: Select "🚀 Homelab System (Full)" for debugging multiple services

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F5` | Start Chat Interface |
| `Cmd+Shift+H` | System Health Check |
| `Cmd+Shift+T` | Run Tests |
| `Cmd+Shift+C` | Run Tests with Coverage |
| `Cmd+Shift+I` | Install Dependencies |
| `Cmd+Shift+D` | Open Debug Panel |

## 🛠️ VS Code Tasks

Access via: `Cmd+Shift+P` → "Tasks: Run Task"

- **Install Dependencies** - Install/update Python packages
- **Run Tests** - Run pytest on current file or all tests
- **Run Tests with Coverage** - Generate coverage report
- **Format Code** - Apply Black formatting
- **Lint Code** - Check code with flake8
- **System Health Check** - Verify all services are ready
- **Clean Project** - Remove cache files

## 🐛 Debugging Features

### Debug Configurations
1. **💬 Chat Interface (Default)** - Full system with auto-dependency install
2. **🚀 Homelab System (Full)** - Multi-process debugging
3. **🧪 Run Tests** - Debug specific test files
4. **🐛 Debug Current File** - Debug any Python file

### Debugging Tips
- Set breakpoints by clicking left of line numbers
- Use Debug Console for interactive debugging
- Watch variables in the Variables panel
- Step through code with F10 (step over) and F11 (step into)

## 📦 Extension Recommendations

Install recommended extensions: 
1. Open Extensions panel (`Cmd+Shift+X`)
2. Filter by `@recommended`
3. Install all workspace recommendations

Key extensions:
- **Python** - IntelliSense, debugging, testing
- **Pylance** - Advanced type checking
- **Coverage Gutters** - Shows test coverage in editor
- **GitLens** - Enhanced Git integration

## 🧪 Testing

### Run Tests
- **Current File**: Right-click → "Run Python Tests in Current File"
- **All Tests**: Test Explorer panel → Run all
- **Debug Test**: Click debug icon next to test in Test Explorer

### Coverage
1. Run task: "Run Tests with Coverage"
2. View coverage:
   - In editor: Green/red highlights
   - HTML report: `htmlcov/index.html`

## 🔧 Configuration

### Environment Variables
- Edit `.env` file for configuration
- VS Code auto-loads `.env` when debugging

### Python Interpreter
- Auto-detects `.venv` 
- Change via: Bottom status bar → Python version

## 📝 Code Snippets

Type these prefixes for quick code generation:
- `mcptool` - Create MCP tool definition
- `atest` - Create async test
- `toolhandler` - Create tool handler function

## 🏗️ Project Structure

```
mcp_python_server/
├── .vscode/          # VS Code configuration
├── src/              # Source code
│   ├── server/       # MCP servers
│   ├── tools/        # MCP tools
│   └── utils/        # Utilities
├── tests/            # Test files
├── main.py           # Entry point
└── .env              # Configuration
```

## 💡 Tips

1. **IntelliSense**: Use `Ctrl+Space` for suggestions
2. **Quick Fix**: `Cmd+.` on errors for auto-fixes
3. **Refactor**: `F2` to rename symbols
4. **Go to Definition**: `Cmd+Click` on any symbol
5. **Find References**: Right-click → "Find All References"

## 🚨 Troubleshooting

### Build Errors
1. Run "System Health Check" task
2. Run "Install Dependencies" task
3. Restart VS Code

### Import Errors
- Ensure Python interpreter is set to `.venv`
- Check PYTHONPATH in launch.json

### Debugging Issues
- Check Debug Console for errors
- Verify breakpoints are in executable code
- Use "justMyCode": false for library debugging