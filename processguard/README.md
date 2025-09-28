# ProcessGuard

ProcessGuard is a comprehensive process monitoring and management system designed for mission-critical applications. It provides real-time monitoring, automatic restart capabilities, alerting, and a web-based dashboard for managing your applications.

## Features

### Core Monitoring
- **Multi-language support**: Node.js, Python, Java, Go, Rust, and generic processes
- **Real-time metrics**: CPU usage, memory consumption, thread count, open files, network connections
- **System monitoring**: Overall system health, disk usage, network I/O, open ports
- **Process lifecycle management**: Start, stop, restart processes with configurable policies

### Advanced Capabilities
- **Auto-restart**: Configurable restart policies with failure thresholds
- **Log management**: Centralized logging with rotation and retention policies
- **Output redirection**: Capture and store application output
- **Resource monitoring**: Track CPU and memory usage with configurable thresholds
- **Port monitoring**: Track which ports are open and which processes are using them

### Alerting & Notifications
- **Multi-channel alerts**: Email, Slack, webhooks
- **Configurable thresholds**: CPU, memory, disk usage alerts
- **Alert management**: Acknowledge and resolve alerts through the web interface
- **Smart notifications**: Cooldown periods to prevent spam

### Web Interface
- **Real-time dashboard**: Live metrics and process status
- **Process management**: Start/stop/restart processes through the UI
- **Log viewing**: Browse and search application logs
- **Alert management**: View and manage active alerts
- **System overview**: Comprehensive system health metrics

## Installation

### Prerequisites
- Linux server (Ubuntu 18.04+ recommended)
- Python 3.8 or higher
- Node.js 16+ (for building the frontend)
- Sudo privileges

### Quick Install
```bash
# Clone the repository
git clone https://github.com/your-org/processguard.git
cd processguard

# Run the installation script
chmod +x scripts/install.sh
./scripts/install.sh
```

### Manual Installation
1. **Install system dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-venv nginx nodejs npm
   ```

2. **Create system user**:
   ```bash
   sudo useradd --system --shell /bin/bash --home-dir /opt/processguard --create-home processguard
   ```

3. **Setup directories**:
   ```bash
   sudo mkdir -p /opt/processguard /etc/processguard /var/log/processguard
   sudo chown processguard:processguard /opt/processguard /var/log/processguard
   ```

4. **Install Python dependencies**:
   ```bash
   cd /opt/processguard
   sudo -u processguard python3 -m venv venv
   sudo -u processguard venv/bin/pip install -r requirements.txt
   ```

5. **Build frontend**:
   ```bash
   cd frontend
   sudo -u processguard npm install
   sudo -u processguard npm run build
   ```

6. **Setup systemd service**:
   ```bash
   sudo cp scripts/processguard.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable processguard
   ```

## Configuration

### Main Configuration
Edit `/etc/processguard/config.json`:

```json
{
  "log_level": "INFO",
  "monitor_interval": 10,
  "auto_start_processes": true,
  "processes": [
    {
      "name": "my-app",
      "command": "node server.js",
      "working_dir": "/home/user/my-app",
      "type": "nodejs",
      "auto_restart": true,
      "max_restarts": 5,
      "cpu_threshold": 80.0,
      "memory_threshold": 80.0
    }
  ],
  "notifications": {
    "email_enabled": true,
    "email_smtp_server": "smtp.gmail.com",
    "email_recipients": ["admin@example.com"]
  }
}
```

### Process Configuration Options
- **name**: Unique identifier for the process
- **command**: Command to execute
- **working_dir**: Directory to run the command in
- **type**: Process type (nodejs, python, java, go, rust, generic)
- **env_vars**: Environment variables to set
- **auto_restart**: Enable automatic restart on failure
- **max_restarts**: Maximum restart attempts
- **restart_delay**: Delay between restart attempts (seconds)
- **cpu_threshold**: CPU usage alert threshold (%)
- **memory_threshold**: Memory usage alert threshold (%)
- **log_file**: Custom log file path (optional)

### Notification Configuration
Support for multiple notification channels:

#### Email
```json
"notifications": {
  "email_enabled": true,
  "email_smtp_server": "smtp.gmail.com",
  "email_smtp_port": 587,
  "email_username": "your-email@gmail.com",
  "email_password": "app-password",
  "email_recipients": ["admin@example.com"],
  "email_use_tls": true
}
```

#### Slack
```json
"notifications": {
  "slack_enabled": true,
  "slack_webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/URL"
}
```

#### Webhooks
```json
"notifications": {
  "webhook_enabled": true,
  "webhook_url": "https://your-webhook-endpoint.com",
  "webhook_headers": {
    "Authorization": "Bearer your-token"
  }
}
```

## Usage

### Starting the Service
```bash
sudo systemctl start processguard
sudo systemctl status processguard
```

### Web Interface
Access the web interface at `http://your-server-ip`. The interface provides:

- **Dashboard**: Overview of system and process health
- **Processes**: Manage individual processes
- **System**: Detailed system metrics
- **Alerts**: View and manage alerts
- **Logs**: Browse application logs

### Command Line Interface
```bash
# View process status
processguard status

# Add a new process
processguard add-process --name myapp --command "python app.py" --dir /home/user/myapp

# Start a process
processguard start myapp

# Stop a process
processguard stop myapp

# View logs
processguard logs myapp --tail 100
```

### API Access
ProcessGuard provides a REST API for integration:

```bash
# Get all processes
curl http://localhost:8000/api/v1/processes

# Start a process
curl -X POST http://localhost:8000/api/v1/processes/myapp/start

# Get system metrics
curl http://localhost:8000/api/v1/system/metrics
```

## Monitoring Capabilities

### Process Metrics
- CPU usage percentage
- Memory usage (RSS, percentage)
- Thread count
- Open file descriptors
- Network connections
- Process uptime
- Exit codes and restart history

### System Metrics
- Overall CPU usage
- Memory usage and availability
- Disk usage per mount point
- Network I/O statistics
- Load averages
- Open ports and listening services
- Active network connections

### Log Management
- Automatic log rotation
- Configurable retention policies
- Real-time log streaming
- Log aggregation across processes
- Search and filtering capabilities

## Security

ProcessGuard runs with minimal privileges:
- Dedicated system user (`processguard`)
- Restricted file system access
- No new privileges escalation
- Secure defaults for systemd service

## Troubleshooting

### Service Issues
```bash
# Check service status
sudo systemctl status processguard

# View logs
sudo journalctl -u processguard -f

# Restart service
sudo systemctl restart processguard
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R processguard:processguard /opt/processguard /var/log/processguard

# Check file permissions
ls -la /etc/processguard/config.json
```

### Configuration Issues
- Validate JSON syntax in config file
- Check file paths and permissions
- Verify process commands can be executed
- Test notification settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues: https://github.com/your-org/processguard/issues
- Documentation: https://docs.processguard.io
- Community: https://community.processguard.io