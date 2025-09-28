# Crash Management Examples

ProcessGuard provides intelligent crash management with dependency-aware shutdown policies.

## Basic Crash Policies

### 1. Simple Crash Threshold
```json
{
  "name": "my-api",
  "command": "node server.js",
  "working_dir": "/host/root/home/user/api",
  "crash_policy": {
    "max_crashes": 5,
    "time_window_minutes": 10,
    "action_on_threshold": "disable"
  }
}
```
**Result**: If the API crashes 5 times in 10 minutes, it stays OFF permanently.

### 2. Quarantine Strategy
```json
{
  "name": "unstable-service",
  "command": "npm start",
  "working_dir": "/host/root/home/user/service",
  "crash_policy": {
    "max_crashes": 3,
    "time_window_minutes": 5,
    "action_on_threshold": "quarantine",
    "quarantine_duration_minutes": 30
  }
}
```
**Result**: After 3 crashes in 5 minutes, service is quarantined for 30 minutes, then can restart.

## Dependency-Based Shutdown

### 3. Critical Service with Dependents
```json
{
  "name": "database-service",
  "command": "node db-server.js",
  "crash_policy": {
    "max_crashes": 2,
    "time_window_minutes": 15,
    "action_on_threshold": "kill_dependencies",
    "kill_dependencies": true
  },
  "dependencies": []
}
```

```json
{
  "name": "api-service",
  "command": "node api.js",
  "crash_policy": {
    "max_crashes": 5,
    "time_window_minutes": 10,
    "action_on_threshold": "disable"
  },
  "dependencies": ["database-service"]
}
```

```json
{
  "name": "frontend",
  "command": "npm start",
  "crash_policy": {
    "max_crashes": 8,
    "time_window_minutes": 5,
    "action_on_threshold": "disable"
  },
  "dependencies": ["api-service", "database-service"]
}
```

**Result**: If `database-service` crashes 2 times in 15 minutes:
- `database-service` is disabled
- `api-service` is automatically killed (depends on database)
- `frontend` is automatically killed (depends on both)

## Real-World Scenarios

### 4. Node.js Backend + React Frontend
```json
{
  "processes": [
    {
      "name": "nodejs-backend",
      "command": "node server.js",
      "working_dir": "/host/root/home/user/backend",
      "crash_policy": {
        "max_crashes": 3,
        "time_window_minutes": 10,
        "action_on_threshold": "kill_dependencies",
        "kill_dependencies": true
      }
    },
    {
      "name": "react-frontend",
      "command": "npm start",
      "working_dir": "/host/root/home/user/frontend",
      "crash_policy": {
        "max_crashes": 10,
        "time_window_minutes": 5,
        "action_on_threshold": "quarantine",
        "quarantine_duration_minutes": 10
      },
      "dependencies": ["nodejs-backend"]
    }
  ]
}
```

**Behavior**:
- If backend crashes 3 times in 10 minutes → backend disabled, frontend killed
- If frontend crashes 10 times in 5 minutes → frontend quarantined for 10 minutes
- Backend can restart independently, frontend needs backend to be running

### 5. Microservices Architecture
```json
{
  "processes": [
    {
      "name": "auth-service",
      "command": "node auth.js",
      "crash_policy": {
        "max_crashes": 2,
        "time_window_minutes": 20,
        "action_on_threshold": "kill_dependencies"
      }
    },
    {
      "name": "user-service",
      "command": "node users.js",
      "crash_policy": {
        "max_crashes": 4,
        "time_window_minutes": 10,
        "action_on_threshold": "disable"
      },
      "dependencies": ["auth-service"]
    },
    {
      "name": "api-gateway",
      "command": "node gateway.js",
      "crash_policy": {
        "max_crashes": 5,
        "time_window_minutes": 10,
        "action_on_threshold": "disable"
      },
      "dependencies": ["auth-service", "user-service"]
    }
  ]
}
```

**Cascade Effect**: If auth-service fails → user-service + api-gateway are killed

## Configuration Options

### Crash Actions
- **`disable`**: Process stays OFF permanently until manually enabled
- **`quarantine`**: Process stays OFF for specified duration, then can restart
- **`kill_dependencies`**: Disable process AND kill all dependent processes

### Time-Based Policies
```json
{
  "crash_policy": {
    "max_crashes": 5,              // Maximum crashes allowed
    "time_window_minutes": 10,     // Within this time window
    "action_on_threshold": "disable"
  }
}
```

### Development vs Production
```json
{
  "development": {
    "max_crashes": 10,             // More lenient for dev
    "time_window_minutes": 5,
    "action_on_threshold": "quarantine",
    "quarantine_duration_minutes": 5
  },
  "production": {
    "max_crashes": 3,              // Stricter for production
    "time_window_minutes": 15,
    "action_on_threshold": "kill_dependencies"
  }
}
```

## Admin Controls

### Force Enable Disabled Process
```bash
# Via API
curl -X POST http://localhost:7501/api/v1/processes/my-api/force-enable

# Via Web Interface
# Go to process → Click "Force Enable"
```

### Reset Crash History
```bash
# Clear crash history for fresh start
curl -X POST http://localhost:7501/api/v1/processes/my-api/reset-crashes
```

### Override Dependencies
```bash
# Start process ignoring dependency requirements
curl -X POST http://localhost:7501/api/v1/processes/my-api/start?ignore_dependencies=true
```

## Monitoring Crash Status

### Get Crash Statistics
```bash
curl http://localhost:7501/api/v1/processes/my-api/crash-stats
```

### View Disabled Processes
```bash
curl http://localhost:7501/api/v1/system/disabled-processes
```

### Check Quarantined Processes
```bash
curl http://localhost:7501/api/v1/system/quarantined-processes
```

## Advanced Features

### Smart Crash Detection
ProcessGuard automatically detects crash types:
- **Port conflicts** → Delayed restart with port check
- **Missing dependencies** → Don't restart until fixed
- **Memory issues** → Restart with memory limits
- **Code errors** → Don't restart until code is fixed

### Escalation Policies
```json
{
  "crash_policy": {
    "escalation_enabled": true,
    "escalation_rules": [
      {
        "after_crashes": 3,
        "action": "notify_team"
      },
      {
        "after_crashes": 5,
        "action": "page_oncall"
      },
      {
        "after_crashes": 8,
        "action": "emergency_shutdown"
      }
    ]
  }
}
```

This gives you enterprise-level fault tolerance and prevents cascading failures in your application stack! 🛡️