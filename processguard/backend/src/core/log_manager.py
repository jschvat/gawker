import os
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
from collections import deque
import threading
import queue

from ..utils.logging import get_logger

class LogManager:
    def __init__(self, log_base_dir: str = "/var/log/processguard"):
        self.log_base_dir = Path(log_base_dir)
        self.log_base_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__)

        self._log_buffers: Dict[str, deque] = {}
        self._log_files: Dict[str, str] = {}
        self._log_locks: Dict[str, threading.Lock] = {}

        self._max_buffer_size = 1000
        self._log_rotation_size = 10 * 1024 * 1024

    def create_log_file(self, process_name: str) -> str:
        log_dir = self.log_base_dir / process_name
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{process_name}_{timestamp}.log"

        self._log_files[process_name] = str(log_file)
        self._log_buffers[process_name] = deque(maxlen=self._max_buffer_size)
        self._log_locks[process_name] = threading.Lock()

        return str(log_file)

    def write_log(self, process_name: str, message: str, level: str = "INFO"):
        if process_name not in self._log_buffers:
            self.create_log_file(process_name)

        timestamp = datetime.now().isoformat()
        formatted_message = f"[{timestamp}] [{level}] {message}"

        with self._log_locks[process_name]:
            self._log_buffers[process_name].append(formatted_message)

        if process_name in self._log_files:
            self._write_to_file(process_name, formatted_message)

    def _write_to_file(self, process_name: str, message: str):
        try:
            log_file = self._log_files[process_name]

            if os.path.exists(log_file) and os.path.getsize(log_file) > self._log_rotation_size:
                self._rotate_log(process_name)

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
                f.flush()

        except Exception as e:
            self.logger.error(f"Failed to write log for {process_name}: {e}")

    def _rotate_log(self, process_name: str):
        try:
            current_log = self._log_files[process_name]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            log_dir = Path(current_log).parent
            archived_log = log_dir / f"{process_name}_{timestamp}_archived.log"

            os.rename(current_log, archived_log)

            self.create_log_file(process_name)
            self.logger.info(f"Rotated log for {process_name}: {archived_log}")

        except Exception as e:
            self.logger.error(f"Failed to rotate log for {process_name}: {e}")

    def get_recent_logs(self, process_name: str, lines: int = 100) -> List[str]:
        if process_name not in self._log_buffers:
            return []

        with self._log_locks[process_name]:
            buffer = list(self._log_buffers[process_name])

        return buffer[-lines:] if len(buffer) > lines else buffer

    async def get_log_stream(self, process_name: str) -> AsyncGenerator[str, None]:
        if process_name not in self._log_files:
            return

        log_file = self._log_files[process_name]

        try:
            async with aiofiles.open(log_file, 'r') as f:
                await f.seek(0, 2)

                while True:
                    line = await f.readline()
                    if line:
                        yield line.strip()
                    else:
                        await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error streaming logs for {process_name}: {e}")

    def get_log_file_path(self, process_name: str) -> Optional[str]:
        return self._log_files.get(process_name)

    def cleanup_old_logs(self, days: int = 7):
        cutoff_date = datetime.now() - timedelta(days=days)

        for process_dir in self.log_base_dir.iterdir():
            if process_dir.is_dir():
                for log_file in process_dir.glob("*.log"):
                    try:
                        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if file_time < cutoff_date:
                            log_file.unlink()
                            self.logger.info(f"Cleaned up old log file: {log_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to clean up {log_file}: {e}")

    def list_log_files(self, process_name: str) -> List[Dict[str, str]]:
        log_dir = self.log_base_dir / process_name
        if not log_dir.exists():
            return []

        log_files = []
        for log_file in log_dir.glob("*.log"):
            try:
                stat = log_file.stat()
                log_files.append({
                    "name": log_file.name,
                    "path": str(log_file),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "is_current": str(log_file) == self._log_files.get(process_name)
                })
            except Exception as e:
                self.logger.error(f"Failed to get info for {log_file}: {e}")

        return sorted(log_files, key=lambda x: x["modified"], reverse=True)

    async def tail_log_file(self, file_path: str, lines: int = 50) -> List[str]:
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                all_lines = content.splitlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            self.logger.error(f"Failed to tail log file {file_path}: {e}")
            return []

    def remove_process_logs(self, process_name: str):
        if process_name in self._log_buffers:
            del self._log_buffers[process_name]
        if process_name in self._log_files:
            del self._log_files[process_name]
        if process_name in self._log_locks:
            del self._log_locks[process_name]

        log_dir = self.log_base_dir / process_name
        if log_dir.exists():
            try:
                for log_file in log_dir.glob("*.log"):
                    log_file.unlink()
                log_dir.rmdir()
                self.logger.info(f"Removed all logs for process: {process_name}")
            except Exception as e:
                self.logger.error(f"Failed to remove logs for {process_name}: {e}")