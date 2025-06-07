# Wizard Workflow Testing Checklist

## 🧙 Wizard Implementation Overview

The web UI chat client implements interactive wizards that:
1. Guide users through multi-step configurations
2. Validate input at each step
3. Provide feedback and error handling
4. Save configuration upon completion

## ✅ Wizard Test Scenarios

### 1. Proxmox Setup Wizard
- [ ] **Happy Path**
  - Trigger: "Setup Proxmox connection"
  - Enter valid host (192.168.10.200)
  - Enter valid credentials
  - Test connection succeeds
  - Credentials saved to profile
  - Can execute Proxmox commands after

- [ ] **Error Handling**
  - Invalid IP format
  - Unreachable host  
  - Wrong credentials
  - Network timeout
  - User cancellation

- [ ] **API Token Flow**
  - Choose token auth instead of password
  - Enter token in correct format
  - Verify no timeout issues
  - Token persists across sessions

### 2. Profile Management Wizard
- [ ] **Create New Profile**
  - Trigger: "Create new profile"
  - Name profile (dev/staging/prod)
  - Configure different endpoints
  - Set as active profile
  - Verify profile switching works

- [ ] **Switch Profiles**
  - List available profiles
  - Switch between profiles
  - Verify correct credentials loaded
  - Test commands use right profile

### 3. VM Creation Wizard
- [ ] **Basic VM Creation**
  - Trigger: "Create new VM"
  - Enter VM name
  - Select resources (CPU/RAM/disk)
  - Choose template
  - Select network
  - Confirm and create

- [ ] **Advanced Options**
  - GPU passthrough selection
  - Multiple disks
  - Network configuration
  - Cloud-init settings
  - SSH key injection

### 4. Service Deployment Wizard
- [ ] **Ollama Setup**
  - Deploy Ollama on VM
  - Select appropriate VM (with GPU)
  - Configure model
  - Set resource limits
  - Verify deployment

- [ ] **Application Deploy**
  - Select from templates
  - Configure parameters
  - Choose target VM
  - Post-deployment validation

## 🔍 Wizard Testing Patterns

### Input Validation Tests
```
Test: Invalid IP format
Input: "proxmox.local" (when IP expected)
Expected: Error message, re-prompt for valid IP
```

### State Management Tests
```
Test: Resume after cancellation
1. Start wizard
2. Complete 2 steps
3. Cancel wizard
4. Start wizard again
Expected: Fresh start, no state leakage
```

### Integration Tests
```
Test: Wizard → Tool execution
1. Complete Proxmox setup wizard
2. Immediately run "list VMs"
Expected: Command works with wizard-configured credentials
```

## 🐛 Common Wizard Issues

### 1. State Persistence
- Wizard state survives page refresh?
- Partial completion handling
- Multiple wizard instances

### 2. Validation Timing
- Real-time vs on-submit validation
- Async validation (connection tests)
- Clear error messages

### 3. Navigation
- Back button functionality
- Skip optional steps
- Progress indication

### 4. Data Flow
- Wizard data → MCP tools
- Profile integration
- Credential security

## 📝 Wizard Test Report Template

```markdown
## Wizard Test Report

**Date**: [Date]
**Wizard**: [Name]
**Tester**: [Name]

### Test Results

| Step | Input | Expected | Actual | Pass/Fail |
|------|-------|----------|--------|-----------|
| 1. Trigger | "Setup Proxmox" | Wizard starts | Wizard started | ✅ |
| 2. Host | "192.168.10.200" | Accepted | Accepted | ✅ |
| 3. Auth | "root@pam/***" | Test option shown | Test available | ✅ |
| 4. Test | Click test | Connection success | Connected | ✅ |
| 5. Save | Confirm | Saved to profile | Saved | ✅ |

### Issues Found
- [Issue 1 description]
- [Issue 2 description]

### Notes
- [Additional observations]
```

## 🚀 Automated Wizard Testing Ideas

Consider creating:
1. **Playwright/Selenium tests** for web UI wizards
2. **API tests** that simulate wizard flows
3. **State machine tests** for wizard logic
4. **Integration tests** combining wizards + MCP tools

Remember: Wizard workflows are critical for user onboarding and should be thoroughly tested!