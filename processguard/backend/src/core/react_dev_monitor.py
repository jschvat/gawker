import json
import re
import requests
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import psutil
from pathlib import Path
import websocket
import threading

from ..models.process import ProcessMetrics, ManagedProcess
from ..utils.logging import get_logger

class ReactDevMonitor:
    """Enhanced monitoring for React development servers"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.webpack_stats = {}

    async def get_react_dev_metrics(self, process: ManagedProcess) -> Dict[str, Any]:
        """Get React development server specific metrics"""
        metrics = {}

        if not process.pid:
            return metrics

        try:
            metrics.update({
                'webpack_status': await self._get_webpack_status(process),
                'build_stats': self._get_build_stats(process),
                'hot_reload_status': await self._check_hot_reload(process),
                'dev_server_health': await self._check_dev_server_health(process),
                'bundle_size': self._get_bundle_size(process),
                'compile_time': self._get_compile_time(process),
                'errors_warnings': self._parse_build_output(process),
                'react_version': self._get_react_version(process),
                'dependencies_status': self._check_dependencies(process)
            })

        except Exception as e:
            self.logger.error(f"Failed to get React dev metrics for {process.config.name}: {e}")

        return metrics

    async def _get_webpack_status(self, process: ManagedProcess) -> Dict[str, Any]:
        """Get webpack compilation status"""
        try:
            # Common webpack dev server ports
            ports = [3000, 3001, 8080, 8081, 9000]

            for port in ports:
                try:
                    # Check webpack-dev-server status endpoint
                    response = requests.get(f"http://localhost:{port}/webpack-dev-server", timeout=2)
                    if response.status_code == 200:
                        return {
                            'status': 'running',
                            'port': port,
                            'webpack_version': self._extract_webpack_version(response.text)
                        }
                except:
                    continue

            # Try sockjs endpoint for webpack status
            for port in ports:
                try:
                    response = requests.get(f"http://localhost:{port}/sockjs-node/info", timeout=2)
                    if response.status_code == 200:
                        return {
                            'status': 'running',
                            'port': port,
                            'websocket_enabled': True
                        }
                except:
                    continue

            return {'status': 'not_accessible'}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_build_stats(self, process: ManagedProcess) -> Dict[str, Any]:
        """Parse build statistics from logs"""
        try:
            log_manager = process.config.log_file
            if not log_manager:
                return {'status': 'no_logs'}

            # Read recent log lines
            try:
                with open(log_manager, 'r') as f:
                    lines = f.readlines()[-200:]  # Last 200 lines
            except:
                return {'status': 'log_read_error'}

            stats = {
                'compiled_successfully': False,
                'compilation_time': None,
                'warnings_count': 0,
                'errors_count': 0,
                'asset_count': 0,
                'total_size': None
            }

            for line in lines:
                # Webpack compilation success
                if 'compiled successfully' in line.lower():
                    stats['compiled_successfully'] = True

                # Extract compilation time
                time_match = re.search(r'compiled.*in (\d+(?:\.\d+)?)\s*([ms]+)', line, re.IGNORECASE)
                if time_match:
                    time_val = float(time_match.group(1))
                    unit = time_match.group(2)
                    if unit == 's':
                        time_val *= 1000  # Convert to ms
                    stats['compilation_time'] = time_val

                # Count warnings and errors
                if re.search(r'(\d+)\s+warning', line, re.IGNORECASE):
                    stats['warnings_count'] = int(re.search(r'(\d+)\s+warning', line, re.IGNORECASE).group(1))

                if re.search(r'(\d+)\s+error', line, re.IGNORECASE):
                    stats['errors_count'] = int(re.search(r'(\d+)\s+error', line, re.IGNORECASE).group(1))

                # Extract asset information
                if 'asset' in line.lower() and 'kb' in line.lower():
                    stats['asset_count'] += 1

                # Extract total bundle size
                size_match = re.search(r'(\d+(?:\.\d+)?)\s*(kb|mb)', line, re.IGNORECASE)
                if size_match and 'main' in line:
                    size_val = float(size_match.group(1))
                    unit = size_match.group(2).lower()
                    if unit == 'mb':
                        size_val *= 1024
                    stats['total_size'] = size_val

            return stats

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def _check_hot_reload(self, process: ManagedProcess) -> Dict[str, Any]:
        """Check if hot module replacement is working"""
        try:
            # Look for HMR indicators in process connections
            ps_process = psutil.Process(process.pid)

            # Check for websocket connections (used by HMR)
            websocket_connections = 0
            for conn in ps_process.connections():
                if conn.laddr and conn.laddr.port in [3000, 3001, 8080, 8081]:
                    websocket_connections += 1

            return {
                'websocket_connections': websocket_connections,
                'hmr_enabled': websocket_connections > 0,
                'status': 'active' if websocket_connections > 0 else 'inactive'
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def _check_dev_server_health(self, process: ManagedProcess) -> Dict[str, Any]:
        """Check development server health and responsiveness"""
        try:
            ps_process = psutil.Process(process.pid)
            health_data = {
                'responding': False,
                'response_time': None,
                'port': None,
                'serving_files': False
            }

            # Find the port the dev server is listening on
            for conn in ps_process.connections():
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    port = conn.laddr.port
                    try:
                        # Test main page
                        response = requests.get(f"http://localhost:{port}", timeout=5)
                        health_data.update({
                            'responding': True,
                            'response_time': response.elapsed.total_seconds(),
                            'port': port,
                            'http_status': response.status_code,
                            'serving_files': response.status_code == 200
                        })

                        # Check if it's serving React app
                        if 'react' in response.text.lower() or 'div id="root"' in response.text:
                            health_data['react_app_detected'] = True

                        break

                    except Exception as e:
                        health_data.update({
                            'port': port,
                            'error': str(e)
                        })

            return health_data

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_bundle_size(self, process: ManagedProcess) -> Dict[str, Any]:
        """Get current bundle size information"""
        try:
            working_dir = Path(process.config.working_dir)

            # Check build directory for bundle files
            build_paths = [
                working_dir / 'build' / 'static' / 'js',
                working_dir / 'dist',
                working_dir / 'public' / 'static' / 'js'
            ]

            bundle_info = {
                'total_size': 0,
                'js_files': [],
                'css_files': [],
                'asset_files': []
            }

            for build_path in build_paths:
                if build_path.exists():
                    for file_path in build_path.rglob('*'):
                        if file_path.is_file():
                            size = file_path.stat().st_size
                            bundle_info['total_size'] += size

                            if file_path.suffix == '.js':
                                bundle_info['js_files'].append({
                                    'name': file_path.name,
                                    'size': size,
                                    'size_kb': round(size / 1024, 2)
                                })
                            elif file_path.suffix == '.css':
                                bundle_info['css_files'].append({
                                    'name': file_path.name,
                                    'size': size,
                                    'size_kb': round(size / 1024, 2)
                                })

            bundle_info['total_size_kb'] = round(bundle_info['total_size'] / 1024, 2)
            bundle_info['total_size_mb'] = round(bundle_info['total_size'] / (1024 * 1024), 2)

            return bundle_info

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_compile_time(self, process: ManagedProcess) -> Optional[float]:
        """Get last compilation time"""
        try:
            # This would typically be extracted from webpack logs
            # Implementation depends on log format
            return self.webpack_stats.get('last_compile_time')
        except:
            return None

    def _parse_build_output(self, process: ManagedProcess) -> Dict[str, Any]:
        """Parse build output for errors and warnings"""
        try:
            log_file = process.config.log_file
            if not log_file:
                return {'status': 'no_logs'}

            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-100:]  # Last 100 lines
            except:
                return {'status': 'log_read_error'}

            errors = []
            warnings = []

            current_error = None
            current_warning = None

            for line in lines:
                line = line.strip()

                # Detect error start
                if re.match(r'ERROR in ', line) or 'Module not found:' in line:
                    if current_error:
                        errors.append(current_error)
                    current_error = {'type': 'error', 'message': line, 'details': []}

                # Detect warning start
                elif re.match(r'WARNING in ', line) or 'warning' in line.lower():
                    if current_warning:
                        warnings.append(current_warning)
                    current_warning = {'type': 'warning', 'message': line, 'details': []}

                # Add details to current error/warning
                elif current_error and line and not line.startswith('ERROR'):
                    current_error['details'].append(line)
                elif current_warning and line and not line.startswith('WARNING'):
                    current_warning['details'].append(line)

            # Add final error/warning
            if current_error:
                errors.append(current_error)
            if current_warning:
                warnings.append(current_warning)

            return {
                'errors': errors,
                'warnings': warnings,
                'error_count': len(errors),
                'warning_count': len(warnings)
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_react_version(self, process: ManagedProcess) -> Optional[str]:
        """Get React version from package.json"""
        try:
            working_dir = Path(process.config.working_dir)
            package_json = working_dir / 'package.json'

            if package_json.exists():
                with open(package_json, 'r') as f:
                    data = json.load(f)

                dependencies = data.get('dependencies', {})
                dev_dependencies = data.get('devDependencies', {})

                react_version = dependencies.get('react') or dev_dependencies.get('react')
                return react_version

        except:
            pass

        return None

    def _check_dependencies(self, process: ManagedProcess) -> Dict[str, Any]:
        """Check for missing or outdated dependencies"""
        try:
            working_dir = Path(process.config.working_dir)
            package_json = working_dir / 'package.json'
            node_modules = working_dir / 'node_modules'

            if not package_json.exists():
                return {'status': 'no_package_json'}

            if not node_modules.exists():
                return {'status': 'node_modules_missing', 'action': 'run npm install'}

            # Check for common React dependencies
            with open(package_json, 'r') as f:
                data = json.load(f)

            dependencies = data.get('dependencies', {})
            dev_dependencies = data.get('devDependencies', {})
            all_deps = {**dependencies, **dev_dependencies}

            missing_deps = []
            for dep_name in all_deps.keys():
                dep_path = node_modules / dep_name
                if not dep_path.exists():
                    missing_deps.append(dep_name)

            return {
                'status': 'checked',
                'total_dependencies': len(all_deps),
                'missing_dependencies': missing_deps,
                'missing_count': len(missing_deps),
                'node_modules_size': self._get_directory_size(node_modules) if node_modules.exists() else 0
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory"""
        try:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except:
            return 0

    def _extract_webpack_version(self, text: str) -> Optional[str]:
        """Extract webpack version from dev server output"""
        version_match = re.search(r'webpack[^\d]*(\d+\.\d+\.\d+)', text, re.IGNORECASE)
        return version_match.group(1) if version_match else None

    def detect_react_dev_issues(self, process: ManagedProcess, log_lines: List[str]) -> List[Dict[str, Any]]:
        """Detect React development specific issues"""
        issues = []

        issue_patterns = [
            (r'Module not found:.*Can\'t resolve', 'module_not_found'),
            (r'Failed to compile', 'compilation_failed'),
            (r'Syntax error:', 'syntax_error'),
            (r'Cannot read property.*of undefined', 'undefined_property'),
            (r'React Hook.*has missing dependencies', 'hook_dependencies'),
            (r'EADDRINUSE.*address already in use', 'port_in_use'),
            (r'npm ERR!', 'npm_error'),
            (r'Warning:.*deprecated', 'deprecated_dependency'),
            (r'Critical dependency:', 'critical_dependency'),
            (r'export.*was not found', 'export_not_found'),
            (r'Unexpected token', 'unexpected_token')
        ]

        for line in log_lines[-50:]:  # Check last 50 lines
            for pattern, issue_type in issue_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'type': issue_type,
                        'message': line.strip(),
                        'timestamp': datetime.now().isoformat(),
                        'severity': self._get_issue_severity(issue_type)
                    })

        return issues

    def _get_issue_severity(self, issue_type: str) -> str:
        """Get severity level for different issue types"""
        critical_issues = ['compilation_failed', 'port_in_use', 'module_not_found']
        warning_issues = ['deprecated_dependency', 'hook_dependencies']

        if issue_type in critical_issues:
            return 'critical'
        elif issue_type in warning_issues:
            return 'warning'
        else:
            return 'error'

    def get_development_recommendations(self, process: ManagedProcess, metrics: Dict[str, Any]) -> List[str]:
        """Get development recommendations based on metrics"""
        recommendations = []

        # Bundle size recommendations
        bundle_info = metrics.get('bundle_size', {})
        if bundle_info.get('total_size_mb', 0) > 5:
            recommendations.append("Consider code splitting - bundle size is over 5MB")

        # Compilation time recommendations
        compile_time = metrics.get('compile_time')
        if compile_time and compile_time > 10000:  # 10 seconds
            recommendations.append("Compilation is slow - consider optimizing webpack config")

        # Dependency recommendations
        deps_status = metrics.get('dependencies_status', {})
        if deps_status.get('missing_count', 0) > 0:
            recommendations.append("Missing dependencies detected - run 'npm install'")

        # Error recommendations
        errors_warnings = metrics.get('errors_warnings', {})
        if errors_warnings.get('error_count', 0) > 0:
            recommendations.append("Fix compilation errors for hot reload to work properly")

        return recommendations