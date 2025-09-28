#!/bin/bash
# Sample React Development Server Launch Script

set -e

# Configuration
APP_NAME="react-frontend"
PORT=${PORT:-3000}
BROWSER=${BROWSER:-none}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$APP_NAME] $1"
}

log "Starting React development server on port $PORT..."

# Check prerequisites
if [ ! -f "package.json" ]; then
    log "ERROR: package.json not found"
    exit 1
fi

# Check if this is a React app
if ! grep -q "react" package.json; then
    log "WARNING: This doesn't appear to be a React application"
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log "Installing dependencies..."

    # Detect package manager
    if [ -f "yarn.lock" ]; then
        yarn install
    elif [ -f "pnpm-lock.yaml" ]; then
        pnpm install
    else
        npm install
    fi
fi

# Set environment variables for React
export PORT=$PORT
export BROWSER=$BROWSER
export FAST_REFRESH=true
export GENERATE_SOURCEMAP=true

# Check if we have a dev script
if grep -q '"dev"' package.json; then
    log "Starting with npm run dev..."
    exec npm run dev
elif grep -q '"start"' package.json; then
    log "Starting with npm start..."
    exec npm start
else
    log "ERROR: No start or dev script found in package.json"
    exit 1
fi