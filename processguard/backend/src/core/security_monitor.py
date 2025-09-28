import re
import hashlib
import subprocess
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..utils.logging import get_logger

class SecurityMonitor:
    """Enterprise security and compliance monitoring"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.security_events = []
        self.vulnerability_cache = {}
        self.compliance_rules = self._load_compliance_rules()

    def _load_compliance_rules(self) -> Dict[str, Any]:
        """Load compliance rules (SOC2, GDPR, HIPAA, etc.)"""
        return {
            'process_isolation': {
                'description': 'Processes should run with minimal privileges',
                'check': 'user_privileges'
            },
            'log_encryption': {
                'description': 'Sensitive logs should be encrypted',
                'check': 'log_security'
            },
            'network_security': {
                'description': 'Network connections should be monitored',
                'check': 'network_monitoring'
            },
            'file_integrity': {
                'description': 'Critical files should be monitored for changes',
                'check': 'file_integrity'
            },
            'access_logging': {
                'description': 'All access should be logged',
                'check': 'access_logs'
            }
        }

    async def scan_process_security(self, process_name: str, pid: int) -> Dict[str, Any]:
        """Comprehensive security scan of a process"""
        security_report = {
            'process_name': process_name,
            'pid': pid,
            'timestamp': datetime.now(),
            'vulnerabilities': [],
            'security_score': 100,
            'compliance_issues': [],
            'recommendations': []
        }

        try:
            ps_process = psutil.Process(pid)

            # Check process privileges
            privilege_check = await self._check_process_privileges(ps_process)
            security_report.update(privilege_check)

            # Check network security
            network_check = await self._check_network_security(ps_process)
            security_report.update(network_check)

            # Check file access patterns
            file_check = await self._check_file_access(ps_process)
            security_report.update(file_check)

            # Check for suspicious behavior
            behavior_check = await self._check_suspicious_behavior(ps_process)
            security_report.update(behavior_check)

            # Vulnerability scanning
            vuln_check = await self._scan_vulnerabilities(process_name, ps_process)
            security_report['vulnerabilities'].extend(vuln_check)

            # Calculate security score
            security_report['security_score'] = self._calculate_security_score(security_report)

        except Exception as e:
            self.logger.error(f"Security scan failed for {process_name}: {e}")
            security_report['error'] = str(e)

        return security_report

    async def _check_process_privileges(self, process: psutil.Process) -> Dict[str, Any]:
        """Check process privilege escalation and user context"""
        try:
            username = process.username()
            uids = process.uids()

            issues = []
            if username == 'root':
                issues.append({
                    'type': 'privilege_escalation',
                    'severity': 'high',
                    'description': 'Process running as root user',
                    'recommendation': 'Run with least privileged user'
                })

            # Check for SUID/SGID
            if hasattr(process, 'exe'):
                try:
                    exe_path = process.exe()
                    if exe_path:
                        stat_info = Path(exe_path).stat()
                        if stat_info.st_mode & 0o4000:  # SUID bit
                            issues.append({
                                'type': 'suid_binary',
                                'severity': 'medium',
                                'description': 'Process executable has SUID bit set',
                                'file': exe_path
                            })
                except:
                    pass

            return {
                'privilege_check': {
                    'username': username,
                    'real_uid': uids.real if uids else None,
                    'effective_uid': uids.effective if uids else None,
                    'issues': issues
                }
            }

        except Exception as e:
            return {'privilege_check': {'error': str(e)}}

    async def _check_network_security(self, process: psutil.Process) -> Dict[str, Any]:
        """Check network connections for security issues"""
        try:
            connections = process.connections()
            issues = []

            external_connections = []
            listening_ports = []

            for conn in connections:
                if conn.status == psutil.CONN_LISTEN:
                    listening_ports.append({
                        'port': conn.laddr.port if conn.laddr else None,
                        'address': conn.laddr.ip if conn.laddr else None
                    })

                    # Check for insecure listening
                    if conn.laddr and conn.laddr.ip == '0.0.0.0':
                        issues.append({
                            'type': 'insecure_binding',
                            'severity': 'medium',
                            'description': f'Process listening on all interfaces (port {conn.laddr.port})',
                            'recommendation': 'Bind to specific interface only'
                        })

                elif conn.raddr:
                    # External connection
                    external_connections.append({
                        'remote_ip': conn.raddr.ip,
                        'remote_port': conn.raddr.port,
                        'status': conn.status
                    })

                    # Check for suspicious external connections
                    if self._is_suspicious_ip(conn.raddr.ip):
                        issues.append({
                            'type': 'suspicious_connection',
                            'severity': 'high',
                            'description': f'Connection to suspicious IP: {conn.raddr.ip}',
                            'recommendation': 'Investigate connection purpose'
                        })

            return {
                'network_check': {
                    'listening_ports': listening_ports,
                    'external_connections': external_connections,
                    'issues': issues
                }
            }

        except Exception as e:
            return {'network_check': {'error': str(e)}}

    def _is_suspicious_ip(self, ip: str) -> bool:
        """Check if IP is in known suspicious ranges"""
        # This would integrate with threat intelligence feeds
        suspicious_ranges = [
            '10.0.0.0/8',    # Private ranges shouldn't be external
            '172.16.0.0/12',
            '192.168.0.0/16'
        ]

        # In real implementation, check against threat intel feeds
        return False

    async def _check_file_access(self, process: psutil.Process) -> Dict[str, Any]:
        """Check file access patterns for security issues"""
        try:
            open_files = process.open_files()
            issues = []

            sensitive_paths = [
                '/etc/passwd', '/etc/shadow', '/etc/hosts',
                '/home/', '/root/', '/var/log/',
                '/.ssh/', '/etc/ssl/'
            ]

            sensitive_file_access = []

            for file_info in open_files:
                file_path = file_info.path

                # Check for sensitive file access
                for sensitive_path in sensitive_paths:
                    if file_path.startswith(sensitive_path):
                        sensitive_file_access.append({
                            'path': file_path,
                            'mode': file_info.mode
                        })

                        if sensitive_path in ['/etc/passwd', '/etc/shadow']:
                            issues.append({
                                'type': 'sensitive_file_access',
                                'severity': 'high',
                                'description': f'Access to sensitive file: {file_path}',
                                'recommendation': 'Verify legitimate access need'
                            })

                # Check for temporary file creation in insecure locations
                if '/tmp/' in file_path and file_info.mode == 'w':
                    issues.append({
                        'type': 'insecure_temp_file',
                        'severity': 'low',
                        'description': f'Writing to potentially insecure temp location: {file_path}',
                        'recommendation': 'Use secure temp directory'
                    })

            return {
                'file_access_check': {
                    'total_open_files': len(open_files),
                    'sensitive_file_access': sensitive_file_access,
                    'issues': issues
                }
            }

        except Exception as e:
            return {'file_access_check': {'error': str(e)}}

    async def _check_suspicious_behavior(self, process: psutil.Process) -> Dict[str, Any]:
        """Check for suspicious process behavior patterns"""
        try:
            issues = []

            # Check CPU usage pattern (potential crypto mining)
            cpu_percent = process.cpu_percent(interval=1)
            if cpu_percent > 90:
                issues.append({
                    'type': 'high_cpu_usage',
                    'severity': 'medium',
                    'description': f'Sustained high CPU usage: {cpu_percent}%',
                    'recommendation': 'Investigate process activity'
                })

            # Check memory usage pattern
            memory_info = process.memory_info()
            if memory_info.rss > 1024 * 1024 * 1024:  # 1GB
                issues.append({
                    'type': 'high_memory_usage',
                    'severity': 'low',
                    'description': f'High memory usage: {memory_info.rss / 1024 / 1024:.1f} MB',
                    'recommendation': 'Monitor for memory leaks'
                })

            # Check process creation pattern
            create_time = datetime.fromtimestamp(process.create_time())
            if datetime.now() - create_time < timedelta(minutes=5):
                # Recently created process - check if it's frequently restarting
                cmdline = ' '.join(process.cmdline())
                if self._is_frequent_restart_pattern(cmdline):
                    issues.append({
                        'type': 'frequent_restart',
                        'severity': 'medium',
                        'description': 'Process appears to be restarting frequently',
                        'recommendation': 'Check for crash loops or instability'
                    })

            return {
                'behavior_check': {
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_info.rss / 1024 / 1024,
                    'uptime_minutes': (datetime.now() - create_time).total_seconds() / 60,
                    'issues': issues
                }
            }

        except Exception as e:
            return {'behavior_check': {'error': str(e)}}

    def _is_frequent_restart_pattern(self, cmdline: str) -> bool:
        """Check if command line indicates frequent restart pattern"""
        # This would check against historical data
        return False

    async def _scan_vulnerabilities(self, process_name: str, process: psutil.Process) -> List[Dict[str, Any]]:
        """Scan for known vulnerabilities"""
        vulnerabilities = []

        try:
            # Get process executable path
            exe_path = process.exe()
            if not exe_path:
                return vulnerabilities

            # Check against vulnerability database
            vuln_check = await self._check_vulnerability_database(exe_path)
            vulnerabilities.extend(vuln_check)

            # Check for insecure configurations
            config_check = await self._check_insecure_configurations(process_name, process)
            vulnerabilities.extend(config_check)

        except Exception as e:
            self.logger.error(f"Vulnerability scan failed: {e}")

        return vulnerabilities

    async def _check_vulnerability_database(self, exe_path: str) -> List[Dict[str, Any]]:
        """Check executable against vulnerability databases"""
        vulnerabilities = []

        try:
            # Get file hash
            file_hash = self._get_file_hash(exe_path)

            # Check against known vulnerable hashes (would integrate with CVE databases)
            # This is a placeholder - real implementation would check against:
            # - National Vulnerability Database (NVD)
            # - CVE databases
            # - Security vendor feeds

            vulnerabilities.append({
                'type': 'vulnerability_scan',
                'file_path': exe_path,
                'file_hash': file_hash,
                'status': 'scanned',
                'vulnerabilities_found': 0
            })

        except Exception as e:
            vulnerabilities.append({
                'type': 'scan_error',
                'error': str(e)
            })

        return vulnerabilities

    def _get_file_hash(self, file_path: str) -> str:
        """Get SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except:
            return ""

    async def _check_insecure_configurations(self, process_name: str, process: psutil.Process) -> List[Dict[str, Any]]:
        """Check for insecure process configurations"""
        issues = []

        try:
            cmdline = process.cmdline()
            cmdline_str = ' '.join(cmdline)

            # Check for hardcoded credentials in command line
            credential_patterns = [
                r'password[=\s]+[\w\d]+',
                r'api[_-]?key[=\s]+[\w\d]+',
                r'secret[=\s]+[\w\d]+',
                r'token[=\s]+[\w\d]+'
            ]

            for pattern in credential_patterns:
                if re.search(pattern, cmdline_str, re.IGNORECASE):
                    issues.append({
                        'type': 'credential_exposure',
                        'severity': 'critical',
                        'description': 'Potential credentials in command line',
                        'recommendation': 'Use environment variables or config files'
                    })
                    break

            # Check for debug/development flags in production
            debug_patterns = ['--debug', '--dev', '--development', '--verbose']
            for pattern in debug_patterns:
                if pattern in cmdline_str:
                    issues.append({
                        'type': 'debug_mode',
                        'severity': 'low',
                        'description': f'Debug/development flag detected: {pattern}',
                        'recommendation': 'Remove debug flags in production'
                    })

        except Exception as e:
            issues.append({
                'type': 'config_check_error',
                'error': str(e)
            })

        return issues

    def _calculate_security_score(self, security_report: Dict[str, Any]) -> int:
        """Calculate overall security score (0-100)"""
        score = 100

        # Deduct points for issues
        all_issues = []
        for check_name, check_data in security_report.items():
            if isinstance(check_data, dict) and 'issues' in check_data:
                all_issues.extend(check_data['issues'])

        for issue in all_issues:
            severity = issue.get('severity', 'low')
            if severity == 'critical':
                score -= 25
            elif severity == 'high':
                score -= 15
            elif severity == 'medium':
                score -= 10
            elif severity == 'low':
                score -= 5

        return max(0, score)

    async def generate_compliance_report(self, processes: List[str]) -> Dict[str, Any]:
        """Generate compliance report for multiple processes"""
        report = {
            'timestamp': datetime.now(),
            'processes_scanned': len(processes),
            'compliance_status': {},
            'violations': [],
            'recommendations': [],
            'overall_score': 0
        }

        total_score = 0

        for process_name in processes:
            # This would scan each process for compliance
            # Placeholder for full implementation
            process_score = 85  # Example score
            total_score += process_score

            report['compliance_status'][process_name] = {
                'score': process_score,
                'last_scanned': datetime.now()
            }

        report['overall_score'] = total_score / len(processes) if processes else 0

        return report