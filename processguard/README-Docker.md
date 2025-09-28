# ProcessGuard - Docker Installation

ProcessGuard can be run completely in Docker containers, providing full isolation from your host system while still monitoring host processes and system metrics.

## 🐳 Docker Features

- **Complete Isolation**: No changes to your host system
- **Host System Monitoring**: Access to host CPU, memory, disk, and process information
- **Web Interface**: React-based dashboard accessible via browser
- **Persistent Data**: Configuration and logs stored in Docker volumes
- **Auto-restart**: Containers restart automatically on failure
- **Health Checks**: Built-in health monitoring for all services

## 📋 Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- Linux host (for process monitoring)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/processguard.git
cd processguard

# Run the setup script
chmod +x docker-setup.sh
./docker-setup.sh
```

The setup script will:
1. ✅ Check Docker/Docker Compose installation
2. 📁 Create necessary directories
3. 📄 Generate default configuration
4. 🏗️ Build the Docker images
5. 🚀 Start all services
6. 🔍 Verify health status

## 🎯 Access Points

After setup completes:

- **Web Interface**: http://localhost:7501
- **API**: http://localhost:7501/api/v1
- **Health Check**: http://localhost:7501/health

## 📁 Directory Structure

```
processguard/
├── docker-data/              # Persistent data (created by setup)
│   ├── config/
│   │   └── config.json       # Main configuration
│   ├── logs/                 # Application logs
│   └── data/                 # Database and cache
├── docker-config/            # Docker configuration
│   └── nginx.conf           # Nginx configuration
└── docker-compose.yml       # Service definitions
```

## ⚙️ Configuration

### Edit Configuration
```bash
# Edit the main configuration file
nano docker-data/config/config.json

# Restart to apply changes
docker-compose restart processguard
```

### Example Process Configuration
```json
{
  "processes": [
    {
      "name": "my-nodejs-app",
      "command": "node /host/root/home/user/myapp/server.js",
      "working_dir": "/host/root/home/user/myapp",
      "type": "nodejs",
      "auto_restart": true,
      "cpu_threshold": 80.0,
      "memory_threshold": 80.0
    }
  ]
}
```

**Important**: Use `/host/root/` prefix for absolute paths to access host filesystem from container.

## 🔧 Management Commands

### Service Management
```bash
# View status
docker-compose ps

# View logs
docker-compose logs -f processguard

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and rebuild
git pull
docker-compose build
docker-compose up -d
```

### Process Management
```bash
# Access container shell
docker-compose exec processguard bash

# View process logs
docker-compose exec processguard cat /app/logs/my-process.log

# Edit configuration
docker-compose exec processguard nano /app/config/config.json
```

## 🔐 Security

### Container Security
- Runs as non-root user (UID 1000)
- Limited filesystem access
- No privileged mode required
- Network isolation

### Host Access
The container mounts host directories read-only:
- `/proc` → `/host/proc` (process information)
- `/sys` → `/host/sys` (system information)
- `/` → `/host/root` (filesystem access for monitored processes)

## 📊 Monitoring Capabilities

### What ProcessGuard Can Monitor in Docker

✅ **Host System Metrics**:
- CPU usage and load
- Memory usage
- Disk usage
- Network I/O
- Open ports

✅ **Host Processes**:
- Any process running on the host
- Process CPU/memory usage
- Process lifecycle management
- Log collection

✅ **Container Processes**:
- Other Docker containers
- Host-native applications
- System services

### Example Monitored Applications
- Node.js applications
- Python services
- Java applications
- Go binaries
- System daemons
- Other Docker containers

## 🚨 Alerting Setup

### Email Notifications
```json
{
  "notifications": {
    "email_enabled": true,
    "email_smtp_server": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_username": "your-email@gmail.com",
    "email_password": "app-password",
    "email_recipients": ["admin@example.com"]
  }
}
```

### Slack Integration
```json
{
  "notifications": {
    "slack_enabled": true,
    "slack_webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/URL"
  }
}
```

## 🔧 Troubleshooting

### Check Service Health
```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs processguard
docker-compose logs nginx
docker-compose logs redis

# Check container health
docker-compose exec processguard curl -f http://localhost:7500/api/v1/health
```

### Common Issues

**1. Permission Denied**
```bash
# Fix data directory permissions
sudo chown -R 1000:1000 docker-data/
```

**2. Port Already in Use**
```bash
# Check what's using port 80
sudo netstat -tlnp | grep :80

# Use different ports in docker-compose.yml
ports:
  - "8080:80"  # Change 80 to 8080
```

**3. Host Process Access Issues**
```bash
# Verify host mounts
docker-compose exec processguard ls -la /host/proc
docker-compose exec processguard ls -la /host/root
```

**4. Configuration Not Loading**
```bash
# Check config file syntax
cat docker-data/config/config.json | python -m json.tool

# Check container can read config
docker-compose exec processguard cat /app/config/config.json
```

### Debug Mode
```bash
# Run with debug logging
docker-compose exec processguard python -m backend.src.api.main \
  --config /app/config/config.json --reload
```

## 🔄 Updates

### Update ProcessGuard
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d

# Check health
docker-compose exec processguard curl -f http://localhost:7500/api/v1/health
```

### Backup Configuration
```bash
# Backup your configuration and logs
tar -czf processguard-backup.tar.gz docker-data/

# Restore from backup
tar -xzf processguard-backup.tar.gz
```

## 🌐 Production Deployment

### Enable HTTPS
1. Place SSL certificates in `docker-config/ssl/`
2. Edit `docker-config/nginx.conf` to enable HTTPS
3. Restart: `docker-compose restart nginx`

### Resource Limits
Add to `docker-compose.yml`:
```yaml
services:
  processguard:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

### Monitoring the Monitor
```bash
# Monitor ProcessGuard itself
docker stats processguard
docker-compose exec processguard top
```

This Docker setup provides complete isolation while maintaining full monitoring capabilities of your host system and processes.