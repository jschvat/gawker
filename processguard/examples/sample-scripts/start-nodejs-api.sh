#!/bin/bash
# Sample Node.js API Launch Script

set -e  # Exit on any error

# Configuration
APP_NAME="nodejs-api"
PORT=${PORT:-3001}
NODE_ENV=${NODE_ENV:-development}

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}

log "Starting $APP_NAME on port $PORT in $NODE_ENV mode..."

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    log "ERROR: Node.js is not installed"
    exit 1
fi

# Check if package.json exists
if [ ! -f "package.json" ]; then
    log "ERROR: package.json not found in $(pwd)"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        log "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

# Check if main file exists
MAIN_FILE=$(node -p "require('./package.json').main || 'index.js'")
if [ ! -f "$MAIN_FILE" ]; then
    log "ERROR: Main file $MAIN_FILE not found"
    exit 1
fi

# Set environment variables
export NODE_ENV=$NODE_ENV
export PORT=$PORT

# Start the application
log "Starting application: node $MAIN_FILE"
exec node "$MAIN_FILE"