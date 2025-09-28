import smtplib
import json
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dataclasses import dataclass, field
from enum import Enum

from ..models.process import ProcessMetrics, ManagedProcess
from ..models.system import SystemMetrics
from ..utils.logging import get_logger

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertType(Enum):
    PROCESS_FAILED = "process_failed"
    PROCESS_RESTARTED = "process_restarted"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    SYSTEM_HIGH_CPU = "system_high_cpu"
    SYSTEM_HIGH_MEMORY = "system_high_memory"
    DISK_FULL = "disk_full"
    PROCESS_UNRESPONSIVE = "process_unresponsive"

@dataclass
class Alert:
    id: str
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    process_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotificationConfig:
    email_enabled: bool = False
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = field(default_factory=list)
    email_use_tls: bool = True

    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_headers: Dict[str, str] = field(default_factory=dict)

    slack_enabled: bool = False
    slack_webhook_url: str = ""

class AlertManager:
    def __init__(self, notification_config: NotificationConfig):
        self.notification_config = notification_config
        self.logger = get_logger(__name__)

        self.alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self.alert_handlers: Dict[AlertType, List[Callable]] = {}

        self._alert_cooldowns: Dict[str, datetime] = {}
        self._cooldown_duration = timedelta(minutes=5)

    def add_alert_handler(self, alert_type: AlertType, handler: Callable):
        if alert_type not in self.alert_handlers:
            self.alert_handlers[alert_type] = []
        self.alert_handlers[alert_type].append(handler)

    async def create_alert(self, alert_type: AlertType, level: AlertLevel,
                          title: str, message: str, process_name: str = None,
                          metadata: Dict[str, Any] = None) -> Alert:

        alert_key = f"{alert_type.value}:{process_name or 'system'}"

        if alert_key in self._alert_cooldowns:
            if datetime.now() < self._alert_cooldowns[alert_key]:
                self.logger.debug(f"Alert {alert_key} is in cooldown, skipping")
                return None

        alert_id = f"{alert_type.value}_{datetime.now().timestamp()}"

        alert = Alert(
            id=alert_id,
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            process_name=process_name,
            metadata=metadata or {}
        )

        self.alerts.append(alert)
        self.alert_history.append(alert)

        self._alert_cooldowns[alert_key] = datetime.now() + self._cooldown_duration

        await self._send_notifications(alert)

        if alert_type in self.alert_handlers:
            for handler in self.alert_handlers[alert_type]:
                try:
                    await handler(alert)
                except Exception as e:
                    self.logger.error(f"Alert handler failed: {e}")

        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]

        self.logger.info(f"Created alert: {alert.title}")
        return alert

    async def _send_notifications(self, alert: Alert):
        tasks = []

        if self.notification_config.email_enabled:
            tasks.append(self._send_email_notification(alert))

        if self.notification_config.webhook_enabled:
            tasks.append(self._send_webhook_notification(alert))

        if self.notification_config.slack_enabled:
            tasks.append(self._send_slack_notification(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email_notification(self, alert: Alert):
        try:
            msg = MimeMultipart()
            msg['From'] = self.notification_config.email_username
            msg['To'] = ', '.join(self.notification_config.email_recipients)
            msg['Subject'] = f"[ProcessGuard] {alert.level.value.upper()}: {alert.title}"

            body = f"""
Alert Details:
- Type: {alert.alert_type.value}
- Level: {alert.level.value}
- Time: {alert.timestamp.isoformat()}
- Process: {alert.process_name or 'System'}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata, indent=2)}
            """

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(
                self.notification_config.email_smtp_server,
                self.notification_config.email_smtp_port
            )

            if self.notification_config.email_use_tls:
                server.starttls()

            server.login(
                self.notification_config.email_username,
                self.notification_config.email_password
            )

            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email notification sent for alert: {alert.id}")

        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")

    async def _send_webhook_notification(self, alert: Alert):
        try:
            import aiohttp

            payload = {
                "alert_id": alert.id,
                "type": alert.alert_type.value,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "process_name": alert.process_name,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.notification_config.webhook_url,
                    json=payload,
                    headers=self.notification_config.webhook_headers
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook notification sent for alert: {alert.id}")
                    else:
                        self.logger.error(f"Webhook notification failed: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")

    async def _send_slack_notification(self, alert: Alert):
        try:
            import aiohttp

            color_map = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff9500",
                AlertLevel.CRITICAL: "#ff0000"
            }

            payload = {
                "attachments": [{
                    "color": color_map.get(alert.level, "#36a64f"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {"title": "Type", "value": alert.alert_type.value, "short": True},
                        {"title": "Level", "value": alert.level.value, "short": True},
                        {"title": "Process", "value": alert.process_name or "System", "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                    ]
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.notification_config.slack_webhook_url,
                    json=payload
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Slack notification sent for alert: {alert.id}")
                    else:
                        self.logger.error(f"Slack notification failed: {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send slack notification: {e}")

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                self.logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        for i, alert in enumerate(self.alerts):
            if alert.id == alert_id:
                alert.resolved = True
                self.alerts.pop(i)
                self.logger.info(f"Alert resolved: {alert_id}")
                return True
        return False

    def get_active_alerts(self) -> List[Alert]:
        return [alert for alert in self.alerts if not alert.resolved]

    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff]

    async def check_process_alerts(self, process: ManagedProcess, metrics: ProcessMetrics):
        config = process.config

        if metrics.status.value == "failed" and config.alert_on_failure:
            await self.create_alert(
                AlertType.PROCESS_FAILED,
                AlertLevel.CRITICAL,
                f"Process {config.name} has failed",
                f"Process {config.name} is no longer running and has failed.",
                config.name,
                {"pid": metrics.pid, "uptime": metrics.uptime}
            )

        if config.alert_on_high_cpu and metrics.cpu_percent > config.cpu_threshold:
            await self.create_alert(
                AlertType.HIGH_CPU,
                AlertLevel.WARNING,
                f"High CPU usage for {config.name}",
                f"Process {config.name} is using {metrics.cpu_percent:.1f}% CPU (threshold: {config.cpu_threshold}%)",
                config.name,
                {"cpu_percent": metrics.cpu_percent, "threshold": config.cpu_threshold}
            )

        if config.alert_on_high_memory and metrics.memory_percent > config.memory_threshold:
            await self.create_alert(
                AlertType.HIGH_MEMORY,
                AlertLevel.WARNING,
                f"High memory usage for {config.name}",
                f"Process {config.name} is using {metrics.memory_percent:.1f}% memory (threshold: {config.memory_threshold}%)",
                config.name,
                {"memory_percent": metrics.memory_percent, "memory_mb": metrics.memory_mb, "threshold": config.memory_threshold}
            )

    async def check_system_alerts(self, metrics: SystemMetrics):
        if metrics.cpu_percent > 90:
            await self.create_alert(
                AlertType.SYSTEM_HIGH_CPU,
                AlertLevel.CRITICAL,
                "System CPU usage critical",
                f"System CPU usage is at {metrics.cpu_percent:.1f}%",
                None,
                {"cpu_percent": metrics.cpu_percent}
            )

        if metrics.memory_percent > 90:
            await self.create_alert(
                AlertType.SYSTEM_HIGH_MEMORY,
                AlertLevel.CRITICAL,
                "System memory usage critical",
                f"System memory usage is at {metrics.memory_percent:.1f}%",
                None,
                {"memory_percent": metrics.memory_percent, "memory_available": metrics.memory_available}
            )

        for mount, usage in metrics.disk_usage.items():
            if usage["percent"] > 90:
                await self.create_alert(
                    AlertType.DISK_FULL,
                    AlertLevel.CRITICAL,
                    f"Disk space critical: {mount}",
                    f"Disk usage on {mount} is at {usage['percent']:.1f}%",
                    None,
                    {"mount": mount, "usage_percent": usage["percent"], "free_bytes": usage["free"]}
                )