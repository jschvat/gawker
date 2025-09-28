from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ProcessStatusEnum(str, Enum):
    stopped = "stopped"
    starting = "starting"
    running = "running"
    stopping = "stopping"
    failed = "failed"
    unknown = "unknown"

class ProcessTypeEnum(str, Enum):
    nodejs = "nodejs"
    python = "python"
    java = "java"
    go = "go"
    rust = "rust"
    generic = "generic"

class AlertLevelEnum(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"

class ProcessConfigCreate(BaseModel):
    name: str = Field(..., description="Process name")
    command: str = Field(..., description="Command to execute")
    working_dir: str = Field(..., description="Working directory")
    process_type: ProcessTypeEnum = ProcessTypeEnum.generic
    env_vars: Dict[str, str] = Field(default_factory=dict)
    auto_restart: bool = True
    max_restarts: int = 5
    restart_delay: int = 5
    log_file: Optional[str] = None
    redirect_output: bool = True
    cpu_limit: Optional[float] = None
    memory_limit: Optional[int] = None
    alert_on_failure: bool = True
    alert_on_high_cpu: bool = True
    alert_on_high_memory: bool = True
    cpu_threshold: float = 80.0
    memory_threshold: float = 80.0

class ProcessConfigUpdate(BaseModel):
    command: Optional[str] = None
    working_dir: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    auto_restart: Optional[bool] = None
    max_restarts: Optional[int] = None
    restart_delay: Optional[int] = None
    redirect_output: Optional[bool] = None
    cpu_limit: Optional[float] = None
    memory_limit: Optional[int] = None
    alert_on_failure: Optional[bool] = None
    alert_on_high_cpu: Optional[bool] = None
    alert_on_high_memory: Optional[bool] = None
    cpu_threshold: Optional[float] = None
    memory_threshold: Optional[float] = None

class ProcessMetricsResponse(BaseModel):
    timestamp: datetime
    pid: Optional[int]
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    open_files: int
    connections: List[Dict[str, Any]]
    threads: int
    status: ProcessStatusEnum
    uptime: float

class ProcessStatusResponse(BaseModel):
    name: str
    status: ProcessStatusEnum
    pid: Optional[int]
    started_at: Optional[datetime]
    restart_count: int
    config: ProcessConfigCreate
    latest_metrics: Optional[ProcessMetricsResponse]

class SystemInfoResponse(BaseModel):
    hostname: str
    platform: str
    architecture: str
    cpu_count: int
    total_memory: int
    boot_time: datetime
    open_ports: List[Dict[str, Any]]

class SystemMetricsResponse(BaseModel):
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_total: int
    memory_available: int
    disk_usage: Dict[str, Dict[str, Any]]
    network_io: Dict[str, int]
    load_average: List[float]
    uptime: float
    active_connections: int

class AlertResponse(BaseModel):
    id: str
    type: str
    level: AlertLevelEnum
    title: str
    message: str
    process_name: Optional[str]
    timestamp: datetime
    acknowledged: bool
    resolved: bool
    metadata: Dict[str, Any]

class LogFileResponse(BaseModel):
    name: str
    path: str
    size: int
    modified: datetime
    is_current: bool

class NotificationConfigUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: Optional[int] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: Optional[List[str]] = None
    email_use_tls: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_headers: Optional[Dict[str, str]] = None
    slack_enabled: Optional[bool] = None
    slack_webhook_url: Optional[str] = None

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# App Wizard Models
class WizardProjectAnalysisRequest(BaseModel):
    project_path: str = Field(..., description="Path to the project directory")

class WizardProjectAnalysisResponse(BaseModel):
    app_type: str
    detected_frameworks: List[str]
    package_managers: List[str]
    suggested_commands: Dict[str, str]
    environment_variables: Dict[str, str]
    monitoring_patterns: Dict[str, Any]
    ports: List[int]
    dependencies: List[str]

class WizardScriptGenerationRequest(BaseModel):
    project_path: str
    app_type: str
    process_name: str
    environment: str = "development"  # development, staging, production
    custom_command: Optional[str] = None
    custom_env_vars: Optional[Dict[str, str]] = None
    custom_ports: Optional[List[int]] = None

class WizardScriptGenerationResponse(BaseModel):
    launch_script: str
    kill_script: str
    process_config: Dict[str, Any]
    monitoring_config: Dict[str, Any]