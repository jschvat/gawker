from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ProcessStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    UNKNOWN = "unknown"

class ProcessType(Enum):
    NODEJS = "nodejs"
    PYTHON = "python"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    GENERIC = "generic"

@dataclass
class ProcessConfig:
    name: str
    command: str
    working_dir: str
    process_type: ProcessType = ProcessType.GENERIC
    env_vars: Dict[str, str] = field(default_factory=dict)
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

@dataclass
class ProcessMetrics:
    timestamp: datetime
    pid: Optional[int]
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    open_files: int
    connections: List[Dict[str, Any]]
    threads: int
    status: ProcessStatus
    uptime: float

@dataclass
class ManagedProcess:
    config: ProcessConfig
    status: ProcessStatus = ProcessStatus.STOPPED
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    metrics_history: List[ProcessMetrics] = field(default_factory=list)

    def get_latest_metrics(self) -> Optional[ProcessMetrics]:
        return self.metrics_history[-1] if self.metrics_history else None