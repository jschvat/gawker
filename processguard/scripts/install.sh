#!/bin/bash

# ProcessGuard Installation Script
# Requires sudo privileges

set -e

# Configuration
INSTALL_DIR="/opt/processguard"
CONFIG_DIR="/etc/processguard"
LOG_DIR="/var/log/processguard"
USER="processguard"
SERVICE_NAME="processguard"

echo "Installing ProcessGuard..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Check for Python 3.8+
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "Error: Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "✓ Python $python_version found"

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nginx

# Create user
if ! id "$USER" &>/dev/null; then
    echo "Creating system user: $USER"
    sudo useradd --system --shell /bin/bash --home-dir $INSTALL_DIR --create-home $USER
else
    echo "✓ User $USER already exists"
fi

# Create directories
echo "Creating directories..."
sudo mkdir -p $INSTALL_DIR $CONFIG_DIR $LOG_DIR
sudo chown -R $USER:$USER $INSTALL_DIR $LOG_DIR
sudo chmod 755 $CONFIG_DIR

# Copy application files
echo "Installing application files..."
sudo cp -r backend $INSTALL_DIR/
sudo cp -r frontend $INSTALL_DIR/
sudo cp requirements.txt $INSTALL_DIR/

# Set ownership
sudo chown -R $USER:$USER $INSTALL_DIR

# Create Python virtual environment
echo "Creating Python virtual environment..."
sudo -u $USER python3 -m venv $INSTALL_DIR/venv
sudo -u $USER $INSTALL_DIR/venv/bin/pip install --upgrade pip
sudo -u $USER $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt

# Install Node.js and build frontend
echo "Installing Node.js and building frontend..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

cd $INSTALL_DIR/frontend
sudo -u $USER npm install
sudo -u $USER npm run build

# Copy configuration files
echo "Setting up configuration..."
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    sudo cp configs/config.example.json $CONFIG_DIR/config.json
    echo "✓ Configuration file created at $CONFIG_DIR/config.json"
    echo "  Please edit this file to configure your processes and notifications"
else
    echo "✓ Configuration file already exists at $CONFIG_DIR/config.json"
fi

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=ProcessGuard Monitoring Daemon
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin
ExecStart=$INSTALL_DIR/venv/bin/python -m backend.src.api.main --config $CONFIG_DIR/config.json --port 7500
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Configure nginx
echo "Configuring nginx..."
sudo tee /etc/nginx/sites-available/processguard > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:7500;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/v1/ws/ {
        proxy_pass http://127.0.0.1:7500;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/processguard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Create CLI wrapper
echo "Creating CLI wrapper..."
sudo tee /usr/local/bin/processguard > /dev/null <<EOF
#!/bin/bash
cd $INSTALL_DIR
exec $INSTALL_DIR/venv/bin/python -m backend.src.core.daemon --config $CONFIG_DIR/config.json "\$@"
EOF

sudo chmod +x /usr/local/bin/processguard

# Enable and start services
echo "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl enable nginx

echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit the configuration file: sudo nano $CONFIG_DIR/config.json"
echo "2. Add your processes and configure notifications"
echo "3. Start the service: sudo systemctl start $SERVICE_NAME"
echo "4. Check the status: sudo systemctl status $SERVICE_NAME"
echo "5. Access the web interface at: http://your-server-ip"
echo ""
echo "Useful commands:"
echo "  - View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  - Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  - CLI access: processguard --help"