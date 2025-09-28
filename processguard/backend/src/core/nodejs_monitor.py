import json
import re
import requests
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import psutil
from pathlib import Path

from ..models.process import ProcessMetrics, ManagedProcess
from ..utils.logging import get_logger

class NodeJSMonitor:
    """Enhanced monitoring for Node.js applications"""

    def __init__(self):
        self.logger = get_logger(__name__)

    async def get_nodejs_metrics(self, process: ManagedProcess) -> Dict[str, Any]:
        """Get Node.js specific metrics"""
        metrics = {}

        if not process.pid:
            return metrics

        try:
            # Basic process metrics
            ps_process = psutil.Process(process.pid)

            # Node.js specific metrics
            metrics.update({
                'memory_heap_used': self._get_heap_usage(process),
                'event_loop_lag': self._get_event_loop_lag(process),
                'active_handles': self._get_active_handles(process),
                'open_sockets': self._get_open_sockets(process),
                'npm_dependencies': self._check_npm_dependencies(process),
                'package_json_info': self._get_package_info(process),
                'node_version': self._get_node_version(process),
                'environment': self._get_node_environment(process),
                'port_status': await self._check_port_health(process)
            })

        except Exception as e:
            self.logger.error(f"Failed to get Node.js metrics for {process.config.name}: {e}")

        return metrics

    def _get_heap_usage(self, process: ManagedProcess) -> Optional[Dict[str, int]]:
        """Get Node.js heap usage if available"""
        try:
            # Try to read from V8 inspector if enabled
            # This would require the app to expose metrics endpoint
            return self._try_metrics_endpoint(process)
        except:
            return None

    def _try_metrics_endpoint(self, process: ManagedProcess) -> Optional[Dict[str, Any]]:
        """Try to get metrics from common Node.js metrics endpoints"""
        common_ports = [3000, 8000, 9229, 9230]  # Common Node.js ports

        for port in common_ports:
            try:
                # Try common metrics endpoints
                endpoints = ['/metrics', '/health', '/status', '/_health']

                for endpoint in endpoints:
                    try:
                        response = requests.get(f"http://localhost:{port}{endpoint}", timeout=2)
                        if response.status_code == 200:
                            try:
                                return response.json()
                            except:
                                # Parse text metrics (Prometheus format)
                                return self._parse_prometheus_metrics(response.text)
                    except:
                        continue
            except:
                continue

        return None

    def _parse_prometheus_metrics(self, text: str) -> Dict[str, Any]:
        """Parse Prometheus-style metrics"""
        metrics = {}

        for line in text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue

            try:
                parts = line.split(' ')
                if len(parts) >= 2:
                    key = parts[0]
                    value = float(parts[1])
                    metrics[key] = value
            except:
                continue

        return metrics

    def _get_event_loop_lag(self, process: ManagedProcess) -> Optional[float]:
        """Estimate event loop lag from CPU usage patterns"""
        try:
            ps_process = psutil.Process(process.pid)
            # This is an approximation - real event loop lag needs instrumentation
            cpu_percent = ps_process.cpu_percent()

            # High CPU with low throughput might indicate event loop blocking
            if cpu_percent > 80:
                return cpu_percent / 10  # Rough estimation
            return 0.0
        except:
            return None

    def _get_active_handles(self, process: ManagedProcess) -> int:
        """Get number of active handles (file descriptors)"""
        try:
            ps_process = psutil.Process(process.pid)
            return ps_process.num_fds() if hasattr(ps_process, 'num_fds') else len(ps_process.open_files())
        except:
            return 0

    def _get_open_sockets(self, process: ManagedProcess) -> List[Dict[str, Any]]:
        """Get open sockets for the process"""
        try:
            ps_process = psutil.Process(process.pid)
            connections = []

            for conn in ps_process.connections():
                connections.append({
                    'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                    'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                    'status': conn.status,
                    'type': conn.type.name if hasattr(conn.type, 'name') else str(conn.type)
                })

            return connections
        except:
            return []

    def _check_npm_dependencies(self, process: ManagedProcess) -> Dict[str, Any]:
        """Check npm dependencies and vulnerabilities"""
        try:
            working_dir = Path(process.config.working_dir)
            package_json = working_dir / 'package.json'

            if not package_json.exists():
                return {'status': 'no_package_json'}

            # Check for security vulnerabilities (if npm is available)
            try:
                import subprocess
                result = subprocess.run(
                    ['npm', 'audit', '--json'],
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    audit_data = json.loads(result.stdout)
                    return {
                        'status': 'checked',
                        'vulnerabilities': audit_data.get('metadata', {}).get('vulnerabilities', {}),
                        'total_dependencies': audit_data.get('metadata', {}).get('totalDependencies', 0)
                    }
            except:
                pass

            return {'status': 'audit_unavailable'}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_package_info(self, process: ManagedProcess) -> Dict[str, Any]:
        """Get package.json information"""
        try:
            working_dir = Path(process.config.working_dir)
            package_json = working_dir / 'package.json'

            if package_json.exists():
                with open(package_json, 'r') as f:
                    data = json.load(f)

                return {
                    'name': data.get('name', 'unknown'),
                    'version': data.get('version', 'unknown'),
                    'scripts': data.get('scripts', {}),
                    'main': data.get('main', 'index.js'),
                    'engines': data.get('engines', {}),
                    'dependencies_count': len(data.get('dependencies', {})),
                    'dev_dependencies_count': len(data.get('devDependencies', {}))
                }
        except:
            pass

        return {'status': 'unavailable'}

    def _get_node_version(self, process: ManagedProcess) -> Optional[str]:
        """Get Node.js version"""
        try:
            ps_process = psutil.Process(process.pid)
            cmdline = ps_process.cmdline()

            # Extract Node.js executable path
            if cmdline and 'node' in cmdline[0]:
                import subprocess
                result = subprocess.run([cmdline[0], '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout.strip()
        except:
            pass

        return None

    def _get_node_environment(self, process: ManagedProcess) -> Dict[str, str]:
        """Get Node.js environment variables"""
        try:
            ps_process = psutil.Process(process.pid)
            environ = ps_process.environ()

            node_env_vars = {}
            for key, value in environ.items():
                if key.startswith('NODE_') or key in ['NODE_ENV', 'PORT', 'HOST']:
                    node_env_vars[key] = value

            return node_env_vars
        except:
            return {}

    async def _check_port_health(self, process: ManagedProcess) -> Dict[str, Any]:
        """Check if the Node.js server is responding on its port"""
        try:
            # Get ports the process is listening on
            ps_process = psutil.Process(process.pid)
            listening_ports = []

            for conn in ps_process.connections():
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    listening_ports.append(conn.laddr.port)

            port_status = {}
            for port in listening_ports:
                try:
                    response = requests.get(f"http://localhost:{port}", timeout=3)
                    port_status[port] = {
                        'status': 'responding',
                        'http_status': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                except requests.exceptions.ConnectionError:
                    port_status[port] = {'status': 'connection_refused'}
                except requests.exceptions.Timeout:
                    port_status[port] = {'status': 'timeout'}
                except Exception as e:
                    port_status[port] = {'status': 'error', 'error': str(e)}

            return port_status

        except Exception as e:
            return {'error': str(e)}

    def detect_nodejs_crashes(self, process: ManagedProcess, log_lines: List[str]) -> List[Dict[str, Any]]:
        """Detect Node.js specific crash patterns"""
        crashes = []

        crash_patterns = [
            (r'Error: Cannot find module', 'missing_module'),
            (r'ReferenceError:', 'reference_error'),
            (r'TypeError:', 'type_error'),
            (r'SyntaxError:', 'syntax_error'),
            (r'EADDRINUSE.*address already in use', 'port_in_use'),
            (r'ECONNREFUSED', 'connection_refused'),
            (r'UnhandledPromiseRejectionWarning', 'unhandled_promise'),
            (r'MaxListenersExceededWarning', 'memory_leak_warning'),
            (r'FATAL ERROR:.*JavaScript heap out of memory', 'heap_overflow'),
            (r'segmentation fault', 'segfault'),
            (r'Error: spawn.*ENOENT', 'spawn_error')
        ]

        for line in log_lines[-100:]:  # Check last 100 lines
            for pattern, error_type in crash_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    crashes.append({
                        'type': error_type,
                        'pattern': pattern,
                        'line': line,
                        'timestamp': datetime.now().isoformat()
                    })

        return crashes

    def get_restart_strategy(self, process: ManagedProcess, crash_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get intelligent restart strategy based on crash type"""
        if not crash_info:
            return {'action': 'normal_restart', 'delay': 5}

        latest_crash = crash_info[-1]
        crash_type = latest_crash.get('type')

        strategies = {
            'port_in_use': {
                'action': 'delayed_restart',
                'delay': 10,
                'reason': 'Port conflict - waiting for port to be available'
            },
            'missing_module': {
                'action': 'no_restart',
                'reason': 'Missing dependencies - manual intervention required'
            },
            'heap_overflow': {
                'action': 'restart_with_memory_limit',
                'delay': 15,
                'memory_limit': '2GB',
                'reason': 'Memory issue - restarting with limits'
            },
            'syntax_error': {
                'action': 'no_restart',
                'reason': 'Code error - manual fix required'
            }
        }

        return strategies.get(crash_type, {'action': 'normal_restart', 'delay': 5})