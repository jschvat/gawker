from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class SystemMetrics:
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

@dataclass
class PortInfo:
    port: int
    protocol: str
    process_name: str
    pid: int
    status: str

@dataclass
class SystemInfo:
    hostname: str
    platform: str
    architecture: str
    cpu_count: int
    total_memory: int
    boot_time: datetime
    open_ports: List[PortInfo] = field(default_factory=list)