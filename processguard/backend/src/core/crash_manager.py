import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum

from ..models.process import ManagedProcess, ProcessStatus
from ..utils.logging import get_logger

class CrashAction(Enum):
    RESTART = "restart"
    DISABLE = "disable"
    KILL_DEPENDENCIES = "kill_dependencies"
    QUARANTINE = "quarantine"

@dataclass
class CrashEvent:
    timestamp: datetime
    process_name: str
    crash_reason: str
    exit_code: Optional[int] = None
    restart_attempt: int = 0

@dataclass
class CrashPolicy:
    max_crashes: int = 5
    time_window_minutes: int = 10
    action_on_threshold: CrashAction = CrashAction.DISABLE
    kill_dependencies: bool = False
    quarantine_duration_minutes: int = 60
    escalation_enabled: bool = True

class CrashManager:
    """Manages application crashes with intelligent policies and dependency handling"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Track crash events per process
        self.crash_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Process dependencies (who depends on whom)
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)

        # Crash policies per process
        self.crash_policies: Dict[str, CrashPolicy] = {}

        # Processes that are disabled due to crashes
        self.disabled_processes: Dict[str, datetime] = {}

        # Quarantined processes
        self.quarantined_processes: Dict[str, datetime] = {}

    def set_crash_policy(self, process_name: str, policy: CrashPolicy):
        """Set crash policy for a specific process"""
        self.crash_policies[process_name] = policy
        self.logger.info(f"Set crash policy for {process_name}: max {policy.max_crashes} crashes in {policy.time_window_minutes} minutes")

    def add_dependency(self, process_name: str, depends_on: str):
        """Add a dependency relationship (process_name depends on depends_on)"""
        self.dependencies[depends_on].add(process_name)
        self.logger.info(f"Added dependency: {process_name} depends on {depends_on}")

    def remove_dependency(self, process_name: str, depends_on: str):
        """Remove a dependency relationship"""
        if depends_on in self.dependencies:
            self.dependencies[depends_on].discard(process_name)
            self.logger.info(f"Removed dependency: {process_name} no longer depends on {depends_on}")

    async def record_crash(self, process_name: str, crash_reason: str,
                          exit_code: Optional[int] = None) -> CrashAction:
        """Record a crash event and determine action"""
        crash_event = CrashEvent(
            timestamp=datetime.now(),
            process_name=process_name,
            crash_reason=crash_reason,
            exit_code=exit_code
        )

        self.crash_history[process_name].append(crash_event)

        self.logger.warning(f"Crash recorded for {process_name}: {crash_reason} (exit code: {exit_code})")

        # Determine action based on crash policy
        action = await self._evaluate_crash_policy(process_name)

        # Execute the determined action
        await self._execute_crash_action(process_name, action, crash_event)

        return action

    async def _evaluate_crash_policy(self, process_name: str) -> CrashAction:
        """Evaluate what action to take based on crash history and policy"""
        policy = self.crash_policies.get(process_name, CrashPolicy())

        # Get crashes within the time window
        time_window = timedelta(minutes=policy.time_window_minutes)
        cutoff_time = datetime.now() - time_window

        recent_crashes = [
            crash for crash in self.crash_history[process_name]
            if crash.timestamp > cutoff_time
        ]

        crash_count = len(recent_crashes)

        self.logger.info(f"{process_name}: {crash_count} crashes in last {policy.time_window_minutes} minutes (threshold: {policy.max_crashes})")

        if crash_count >= policy.max_crashes:
            self.logger.critical(f"Crash threshold exceeded for {process_name}: {crash_count}/{policy.max_crashes}")
            return policy.action_on_threshold
        else:
            # Normal restart
            return CrashAction.RESTART

    async def _execute_crash_action(self, process_name: str, action: CrashAction, crash_event: CrashEvent):
        """Execute the determined crash action"""

        if action == CrashAction.RESTART:
            self.logger.info(f"Action: Normal restart for {process_name}")
            # Normal restart is handled by the process manager

        elif action == CrashAction.DISABLE:
            await self._disable_process(process_name)

        elif action == CrashAction.KILL_DEPENDENCIES:
            await self._disable_process(process_name)
            await self._kill_dependent_processes(process_name)

        elif action == CrashAction.QUARANTINE:
            await self._quarantine_process(process_name)

    async def _disable_process(self, process_name: str):
        """Disable a process due to excessive crashes"""
        self.disabled_processes[process_name] = datetime.now()

        self.logger.critical(f"DISABLING process {process_name} due to excessive crashes")

        # Send alert about process being disabled
        await self._send_crash_alert(process_name, "DISABLED",
                                    f"Process {process_name} has been disabled due to excessive crashes")

    async def _quarantine_process(self, process_name: str):
        """Quarantine a process for a specified duration"""
        policy = self.crash_policies.get(process_name, CrashPolicy())
        quarantine_until = datetime.now() + timedelta(minutes=policy.quarantine_duration_minutes)

        self.quarantined_processes[process_name] = quarantine_until

        self.logger.warning(f"QUARANTINING process {process_name} until {quarantine_until}")

        await self._send_crash_alert(process_name, "QUARANTINED",
                                    f"Process {process_name} quarantined for {policy.quarantine_duration_minutes} minutes")

    async def _kill_dependent_processes(self, failed_process: str):
        """Kill all processes that depend on the failed process"""
        dependent_processes = self.dependencies.get(failed_process, set())

        if not dependent_processes:
            self.logger.info(f"No dependent processes found for {failed_process}")
            return

        self.logger.critical(f"Killing dependent processes of {failed_process}: {dependent_processes}")

        for dependent in dependent_processes:
            self.disabled_processes[dependent] = datetime.now()

            self.logger.critical(f"DISABLING dependent process {dependent} due to {failed_process} failure")

            await self._send_crash_alert(dependent, "DISABLED_DEPENDENCY",
                                        f"Process {dependent} disabled because dependency {failed_process} failed")

    async def _send_crash_alert(self, process_name: str, alert_type: str, message: str):
        """Send alert about crash-related actions"""
        # This would integrate with the existing alert system
        self.logger.critical(f"CRASH ALERT [{alert_type}]: {message}")

    def can_restart_process(self, process_name: str) -> tuple[bool, str]:
        """Check if a process can be restarted (not disabled or quarantined)"""

        # Check if disabled
        if process_name in self.disabled_processes:
            disabled_at = self.disabled_processes[process_name]
            return False, f"Process disabled due to crashes at {disabled_at}"

        # Check if quarantined
        if process_name in self.quarantined_processes:
            quarantine_until = self.quarantined_processes[process_name]
            if datetime.now() < quarantine_until:
                remaining = quarantine_until - datetime.now()
                return False, f"Process quarantined for {remaining.total_seconds():.0f} more seconds"
            else:
                # Quarantine period expired, remove from quarantine
                del self.quarantined_processes[process_name]
                self.logger.info(f"Process {process_name} released from quarantine")

        return True, "Process can be restarted"

    def force_enable_process(self, process_name: str) -> bool:
        """Force enable a disabled process (admin override)"""
        removed = False

        if process_name in self.disabled_processes:
            del self.disabled_processes[process_name]
            removed = True
            self.logger.info(f"Force enabled disabled process: {process_name}")

        if process_name in self.quarantined_processes:
            del self.quarantined_processes[process_name]
            removed = True
            self.logger.info(f"Force enabled quarantined process: {process_name}")

        if removed:
            # Clear recent crash history to give it a fresh start
            self.crash_history[process_name].clear()

        return removed

    def get_crash_statistics(self, process_name: str, hours: int = 24) -> Dict:
        """Get crash statistics for a process"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        crashes = [
            crash for crash in self.crash_history[process_name]
            if crash.timestamp > cutoff_time
        ]

        policy = self.crash_policies.get(process_name, CrashPolicy())

        # Get recent crashes within policy window
        policy_cutoff = datetime.now() - timedelta(minutes=policy.time_window_minutes)
        recent_crashes = [
            crash for crash in crashes
            if crash.timestamp > policy_cutoff
        ]

        return {
            "process_name": process_name,
            "total_crashes_24h": len(crashes),
            "recent_crashes": len(recent_crashes),
            "crash_threshold": policy.max_crashes,
            "time_window_minutes": policy.time_window_minutes,
            "is_disabled": process_name in self.disabled_processes,
            "is_quarantined": process_name in self.quarantined_processes,
            "disabled_at": self.disabled_processes.get(process_name),
            "quarantined_until": self.quarantined_processes.get(process_name),
            "can_restart": self.can_restart_process(process_name)[0],
            "last_crash": crashes[-1].timestamp if crashes else None,
            "most_common_reason": self._get_most_common_crash_reason(crashes)
        }

    def _get_most_common_crash_reason(self, crashes: List[CrashEvent]) -> Optional[str]:
        """Get the most common crash reason"""
        if not crashes:
            return None

        reasons = [crash.crash_reason for crash in crashes]
        return max(set(reasons), key=reasons.count)

    def get_dependency_map(self) -> Dict[str, List[str]]:
        """Get the current dependency map"""
        return {
            process: list(dependents)
            for process, dependents in self.dependencies.items()
        }

    def get_disabled_processes(self) -> Dict[str, Dict]:
        """Get all currently disabled processes"""
        return {
            process: {
                "disabled_at": disabled_at,
                "reason": "excessive_crashes",
                "crash_count": len(self.crash_history[process])
            }
            for process, disabled_at in self.disabled_processes.items()
        }

    def get_quarantined_processes(self) -> Dict[str, Dict]:
        """Get all currently quarantined processes"""
        now = datetime.now()
        return {
            process: {
                "quarantined_until": quarantine_until,
                "remaining_seconds": max(0, (quarantine_until - now).total_seconds()),
                "reason": "crash_quarantine"
            }
            for process, quarantine_until in self.quarantined_processes.items()
        }

    async def cleanup_expired_quarantines(self):
        """Clean up expired quarantines"""
        now = datetime.now()
        expired = [
            process for process, until in self.quarantined_processes.items()
            if now >= until
        ]

        for process in expired:
            del self.quarantined_processes[process]
            self.logger.info(f"Removed expired quarantine for {process}")

    def reset_crash_history(self, process_name: str):
        """Reset crash history for a process (admin function)"""
        if process_name in self.crash_history:
            crash_count = len(self.crash_history[process_name])
            self.crash_history[process_name].clear()
            self.logger.info(f"Reset crash history for {process_name} ({crash_count} crashes cleared)")

    def get_crash_report(self) -> Dict:
        """Generate comprehensive crash report"""
        now = datetime.now()

        report = {
            "timestamp": now,
            "total_processes_monitored": len(self.crash_policies),
            "disabled_processes": len(self.disabled_processes),
            "quarantined_processes": len(self.quarantined_processes),
            "processes_with_recent_crashes": 0,
            "dependency_relationships": len(self.dependencies),
            "crash_statistics": {}
        }

        # Get stats for all monitored processes
        for process_name in self.crash_policies:
            stats = self.get_crash_statistics(process_name, 24)
            report["crash_statistics"][process_name] = stats

            if stats["recent_crashes"] > 0:
                report["processes_with_recent_crashes"] += 1

        return report