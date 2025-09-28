import subprocess
import psutil
import time
import os
import signal
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from ..models.process import ManagedProcess, ProcessConfig, ProcessStatus, ProcessMetrics
from ..utils.logging import get_logger

class ProcessManager:
    def __init__(self):
        self.processes: Dict[str, ManagedProcess] = {}
        self.logger = get_logger(__name__)
        self._subprocess_handles: Dict[str, subprocess.Popen] = {}

    def add_process(self, config: ProcessConfig) -> bool:
        if config.name in self.processes:
            self.logger.warning(f"Process {config.name} already exists")
            return False

        self.processes[config.name] = ManagedProcess(config=config)
        self.logger.info(f"Added process configuration: {config.name}")
        return True

    def remove_process(self, name: str) -> bool:
        if name not in self.processes:
            return False

        if self.processes[name].status == ProcessStatus.RUNNING:
            self.stop_process(name)

        del self.processes[name]
        if name in self._subprocess_handles:
            del self._subprocess_handles[name]

        self.logger.info(f"Removed process: {name}")
        return True

    def start_process(self, name: str) -> bool:
        if name not in self.processes:
            self.logger.error(f"Process {name} not found")
            return False

        process = self.processes[name]
        if process.status == ProcessStatus.RUNNING:
            self.logger.warning(f"Process {name} is already running")
            return True

        try:
            process.status = ProcessStatus.STARTING
            config = process.config

            env = os.environ.copy()
            env.update(config.env_vars)

            working_dir = Path(config.working_dir)
            if not working_dir.exists():
                working_dir.mkdir(parents=True, exist_ok=True)

            log_file = None
            if config.log_file and config.redirect_output:
                log_file = open(config.log_file, 'a')

            stdout = log_file if log_file else (subprocess.PIPE if config.redirect_output else None)
            stderr = subprocess.STDOUT if log_file else (subprocess.PIPE if config.redirect_output else None)

            popen = subprocess.Popen(
                config.command.split(),
                cwd=str(working_dir),
                env=env,
                stdout=stdout,
                stderr=stderr,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

            self._subprocess_handles[name] = popen
            process.pid = popen.pid
            process.started_at = datetime.now()
            process.status = ProcessStatus.RUNNING

            self.logger.info(f"Started process {name} with PID {popen.pid}")
            return True

        except Exception as e:
            process.status = ProcessStatus.FAILED
            self.logger.error(f"Failed to start process {name}: {e}")
            return False

    def stop_process(self, name: str, force: bool = False) -> bool:
        if name not in self.processes:
            return False

        process = self.processes[name]
        if process.status != ProcessStatus.RUNNING:
            return True

        try:
            process.status = ProcessStatus.STOPPING

            if name in self._subprocess_handles:
                popen = self._subprocess_handles[name]

                if force:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(popen.pid), signal.SIGKILL)
                    else:
                        popen.kill()
                else:
                    if os.name != 'nt':
                        os.killpg(os.getpgid(popen.pid), signal.SIGTERM)
                    else:
                        popen.terminate()

                    try:
                        popen.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Process {name} didn't terminate gracefully, killing")
                        if os.name != 'nt':
                            os.killpg(os.getpgid(popen.pid), signal.SIGKILL)
                        else:
                            popen.kill()

                del self._subprocess_handles[name]

            process.status = ProcessStatus.STOPPED
            process.pid = None
            self.logger.info(f"Stopped process {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to stop process {name}: {e}")
            return False

    def restart_process(self, name: str) -> bool:
        if name not in self.processes:
            return False

        process = self.processes[name]

        if process.status == ProcessStatus.RUNNING:
            if not self.stop_process(name):
                return False

        time.sleep(process.config.restart_delay)

        if self.start_process(name):
            process.restart_count += 1
            process.last_restart = datetime.now()
            return True

        return False

    def get_process_metrics(self, name: str) -> Optional[ProcessMetrics]:
        if name not in self.processes:
            return None

        process = self.processes[name]
        if not process.pid:
            return ProcessMetrics(
                timestamp=datetime.now(),
                pid=None,
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_mb=0.0,
                open_files=0,
                connections=[],
                threads=0,
                status=process.status,
                uptime=0.0
            )

        try:
            ps_process = psutil.Process(process.pid)

            uptime = (datetime.now() - process.started_at).total_seconds() if process.started_at else 0.0

            connections = []
            try:
                for conn in ps_process.connections():
                    connections.append({
                        "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                        "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                        "status": conn.status,
                        "type": conn.type.name if hasattr(conn.type, 'name') else str(conn.type)
                    })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass

            metrics = ProcessMetrics(
                timestamp=datetime.now(),
                pid=process.pid,
                cpu_percent=ps_process.cpu_percent(),
                memory_percent=ps_process.memory_percent(),
                memory_mb=ps_process.memory_info().rss / 1024 / 1024,
                open_files=len(ps_process.open_files()),
                connections=connections,
                threads=ps_process.num_threads(),
                status=process.status,
                uptime=uptime
            )

            process.metrics_history.append(metrics)

            if len(process.metrics_history) > 1000:
                process.metrics_history = process.metrics_history[-500:]

            return metrics

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process.status = ProcessStatus.FAILED
            process.pid = None
            return ProcessMetrics(
                timestamp=datetime.now(),
                pid=None,
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_mb=0.0,
                open_files=0,
                connections=[],
                threads=0,
                status=ProcessStatus.FAILED,
                uptime=0.0
            )

    def check_process_health(self, name: str) -> bool:
        if name not in self.processes:
            return False

        process = self.processes[name]

        if name in self._subprocess_handles:
            popen = self._subprocess_handles[name]
            if popen.poll() is not None:
                process.status = ProcessStatus.FAILED
                process.pid = None
                del self._subprocess_handles[name]
                self.logger.warning(f"Process {name} has died")
                return False

        return process.status == ProcessStatus.RUNNING

    def auto_restart_failed_processes(self):
        for name, process in self.processes.items():
            if (process.status == ProcessStatus.FAILED and
                process.config.auto_restart and
                process.restart_count < process.config.max_restarts):

                self.logger.info(f"Auto-restarting failed process: {name}")
                self.restart_process(name)

    def get_all_processes(self) -> Dict[str, ManagedProcess]:
        return self.processes.copy()

    def cleanup(self):
        for name in list(self.processes.keys()):
            if self.processes[name].status == ProcessStatus.RUNNING:
                self.stop_process(name, force=True)