import subprocess
import psutil
import time
import os
import signal
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .process_manager import ProcessManager
from .nodejs_monitor import NodeJSMonitor
from .react_dev_monitor import ReactDevMonitor
from .crash_manager import CrashManager, CrashPolicy, CrashAction
from ..models.process import ManagedProcess, ProcessConfig, ProcessStatus, ProcessMetrics, ProcessType
from ..utils.logging import get_logger

class EnhancedProcessManager(ProcessManager):
    """Enhanced process manager with Node.js and React specific features"""

    def __init__(self):
        super().__init__()
        self.nodejs_monitor = NodeJSMonitor()
        self.react_monitor = ReactDevMonitor()
        self.crash_manager = CrashManager()
        self.crash_history: Dict[str, List[Dict]] = {}
        self.logger = get_logger(__name__)

    async def get_enhanced_process_metrics(self, name: str) -> Optional[Dict]:
        """Get enhanced metrics including Node.js/React specific data"""
        if name not in self.processes:
            return None

        process = self.processes[name]
        base_metrics = self.get_process_metrics(name)

        if not base_metrics:
            return None

        enhanced_metrics = {
            'base_metrics': base_metrics.__dict__,
            'crash_history': self.crash_history.get(name, []),
            'restart_recommendations': []
        }

        # Add Node.js specific metrics
        if process.config.process_type == ProcessType.NODEJS:
            enhanced_metrics['nodejs_metrics'] = await self.nodejs_monitor.get_nodejs_metrics(process)

            # Check for Node.js crashes
            log_lines = self._get_recent_logs(name)
            nodejs_crashes = self.nodejs_monitor.detect_nodejs_crashes(process, log_lines)
            if nodejs_crashes:
                self._record_crashes(name, nodejs_crashes)
                enhanced_metrics['nodejs_crashes'] = nodejs_crashes

                # Get restart strategy
                restart_strategy = self.nodejs_monitor.get_restart_strategy(process, nodejs_crashes)
                enhanced_metrics['restart_strategy'] = restart_strategy

        # Add React dev server specific metrics
        if self._is_react_dev_server(process):
            enhanced_metrics['react_dev_metrics'] = await self.react_monitor.get_react_dev_metrics(process)

            # Check for React dev issues
            log_lines = self._get_recent_logs(name)
            react_issues = self.react_monitor.detect_react_dev_issues(process, log_lines)
            if react_issues:
                enhanced_metrics['react_issues'] = react_issues

            # Get development recommendations
            recommendations = self.react_monitor.get_development_recommendations(
                process, enhanced_metrics.get('react_dev_metrics', {})
            )
            enhanced_metrics['recommendations'] = recommendations

        return enhanced_metrics

    def _is_react_dev_server(self, process: ManagedProcess) -> bool:
        """Check if process is a React development server"""
        command = process.config.command.lower()
        react_indicators = [
            'react-scripts start',
            'npm start',
            'yarn start',
            'webpack-dev-server',
            'next dev',
            'vite'
        ]

        return any(indicator in command for indicator in react_indicators)

    def _get_recent_logs(self, process_name: str, lines: int = 100) -> List[str]:
        """Get recent log lines for a process"""
        try:
            if process_name not in self.processes:
                return []

            process = self.processes[process_name]
            log_file = process.config.log_file

            if not log_file or not os.path.exists(log_file):
                return []

            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]

        except Exception as e:
            self.logger.error(f"Failed to read logs for {process_name}: {e}")
            return []

    def _record_crashes(self, process_name: str, crashes: List[Dict]):
        """Record crash information for analysis"""
        if process_name not in self.crash_history:
            self.crash_history[process_name] = []

        for crash in crashes:
            crash['recorded_at'] = datetime.now().isoformat()
            self.crash_history[process_name].append(crash)

        # Keep only recent crashes (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.crash_history[process_name] = [
            crash for crash in self.crash_history[process_name]
            if datetime.fromisoformat(crash['recorded_at']) > cutoff_time
        ]

    async def intelligent_restart(self, name: str) -> bool:
        """Restart process with intelligent strategy based on crash analysis"""
        if name not in self.processes:
            return False

        # Check crash manager policies first
        can_restart, reason = self.crash_manager.can_restart_process(name)
        if not can_restart:
            self.logger.warning(f"Cannot restart {name}: {reason}")
            return False

        process = self.processes[name]

        # Record the restart attempt
        await self.crash_manager.record_crash(name, "restart_requested")

        # Get crash history and determine strategy
        crashes = self.crash_history.get(name, [])
        recent_crashes = [
            crash for crash in crashes
            if datetime.fromisoformat(crash['recorded_at']) > datetime.now() - timedelta(minutes=10)
        ]

        # If too many recent crashes, use longer delay
        if len(recent_crashes) > 3:
            self.logger.warning(f"Too many recent crashes for {name}, using extended delay")
            await asyncio.sleep(30)

        # For Node.js processes, use intelligent restart strategy
        if process.config.process_type == ProcessType.NODEJS and recent_crashes:
            restart_strategy = self.nodejs_monitor.get_restart_strategy(process, recent_crashes)

            if restart_strategy['action'] == 'no_restart':
                self.logger.warning(f"Not restarting {name}: {restart_strategy['reason']}")
                return False

            elif restart_strategy['action'] == 'delayed_restart':
                delay = restart_strategy.get('delay', 10)
                self.logger.info(f"Delayed restart for {name}: waiting {delay}s - {restart_strategy['reason']}")
                await asyncio.sleep(delay)

            elif restart_strategy['action'] == 'restart_with_memory_limit':
                # TODO: Implement memory limit restart
                self.logger.info(f"Restarting {name} with memory considerations")
                await asyncio.sleep(restart_strategy.get('delay', 15))

        return self.restart_process(name)

    def start_nodejs_app(self, name: str, config: Dict) -> bool:
        """Start a Node.js application with enhanced configuration"""
        # Create enhanced config for Node.js apps
        enhanced_config = ProcessConfig(
            name=name,
            command=config['command'],
            working_dir=config['working_dir'],
            process_type=ProcessType.NODEJS,
            env_vars=config.get('env_vars', {}),
            auto_restart=config.get('auto_restart', True),
            max_restarts=config.get('max_restarts', 5),
            restart_delay=config.get('restart_delay', 5),
            redirect_output=config.get('redirect_output', True),
            cpu_threshold=config.get('cpu_threshold', 80.0),
            memory_threshold=config.get('memory_threshold', 80.0)
        )

        # Add Node.js specific environment variables
        enhanced_config.env_vars.update({
            'NODE_ENV': config.get('node_env', 'development'),
            'DEBUG': config.get('debug', ''),
            'PORT': str(config.get('port', 3000))
        })

        # Add log file if not specified
        if not enhanced_config.log_file:
            enhanced_config.log_file = f"/app/logs/{name}_nodejs.log"

        success = self.add_process(enhanced_config)
        if success:
            # Set up crash policy for Node.js apps
            crash_policy = CrashPolicy(
                max_crashes=config.get('max_crashes_threshold', 5),
                time_window_minutes=config.get('crash_time_window', 10),
                action_on_threshold=CrashAction.DISABLE,
                kill_dependencies=config.get('kill_dependencies_on_failure', False)
            )
            self.crash_manager.set_crash_policy(name, crash_policy)

        return success and self.start_process(name)

    def start_react_dev_server(self, name: str, config: Dict) -> bool:
        """Start a React development server with enhanced monitoring"""
        # Detect React app type and adjust command
        working_dir = Path(config['working_dir'])
        package_json = working_dir / 'package.json'

        command = config.get('command', 'npm start')

        # Auto-detect React app type
        if package_json.exists():
            try:
                import json
                with open(package_json, 'r') as f:
                    package_data = json.load(f)

                dependencies = package_data.get('dependencies', {})
                dev_dependencies = package_data.get('devDependencies', {})

                # Detect framework
                if 'next' in dependencies or 'next' in dev_dependencies:
                    if not config.get('command'):
                        command = 'npm run dev'  # Next.js default
                elif 'vite' in dependencies or 'vite' in dev_dependencies:
                    if not config.get('command'):
                        command = 'npm run dev'  # Vite default
                elif 'react-scripts' in dependencies or 'react-scripts' in dev_dependencies:
                    if not config.get('command'):
                        command = 'npm start'  # Create React App default

            except Exception as e:
                self.logger.error(f"Failed to parse package.json for {name}: {e}")

        enhanced_config = ProcessConfig(
            name=name,
            command=command,
            working_dir=config['working_dir'],
            process_type=ProcessType.NODEJS,  # React dev server is Node.js based
            env_vars=config.get('env_vars', {}),
            auto_restart=config.get('auto_restart', True),
            max_restarts=config.get('max_restarts', 10),  # Higher for dev servers
            restart_delay=config.get('restart_delay', 3),  # Faster restart for dev
            redirect_output=True,  # Always capture dev server output
            cpu_threshold=config.get('cpu_threshold', 70.0),  # Lower threshold for dev
            memory_threshold=config.get('memory_threshold', 70.0)
        )

        # Add React dev server specific environment variables
        enhanced_config.env_vars.update({
            'NODE_ENV': 'development',
            'BROWSER': 'none',  # Don't auto-open browser
            'PORT': str(config.get('port', 3000)),
            'FAST_REFRESH': 'true'
        })

        # Add log file
        if not enhanced_config.log_file:
            enhanced_config.log_file = f"/app/logs/{name}_react_dev.log"

        success = self.add_process(enhanced_config)
        if success:
            # Set up crash policy for React dev servers (more lenient)
            crash_policy = CrashPolicy(
                max_crashes=config.get('max_crashes_threshold', 8),  # Higher threshold for dev
                time_window_minutes=config.get('crash_time_window', 5),  # Shorter window
                action_on_threshold=CrashAction.QUARANTINE,  # Quarantine instead of disable
                quarantine_duration_minutes=10
            )
            self.crash_manager.set_crash_policy(name, crash_policy)

        return success and self.start_process(name)

    async def check_development_health(self) -> Dict[str, Any]:
        """Check health of all development processes"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'total_processes': len(self.processes),
            'running_processes': 0,
            'failed_processes': 0,
            'processes_with_issues': [],
            'overall_status': 'healthy'
        }

        for name, process in self.processes.items():
            if process.status == ProcessStatus.RUNNING:
                health_report['running_processes'] += 1

                # Check for specific issues
                issues = []

                # Get enhanced metrics
                metrics = await self.get_enhanced_process_metrics(name)

                if metrics:
                    # Check for React dev issues
                    if 'react_issues' in metrics:
                        issues.extend(metrics['react_issues'])

                    # Check for Node.js crashes
                    if 'nodejs_crashes' in metrics:
                        issues.extend(metrics['nodejs_crashes'])

                    # Check for high restart count
                    if process.restart_count > 5:
                        issues.append({
                            'type': 'high_restart_count',
                            'message': f"Process has restarted {process.restart_count} times",
                            'severity': 'warning'
                        })

                if issues:
                    health_report['processes_with_issues'].append({
                        'name': name,
                        'issues': issues,
                        'issue_count': len(issues)
                    })

            elif process.status == ProcessStatus.FAILED:
                health_report['failed_processes'] += 1

        # Determine overall status
        if health_report['failed_processes'] > 0:
            health_report['overall_status'] = 'critical'
        elif health_report['processes_with_issues']:
            health_report['overall_status'] = 'warning'

        return health_report

    def get_development_summary(self) -> Dict[str, Any]:
        """Get summary of development environment"""
        summary = {
            'total_processes': len(self.processes),
            'by_type': {
                'nodejs': 0,
                'react_dev': 0,
                'other': 0
            },
            'by_status': {
                'running': 0,
                'stopped': 0,
                'failed': 0
            },
            'recent_crashes': 0,
            'high_resource_usage': []
        }

        # Count recent crashes across all processes
        cutoff_time = datetime.now() - timedelta(hours=1)
        for process_name, crashes in self.crash_history.items():
            recent_crashes = [
                crash for crash in crashes
                if datetime.fromisoformat(crash['recorded_at']) > cutoff_time
            ]
            summary['recent_crashes'] += len(recent_crashes)

        for name, process in self.processes.items():
            # Count by type
            if process.config.process_type == ProcessType.NODEJS:
                if self._is_react_dev_server(process):
                    summary['by_type']['react_dev'] += 1
                else:
                    summary['by_type']['nodejs'] += 1
            else:
                summary['by_type']['other'] += 1

            # Count by status
            summary['by_status'][process.status.value] += 1

            # Check for high resource usage
            metrics = self.get_process_metrics(name)
            if metrics and (metrics.cpu_percent > 80 or metrics.memory_percent > 80):
                summary['high_resource_usage'].append({
                    'name': name,
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent
                })

        return summary