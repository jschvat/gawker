import os
import psutil
import platform
import socket
from typing import List, Dict, Any
from datetime import datetime

from ..models.system import SystemMetrics, SystemInfo, PortInfo
from ..utils.logging import get_logger

class DockerSystemMonitor:
    """System monitor that works in Docker containers with host system access"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.host_proc = os.environ.get('HOST_PROC', '/proc')
        self.host_sys = os.environ.get('HOST_SYS', '/sys')
        self.host_root = os.environ.get('HOST_ROOT', '/')

        # Check if we're in a container with host access
        self.in_container = os.path.exists('/.dockerenv')
        self.has_host_access = os.path.exists(self.host_proc)

        if self.in_container and self.has_host_access:
            self.logger.info("Running in Docker container with host system access")
        elif self.in_container:
            self.logger.warning("Running in Docker container without host access")
        else:
            self.logger.info("Running on host system")

    def get_system_info(self) -> SystemInfo:
        if self.in_container and self.has_host_access:
            return self._get_host_system_info()
        else:
            return self._get_container_system_info()

    def _get_host_system_info(self) -> SystemInfo:
        """Get system info from host when running in container"""
        try:
            # Read host information
            hostname = socket.gethostname()

            # Try to get host platform info
            try:
                with open(f"{self.host_root}/etc/os-release", 'r') as f:
                    os_info = f.read()
                    platform_name = "Linux"
                    for line in os_info.split('\n'):
                        if line.startswith('PRETTY_NAME='):
                            platform_name = line.split('=')[1].strip('"')
                            break
            except:
                platform_name = platform.system()

            # CPU count from host
            try:
                with open(f"{self.host_proc}/cpuinfo", 'r') as f:
                    cpu_count = len([line for line in f if line.startswith('processor')])
            except:
                cpu_count = psutil.cpu_count()

            # Memory from host
            try:
                with open(f"{self.host_proc}/meminfo", 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if line.startswith('MemTotal:'):
                            total_memory = int(line.split()[1]) * 1024  # Convert KB to bytes
                            break
                    else:
                        total_memory = psutil.virtual_memory().total
            except:
                total_memory = psutil.virtual_memory().total

            # Boot time from host
            try:
                with open(f"{self.host_proc}/stat", 'r') as f:
                    for line in f:
                        if line.startswith('btime'):
                            boot_time = datetime.fromtimestamp(int(line.split()[1]))
                            break
                    else:
                        boot_time = datetime.fromtimestamp(psutil.boot_time())
            except:
                boot_time = datetime.fromtimestamp(psutil.boot_time())

            return SystemInfo(
                hostname=hostname,
                platform=platform_name,
                architecture=platform.machine(),
                cpu_count=cpu_count,
                total_memory=total_memory,
                boot_time=boot_time,
                open_ports=self.get_open_ports()
            )

        except Exception as e:
            self.logger.error(f"Failed to get host system info: {e}")
            return self._get_container_system_info()

    def _get_container_system_info(self) -> SystemInfo:
        """Fallback to container system info"""
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
        if self.in_container and self.has_host_access:
            return self._get_host_system_metrics()
        else:
            return self._get_container_system_metrics()

    def _get_host_system_metrics(self) -> SystemMetrics:
        """Get system metrics from host when running in container"""
        try:
            # CPU usage from host
            cpu_percent = self._get_host_cpu_percent()

            # Memory from host
            memory_stats = self._get_host_memory_stats()

            # Disk usage
            disk_usage = self._get_host_disk_usage()

            # Network I/O
            network_io = self._get_host_network_io()

            # Load average
            load_average = self._get_host_load_average()

            # Uptime
            uptime = self._get_host_uptime()

            # Active connections
            active_connections = len(psutil.net_connections())

            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_stats['percent'],
                memory_total=memory_stats['total'],
                memory_available=memory_stats['available'],
                disk_usage=disk_usage,
                network_io=network_io,
                load_average=load_average,
                uptime=uptime,
                active_connections=active_connections
            )

        except Exception as e:
            self.logger.error(f"Failed to get host system metrics: {e}")
            return self._get_container_system_metrics()

    def _get_container_system_metrics(self) -> SystemMetrics:
        """Fallback to container system metrics"""
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

    def _get_host_cpu_percent(self) -> float:
        """Get CPU percentage from host /proc/stat"""
        try:
            with open(f"{self.host_proc}/stat", 'r') as f:
                cpu_line = f.readline()
                cpu_values = list(map(int, cpu_line.split()[1:]))

                idle = cpu_values[3]
                total = sum(cpu_values)

                # Simple calculation (not as accurate as psutil's interval-based calculation)
                if total > 0:
                    return ((total - idle) / total) * 100
                return 0.0
        except:
            return psutil.cpu_percent()

    def _get_host_memory_stats(self) -> Dict[str, int]:
        """Get memory stats from host /proc/meminfo"""
        try:
            with open(f"{self.host_proc}/meminfo", 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':')
                        value = int(parts[1]) * 1024  # Convert KB to bytes
                        meminfo[key] = value

                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))

                if total > 0:
                    percent = ((total - available) / total) * 100
                else:
                    percent = 0.0

                return {
                    'total': total,
                    'available': available,
                    'percent': percent
                }
        except:
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent
            }

    def _get_host_disk_usage(self) -> Dict[str, Dict[str, Any]]:
        """Get disk usage from host filesystem"""
        disk_usage = {}
        try:
            # Read mounts from host
            with open(f"{self.host_proc}/mounts", 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device, mountpoint = parts[0], parts[1]
                        if mountpoint.startswith('/') and not mountpoint.startswith('/proc'):
                            try:
                                host_path = f"{self.host_root}{mountpoint}" if mountpoint != '/' else self.host_root
                                usage = psutil.disk_usage(host_path)
                                disk_usage[mountpoint] = {
                                    "total": usage.total,
                                    "used": usage.used,
                                    "free": usage.free,
                                    "percent": (usage.used / usage.total) * 100
                                }
                            except (PermissionError, OSError):
                                continue
        except:
            # Fallback to container disk usage
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

        return disk_usage

    def _get_host_network_io(self) -> Dict[str, int]:
        """Get network I/O stats from host"""
        try:
            network_io = psutil.net_io_counters()._asdict()
            return network_io
        except:
            return {"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0}

    def _get_host_load_average(self) -> List[float]:
        """Get load average from host"""
        try:
            with open(f"{self.host_proc}/loadavg", 'r') as f:
                load_avg = f.read().split()[:3]
                return [float(x) for x in load_avg]
        except:
            return psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]

    def _get_host_uptime(self) -> float:
        """Get uptime from host"""
        try:
            with open(f"{self.host_proc}/uptime", 'r') as f:
                uptime = float(f.read().split()[0])
                return uptime
        except:
            return (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()

    def get_open_ports(self) -> List[PortInfo]:
        """Get open ports (works the same in container)"""
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