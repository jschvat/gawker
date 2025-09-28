import psutil
import platform
import socket
from typing import List, Dict, Any
from datetime import datetime

from ..models.system import SystemMetrics, SystemInfo, PortInfo
from ..utils.logging import get_logger

class SystemMonitor:
    def __init__(self):
        self.logger = get_logger(__name__)

    def get_system_info(self) -> SystemInfo:
        boot_time = datetime.fromtimestamp(psutil.boot_time())

        return SystemInfo(
            hostname=socket.gethostname(),
            platform=platform.system(),
            architecture=platform.machine(),
            cpu_count=psutil.cpu_count(),
            total_memory=psutil.virtual_memory().total,
            boot_time=boot_time,
            open_ports=self.get_open_ports()
        )

    def get_system_metrics(self) -> SystemMetrics:
        memory = psutil.virtual_memory()

        disk_usage = {}
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": (usage.used / usage.total) * 100
                }
            except (PermissionError, OSError):
                continue

        network_io = psutil.net_io_counters()._asdict()

        active_connections = len(psutil.net_connections())

        uptime = (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=memory.percent,
            memory_total=memory.total,
            memory_available=memory.available,
            disk_usage=disk_usage,
            network_io=network_io,
            load_average=psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0],
            uptime=uptime,
            active_connections=active_connections
        )

    def get_open_ports(self) -> List[PortInfo]:
        ports = []
        connections = psutil.net_connections(kind='inet')

        for conn in connections:
            if conn.status == psutil.CONN_LISTEN and conn.laddr:
                try:
                    process = psutil.Process(conn.pid) if conn.pid else None
                    process_name = process.name() if process else "unknown"
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    process_name = "unknown"

                ports.append(PortInfo(
                    port=conn.laddr.port,
                    protocol="TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    process_name=process_name,
                    pid=conn.pid or 0,
                    status=conn.status
                ))

        return sorted(ports, key=lambda x: x.port)

    def get_process_tree(self) -> Dict[str, Any]:
        process_tree = {}

        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                process_tree[info['pid']] = {
                    'name': info['name'],
                    'ppid': info['ppid'],
                    'cpu_percent': info['cpu_percent'] or 0.0,
                    'memory_percent': info['memory_percent'] or 0.0
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return process_tree

    def get_network_connections(self) -> List[Dict[str, Any]]:
        connections = []

        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr:
                    process_name = "unknown"
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            process_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    connections.append({
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                        'status': conn.status,
                        'pid': conn.pid or 0,
                        'process_name': process_name,
                        'protocol': "TCP" if conn.type == socket.SOCK_STREAM else "UDP"
                    })
        except psutil.AccessDenied:
            self.logger.warning("Access denied when getting network connections")

        return connections

    def check_port_availability(self, port: int, protocol: str = "TCP") -> bool:
        sock_type = socket.SOCK_STREAM if protocol.upper() == "TCP" else socket.SOCK_DGRAM

        try:
            with socket.socket(socket.AF_INET, sock_type) as sock:
                sock.bind(('localhost', port))
                return True
        except OSError:
            return False

    def get_detailed_cpu_info(self) -> Dict[str, Any]:
        return {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'per_cpu_percent': psutil.cpu_percent(percpu=True),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
            'stats': psutil.cpu_stats()._asdict()
        }