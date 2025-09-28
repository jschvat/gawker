# Application Launch Methods in ProcessGuard

ProcessGuard supports multiple ways to launch applications via scripts and commands.

## 1. Direct Command Execution

### Simple Node.js App
```json
{
  "name": "my-api",
  "command": "node server.js",
  "working_dir": "/host/root/home/user/my-api"
}
```

### Python Application
```json
{
  "name": "python-worker",
  "command": "python app.py",
  "working_dir": "/host/root/home/user/worker"
}
```

## 2. NPM/Yarn Scripts

### Using package.json scripts
```json
{
  "name": "react-app",
  "command": "npm start",
  "working_dir": "/host/root/home/user/react-app"
}
```

### Production build
```json
{
  "name": "production-app",
  "command": "npm run start:prod",
  "working_dir": "/host/root/home/user/my-app"
}
```

### Using Yarn
```json
{
  "name": "yarn-app",
  "command": "yarn dev",
  "working_dir": "/host/root/home/user/yarn-app"
}
```

## 3. Shell Scripts

### Custom Launch Script
```json
{
  "name": "custom-app",
  "command": "./start.sh",
  "working_dir": "/host/root/home/user/my-app"
}
```

### Script with Arguments
```json
{
  "name": "script-with-args",
  "command": "./deploy.sh production --port 3000",
  "working_dir": "/host/root/opt/deployment"
}
```

## 4. Complex Launch Scenarios

### Java Application
```json
{
  "name": "java-service",
  "command": "java -Xmx2g -jar service.jar --spring.profiles.active=prod",
  "working_dir": "/host/root/opt/java-services"
}
```

### Go Binary
```json
{
  "name": "go-service",
  "command": "./service -config=prod.yml -port=8080",
  "working_dir": "/host/root/opt/go-services"
}
```

### Docker Compose (ProcessGuard managing Docker)
```json
{
  "name": "docker-stack",
  "command": "docker-compose up",
  "working_dir": "/host/root/home/user/docker-project"
}
```

## 5. Environment-Based Launches

### Development Environment
```json
{
  "name": "dev-server",
  "command": "npm run dev",
  "working_dir": "/host/root/home/user/project",
  "env_vars": {
    "NODE_ENV": "development",
    "DEBUG": "*",
    "PORT": "3000"
  }
}
```

### Production Environment
```json
{
  "name": "prod-server",
  "command": "node dist/server.js",
  "working_dir": "/host/root/opt/production",
  "env_vars": {
    "NODE_ENV": "production",
    "PORT": "7510"
  }
}
```

## 6. Multi-Command Scripts

### Bash Script Example
```bash
#!/bin/bash
# File: /home/user/my-app/start.sh

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    npm install
fi

# Build if needed
if [ ! -d "dist" ]; then
    npm run build
fi

# Start the application
npm start
```

```json
{
  "name": "smart-launcher",
  "command": "./start.sh",
  "working_dir": "/host/root/home/user/my-app"
}
```

## 7. Framework-Specific Examples

### Next.js
```json
{
  "name": "nextjs-app",
  "command": "npm run dev",
  "working_dir": "/host/root/home/user/nextjs-app",
  "env_vars": {
    "PORT": "3000"
  }
}
```

### Create React App
```json
{
  "name": "cra-app",
  "command": "npm start",
  "working_dir": "/host/root/home/user/react-app",
  "env_vars": {
    "PORT": "3000",
    "BROWSER": "none"
  }
}
```

### Vite
```json
{
  "name": "vite-app",
  "command": "npm run dev",
  "working_dir": "/host/root/home/user/vite-app",
  "env_vars": {
    "PORT": "5173"
  }
}
```

### Express.js
```json
{
  "name": "express-api",
  "command": "nodemon app.js",
  "working_dir": "/host/root/home/user/api",
  "env_vars": {
    "NODE_ENV": "development",
    "PORT": "3001"
  }
}
```

## 8. Advanced Script Patterns

### Conditional Launch Script
```bash
#!/bin/bash
# File: smart-start.sh

if [ "$NODE_ENV" = "production" ]; then
    # Production mode
    npm run build
    node dist/server.js
else
    # Development mode
    npm run dev
fi
```

### Multi-Service Launch
```bash
#!/bin/bash
# File: start-all.sh

# Start database
docker-compose up -d postgres

# Wait for DB
sleep 5

# Start API
cd api && npm start &

# Start frontend
cd ../frontend && npm start &

# Wait for all
wait
```

## 9. Error Handling in Scripts

### Robust Launch Script
```bash
#!/bin/bash
set -e  # Exit on error

LOG_FILE="/tmp/app-start.log"

log() {
    echo "$(date): $1" | tee -a "$LOG_FILE"
}

log "Starting application..."

# Check prerequisites
if [ ! -f "package.json" ]; then
    log "ERROR: package.json not found"
    exit 1
fi

# Install dependencies
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install || exit 1
fi

# Start application
log "Starting server..."
exec npm start
```

## 10. ProcessGuard Script Integration

### Using the Enhanced Process Manager
```python
# In ProcessGuard, you can use the enhanced manager
enhanced_manager = EnhancedProcessManager()

# Start a Node.js app with intelligent monitoring
enhanced_manager.start_nodejs_app("my-api", {
    "command": "./start.sh",
    "working_dir": "/home/user/my-api",
    "port": 3000,
    "auto_restart": True
})

# Start a React dev server with development features
enhanced_manager.start_react_dev_server("frontend", {
    "command": "npm start",
    "working_dir": "/home/user/frontend",
    "port": 3000
})
```

## Important Notes

1. **File Permissions**: Make sure scripts are executable
   ```bash
   chmod +x start.sh
   ```

2. **Working Directory**: ProcessGuard executes commands in the specified working directory

3. **Environment Variables**: Use `env_vars` to set environment variables

4. **Path Resolution**:
   - Relative paths are resolved from `working_dir`
   - Use absolute paths for system commands

5. **Output Capture**: ProcessGuard captures stdout/stderr from your scripts

6. **Error Codes**: Scripts should exit with proper error codes (0 = success, >0 = error)