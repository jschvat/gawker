#!/bin/bash

# ProcessGuard Development Setup Script
set -e

echo "🚀 ProcessGuard Development Environment Setup"
echo "=============================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Create development data directories
echo "📁 Creating development directories..."
mkdir -p docker-data-dev/{config,logs,data}
mkdir -p docker-data-dev/logs/nginx

# Copy development configuration
echo "📄 Setting up development configuration..."
cp configs/development-config.json docker-data-dev/config/config.json

# Update paths for Docker environment
sed -i 's|/var/log/processguard|/app/logs|g' docker-data-dev/config/config.json 2>/dev/null || \
    sed -i '' 's|/var/log/processguard|/app/logs|g' docker-data-dev/config/config.json

echo "✅ Development configuration created"

# Create development docker-compose file
echo "🐳 Creating development Docker Compose configuration..."
cat > docker-compose.dev.yml << 'EOF'
version: '3.8'

services:
  processguard-dev:
    build: .
    container_name: processguard-dev
    restart: unless-stopped
    ports:
      - "7503:7500"  # Different port for dev
    volumes:
      # Development configuration
      - ./docker-data-dev/config:/app/config
      # Development logs
      - ./docker-data-dev/logs:/app/logs
      # Development data
      - ./docker-data-dev/data:/app/data
      # Host system access
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/host/root:ro
      # Hot reload for development (optional)
      - ./backend:/app/backend:ro
    environment:
      - HOST_PROC=/host/proc
      - HOST_SYS=/host/sys
      - HOST_ROOT=/host/root
      - TZ=UTC
      - PYTHONPATH=/app
      - LOG_LEVEL=DEBUG
    networks:
      - processguard-dev-network
    depends_on:
      - redis-dev
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7500/api/v1/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s

  redis-dev:
    image: redis:7-alpine
    container_name: processguard-redis-dev
    restart: unless-stopped
    volumes:
      - redis-dev-data:/data
    networks:
      - processguard-dev-network
    command: redis-server --appendonly yes

  nginx-dev:
    image: nginx:alpine
    container_name: processguard-nginx-dev
    restart: unless-stopped
    ports:
      - "7504:80"  # Different port for dev
    volumes:
      - ./docker-config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker-data-dev/logs/nginx:/var/log/nginx
    networks:
      - processguard-dev-network
    depends_on:
      - processguard-dev

volumes:
  redis-dev-data:
    driver: local

networks:
  processguard-dev-network:
    driver: bridge
EOF

# Set permissions
if [ "$(uname)" = "Linux" ]; then
    sudo chown -R 1000:1000 docker-data-dev/ 2>/dev/null || chown -R $(id -u):$(id -g) docker-data-dev/
fi

# Build and start development environment
echo "🏗️  Building ProcessGuard development environment..."
docker-compose -f docker-compose.dev.yml build

echo "🚀 Starting development services..."
docker-compose -f docker-compose.dev.yml up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 15

# Check health
echo "🔍 Checking development environment health..."
for i in {1..20}; do
    if curl -s http://localhost:7503/api/v1/health > /dev/null 2>&1; then
        echo "✅ ProcessGuard development environment is ready!"
        break
    fi

    if [ $i -eq 20 ]; then
        echo "❌ Development environment failed to start"
        echo "📋 Checking logs:"
        docker-compose -f docker-compose.dev.yml logs processguard-dev
        exit 1
    fi

    echo "   Waiting... ($i/20)"
    sleep 3
done

echo ""
echo "🎉 ProcessGuard Development Environment Ready!"
echo ""
echo "📊 Development Web Interface: http://localhost:7504"
echo "🔌 Development API:          http://localhost:7503/api/v1"
echo "📁 Development Data:         $(pwd)/docker-data-dev"
echo ""
echo "🛠️  Development Commands:"
echo "   View logs:     docker-compose -f docker-compose.dev.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose.dev.yml down"
echo "   Restart:       docker-compose -f docker-compose.dev.yml restart"
echo "   Shell access:  docker-compose -f docker-compose.dev.yml exec processguard-dev bash"
echo ""
echo "⚙️  Configuration:"
echo "   Edit: docker-data-dev/config/config.json"
echo "   Then: docker-compose -f docker-compose.dev.yml restart processguard-dev"
echo ""
echo "📝 Example Process Configuration:"
echo '   {
     "name": "my-nodejs-app",
     "command": "node server.js",
     "working_dir": "/host/root/home/user/my-app",
     "type": "nodejs",
     "env_vars": {
       "NODE_ENV": "development",
       "PORT": "3000"
     }
   }'
echo ""
echo "🔧 Development Features Enabled:"
echo "   ✅ Enhanced Node.js monitoring"
echo "   ✅ React dev server monitoring"
echo "   ✅ Crash pattern detection"
echo "   ✅ Intelligent restart strategies"
echo "   ✅ Bundle size monitoring"
echo "   ✅ Compilation time tracking"
echo "   ✅ Hot reload monitoring"
echo "   ✅ Debug logging"