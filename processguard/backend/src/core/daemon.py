import asyncio
import signal
import sys
from typing import Dict, List
from datetime import datetime
import json
from pathlib import Path

from .process_manager import ProcessManager
import os
if os.path.exists('/.dockerenv'):
    from .docker_system_monitor import DockerSystemMonitor as SystemMonitor
else:
    from .system_monitor import SystemMonitor
from .log_manager import LogManager
from .alerting import AlertManager, NotificationConfig
from ..models.process import ProcessConfig, ProcessType
from ..utils.logging import setup_logging, get_logger

class ProcessGuardDaemon:
    def __init__(self, config_file: str = "/etc/processguard/config.json"):
        self.config_file = config_file
        self.config = self._load_config()

        setup_logging(
            log_level=self.config.get("log_level", "INFO"),
            log_file=self.config.get("log_file", "/var/log/processguard/daemon.log")
        )

        self.logger = get_logger(__name__)

        self.process_manager = ProcessManager()
        self.system_monitor = SystemMonitor()
        self.log_manager = LogManager(self.config.get("log_base_dir", "/var/log/processguard"))

        notification_config = NotificationConfig(**self.config.get("notifications", {}))
        self.alert_manager = AlertManager(notification_config)

        self.running = False
        self.monitor_interval = self.config.get("monitor_interval", 10)

        self._setup_signal_handlers()

    def _load_config(self) -> Dict:
        default_config = {
            "log_level": "INFO",
            "log_file": "/var/log/processguard/daemon.log",
            "log_base_dir": "/var/log/processguard",
            "monitor_interval": 10,
            "processes": [],
            "notifications": {
                "email_enabled": False,
                "webhook_enabled": False,
                "slack_enabled": False
            }
        }

        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")
            print("Using default configuration")

        return default_config

    def _setup_signal_handlers(self):
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.stop()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _load_processes_from_config(self):
        for process_config in self.config.get("processes", []):
            try:
                process_type = ProcessType(process_config.get("type", "generic"))

                config = ProcessConfig(
                    name=process_config["name"],
                    command=process_config["command"],
                    working_dir=process_config["working_dir"],
                    process_type=process_type,
                    env_vars=process_config.get("env_vars", {}),
                    auto_restart=process_config.get("auto_restart", True),
                    max_restarts=process_config.get("max_restarts", 5),
                    restart_delay=process_config.get("restart_delay", 5),
                    log_file=process_config.get("log_file"),
                    redirect_output=process_config.get("redirect_output", True),
                    cpu_limit=process_config.get("cpu_limit"),
                    memory_limit=process_config.get("memory_limit"),
                    alert_on_failure=process_config.get("alert_on_failure", True),
                    alert_on_high_cpu=process_config.get("alert_on_high_cpu", True),
                    alert_on_high_memory=process_config.get("alert_on_high_memory", True),
                    cpu_threshold=process_config.get("cpu_threshold", 80.0),
                    memory_threshold=process_config.get("memory_threshold", 80.0)
                )

                if not config.log_file:
                    config.log_file = self.log_manager.create_log_file(config.name)

                self.process_manager.add_process(config)
                self.logger.info(f"Loaded process configuration: {config.name}")

            except Exception as e:
                self.logger.error(f"Failed to load process config: {e}")

    async def start(self):
        self.logger.info("Starting ProcessGuard daemon...")
        self.running = True

        self._load_processes_from_config()

        auto_start_processes = self.config.get("auto_start_processes", True)
        if auto_start_processes:
            for name in self.process_manager.get_all_processes().keys():
                self.process_manager.start_process(name)

        await self._main_loop()

    def stop(self):
        self.logger.info("Stopping ProcessGuard daemon...")
        self.running = False

    async def _main_loop(self):
        while self.running:
            try:
                await self._monitor_cycle()
                await asyncio.sleep(self.monitor_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(5)

        await self._cleanup()

    async def _monitor_cycle(self):
        system_metrics = self.system_monitor.get_system_metrics()
        await self.alert_manager.check_system_alerts(system_metrics)

        for name, process in self.process_manager.get_all_processes().items():
            self.process_manager.check_process_health(name)

            metrics = self.process_manager.get_process_metrics(name)
            if metrics:
                await self.alert_manager.check_process_alerts(process, metrics)

                if process.status.value == "running":
                    self.log_manager.write_log(
                        name,
                        f"CPU: {metrics.cpu_percent:.1f}%, Memory: {metrics.memory_mb:.1f}MB, Threads: {metrics.threads}",
                        "DEBUG"
                    )

        self.process_manager.auto_restart_failed_processes()

        if self.config.get("cleanup_logs", True):
            cleanup_days = self.config.get("log_retention_days", 7)
            self.log_manager.cleanup_old_logs(cleanup_days)

    async def _cleanup(self):
        self.logger.info("Cleaning up...")
        self.process_manager.cleanup()

    def add_process(self, config: ProcessConfig) -> bool:
        if not config.log_file:
            config.log_file = self.log_manager.create_log_file(config.name)

        return self.process_manager.add_process(config)

    def remove_process(self, name: str) -> bool:
        if self.process_manager.remove_process(name):
            self.log_manager.remove_process_logs(name)
            return True
        return False

    def start_process(self, name: str) -> bool:
        return self.process_manager.start_process(name)

    def stop_process(self, name: str, force: bool = False) -> bool:
        return self.process_manager.stop_process(name, force)

    def restart_process(self, name: str) -> bool:
        return self.process_manager.restart_process(name)

    def get_process_status(self, name: str = None):
        if name:
            if name in self.process_manager.processes:
                process = self.process_manager.processes[name]
                return {
                    "name": name,
                    "status": process.status.value,
                    "pid": process.pid,
                    "started_at": process.started_at.isoformat() if process.started_at else None,
                    "restart_count": process.restart_count,
                    "latest_metrics": process.get_latest_metrics()
                }
            return None
        else:
            status = {}
            for proc_name, process in self.process_manager.get_all_processes().items():
                status[proc_name] = {
                    "status": process.status.value,
                    "pid": process.pid,
                    "started_at": process.started_at.isoformat() if process.started_at else None,
                    "restart_count": process.restart_count
                }
            return status

    def get_system_status(self):
        system_info = self.system_monitor.get_system_info()
        system_metrics = self.system_monitor.get_system_metrics()

        return {
            "system_info": {
                "hostname": system_info.hostname,
                "platform": system_info.platform,
                "architecture": system_info.architecture,
                "cpu_count": system_info.cpu_count,
                "total_memory": system_info.total_memory,
                "boot_time": system_info.boot_time.isoformat(),
                "open_ports": [
                    {
                        "port": port.port,
                        "protocol": port.protocol,
                        "process_name": port.process_name,
                        "pid": port.pid
                    }
                    for port in system_info.open_ports
                ]
            },
            "system_metrics": {
                "timestamp": system_metrics.timestamp.isoformat(),
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "memory_total": system_metrics.memory_total,
                "memory_available": system_metrics.memory_available,
                "disk_usage": system_metrics.disk_usage,
                "network_io": system_metrics.network_io,
                "load_average": system_metrics.load_average,
                "uptime": system_metrics.uptime,
                "active_connections": system_metrics.active_connections
            }
        }

    def get_alerts(self, active_only: bool = True):
        if active_only:
            alerts = self.alert_manager.get_active_alerts()
        else:
            alerts = self.alert_manager.get_alert_history()

        return [
            {
                "id": alert.id,
                "type": alert.alert_type.value,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "process_name": alert.process_name,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged,
                "resolved": alert.resolved,
                "metadata": alert.metadata
            }
            for alert in alerts
        ]

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ProcessGuard Monitoring Daemon")
    parser.add_argument("-c", "--config", default="/etc/processguard/config.json",
                       help="Configuration file path")
    parser.add_argument("-d", "--daemon", action="store_true",
                       help="Run as daemon")

    args = parser.parse_args()

    daemon = ProcessGuardDaemon(args.config)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        daemon.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()