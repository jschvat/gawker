#!/bin/bash
# Smart Application Launcher - Detects app type and starts appropriately

set -e

APP_NAME=${1:-"unknown-app"}
MODE=${NODE_ENV:-development}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [LAUNCHER] $1"
}

detect_app_type() {
    if [ -f "package.json" ]; then
        # Check for React
        if grep -q "react-scripts\|@vitejs/plugin-react\|next" package.json; then
            if grep -q "next" package.json; then
                echo "nextjs"
            elif grep -q "@vitejs/plugin-react" package.json; then
                echo "vite-react"
            else
                echo "react"
            fi
        # Check for Node.js backend patterns
        elif grep -q "express\|fastify\|koa\|hapi" package.json; then
            echo "nodejs-api"
        # Generic Node.js
        else
            echo "nodejs"
        fi
    elif [ -f "go.mod" ]; then
        echo "go"
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        echo "python"
    elif [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
        echo "java"
    elif [ -f "Cargo.toml" ]; then
        echo "rust"
    else
        echo "unknown"
    fi
}

start_react_app() {
    log "Detected React application"

    # Set React-specific environment variables
    export BROWSER=none
    export FAST_REFRESH=true

    if [ "$MODE" = "development" ]; then
        export GENERATE_SOURCEMAP=true

        if grep -q '"dev"' package.json; then
            exec npm run dev
        else
            exec npm start
        fi
    else
        # Production mode
        if [ ! -d "build" ] && [ ! -d "dist" ]; then
            log "Building for production..."
            npm run build
        fi

        # Serve production build
        if command -v serve &> /dev/null; then
            exec serve -s build -p ${PORT:-3000}
        else
            log "Installing serve package..."
            npx serve -s build -p ${PORT:-3000}
        fi
    fi
}

start_nextjs_app() {
    log "Detected Next.js application"

    if [ "$MODE" = "development" ]; then
        exec npm run dev
    else
        if [ ! -d ".next" ]; then
            log "Building for production..."
            npm run build
        fi
        exec npm start
    fi
}

start_vite_react_app() {
    log "Detected Vite React application"

    if [ "$MODE" = "development" ]; then
        exec npm run dev
    else
        if [ ! -d "dist" ]; then
            log "Building for production..."
            npm run build
        fi
        exec npm run preview
    fi
}

start_nodejs_api() {
    log "Detected Node.js API application"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log "Installing dependencies..."
        npm install
    fi

    if [ "$MODE" = "development" ]; then
        # Try to use nodemon if available
        if grep -q "nodemon" package.json; then
            exec npm run dev 2>/dev/null || exec nodemon
        elif command -v nodemon &> /dev/null; then
            exec nodemon
        else
            exec npm start
        fi
    else
        exec npm start
    fi
}

start_python_app() {
    log "Detected Python application"

    # Check for virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    # Install dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    # Find main file
    if [ -f "app.py" ]; then
        exec python app.py
    elif [ -f "main.py" ]; then
        exec python main.py
    elif [ -f "server.py" ]; then
        exec python server.py
    else
        log "ERROR: No main Python file found"
        exit 1
    fi
}

start_go_app() {
    log "Detected Go application"

    if [ "$MODE" = "development" ]; then
        exec go run .
    else
        # Build and run
        go build -o app .
        exec ./app
    fi
}

# Main execution
log "Smart launcher starting for $APP_NAME in $MODE mode..."
log "Working directory: $(pwd)"

APP_TYPE=$(detect_app_type)
log "Detected application type: $APP_TYPE"

case $APP_TYPE in
    "react")
        start_react_app
        ;;
    "nextjs")
        start_nextjs_app
        ;;
    "vite-react")
        start_vite_react_app
        ;;
    "nodejs-api"|"nodejs")
        start_nodejs_api
        ;;
    "python")
        start_python_app
        ;;
    "go")
        start_go_app
        ;;
    *)
        log "Unknown application type. Attempting generic start..."
        if [ -f "package.json" ]; then
            exec npm start
        else
            log "ERROR: Don't know how to start this application"
            exit 1
        fi
        ;;
esac