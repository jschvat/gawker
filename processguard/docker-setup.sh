#!/bin/bash

# ProcessGuard Docker Setup Script
set -e

echo "🐳 ProcessGuard Docker Setup"
echo "=============================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create data directories
echo "📁 Creating data directories..."
mkdir -p docker-data/{config,logs,data}
mkdir -p docker-data/logs/nginx
mkdir -p docker-config/ssl

# Copy example configuration if it doesn't exist
if [ ! -f "docker-data/config/config.json" ]; then
    echo "📄 Creating default configuration..."
    cp configs/config.example.json docker-data/config/config.json

    # Update paths for Docker environment
    sed -i 's|/var/log/processguard|/app/logs|g' docker-data/config/config.json
    sed -i 's|/etc/processguard|/app/config|g' docker-data/config/config.json

    echo "✅ Configuration created at docker-data/config/config.json"
    echo "   Please edit this file to configure your processes and notifications"
else
    echo "✅ Configuration already exists"
fi

# Set proper permissions
echo "🔐 Setting permissions..."
if [ "$(uname)" = "Linux" ]; then
    # On Linux, set ownership to match container user
    sudo chown -R 1000:1000 docker-data/ 2>/dev/null || chown -R $(id -u):$(id -g) docker-data/
fi

# Build and start services
echo "🏗️  Building ProcessGuard..."
docker-compose build

echo "🚀 Starting ProcessGuard services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🔍 Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:7500/api/v1/health > /dev/null 2>&1; then
        echo "✅ ProcessGuard is healthy!"
        break
    fi

    if [ $i -eq 30 ]; then
        echo "❌ ProcessGuard failed to start properly"
        echo "📋 Checking logs:"
        docker-compose logs processguard
        exit 1
    fi

    echo "   Waiting... ($i/30)"
    sleep 2
done

echo ""
echo "🎉 ProcessGuard is running!"
echo ""
echo "📊 Web Interface: http://localhost:7501"
echo "🔌 API Endpoint:  http://localhost:7501/api/v1"
echo "📁 Data Directory: $(pwd)/docker-data"
echo ""
echo "📖 Useful Commands:"
echo "   View logs:     docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart:       docker-compose restart"
echo "   Update config: edit docker-data/config/config.json then restart"
echo ""
echo "⚙️  Configuration:"
echo "   Edit: docker-data/config/config.json"
echo "   Then run: docker-compose restart processguard"