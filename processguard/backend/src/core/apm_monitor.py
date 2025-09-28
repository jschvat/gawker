import time
import asyncio
import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque, defaultdict
import psutil
import requests

from ..utils.logging import get_logger

class APMMonitor:
    """Application Performance Monitoring for enterprise-grade insights"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.transaction_traces = defaultdict(lambda: deque(maxlen=1000))
        self.error_traces = defaultdict(lambda: deque(maxlen=500))
        self.performance_baselines = {}
        self.sla_violations = defaultdict(list)

    async def trace_transaction(self, process_name: str, transaction_data: Dict[str, Any]):
        """Record transaction performance data"""
        trace = {
            'timestamp': datetime.now(),
            'transaction_id': transaction_data.get('id'),
            'endpoint': transaction_data.get('endpoint'),
            'method': transaction_data.get('method'),
            'response_time': transaction_data.get('response_time'),
            'status_code': transaction_data.get('status_code'),
            'error': transaction_data.get('error'),
            'user_agent': transaction_data.get('user_agent'),
            'ip_address': transaction_data.get('ip_address'),
            'database_time': transaction_data.get('database_time', 0),
            'external_calls': transaction_data.get('external_calls', [])
        }

        self.transaction_traces[process_name].append(trace)

        # Check for SLA violations
        await self._check_sla_violations(process_name, trace)

    def get_performance_metrics(self, process_name: str, time_window: int = 3600) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)

        recent_traces = [
            trace for trace in self.transaction_traces[process_name]
            if trace['timestamp'] > cutoff_time
        ]

        if not recent_traces:
            return {'status': 'no_data'}

        response_times = [t['response_time'] for t in recent_traces if t['response_time']]
        error_count = len([t for t in recent_traces if t.get('error')])

        return {
            'total_requests': len(recent_traces),
            'error_rate': (error_count / len(recent_traces)) * 100 if recent_traces else 0,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'p95_response_time': self._percentile(response_times, 95) if response_times else 0,
            'p99_response_time': self._percentile(response_times, 99) if response_times else 0,
            'throughput': len(recent_traces) / (time_window / 60),  # requests per minute
            'slowest_endpoints': self._get_slowest_endpoints(recent_traces),
            'error_breakdown': self._get_error_breakdown(recent_traces),
            'database_performance': self._get_database_metrics(recent_traces)
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _get_slowest_endpoints(self, traces: List[Dict]) -> List[Dict]:
        """Get slowest endpoints by average response time"""
        endpoint_times = defaultdict(list)

        for trace in traces:
            if trace.get('endpoint') and trace.get('response_time'):
                endpoint_times[trace['endpoint']].append(trace['response_time'])

        slowest = []
        for endpoint, times in endpoint_times.items():
            slowest.append({
                'endpoint': endpoint,
                'avg_response_time': statistics.mean(times),
                'request_count': len(times),
                'p95_response_time': self._percentile(times, 95)
            })

        return sorted(slowest, key=lambda x: x['avg_response_time'], reverse=True)[:10]

    def _get_error_breakdown(self, traces: List[Dict]) -> Dict[str, int]:
        """Get error breakdown by status code"""
        error_counts = defaultdict(int)

        for trace in traces:
            if trace.get('status_code', 200) >= 400:
                error_counts[str(trace['status_code'])] += 1

        return dict(error_counts)

    def _get_database_metrics(self, traces: List[Dict]) -> Dict[str, Any]:
        """Get database performance metrics"""
        db_times = [t['database_time'] for t in traces if t.get('database_time')]

        if not db_times:
            return {'status': 'no_db_data'}

        return {
            'avg_db_time': statistics.mean(db_times),
            'max_db_time': max(db_times),
            'queries_with_db': len(db_times),
            'db_time_ratio': statistics.mean(db_times) / statistics.mean([t['response_time'] for t in traces if t['response_time']]) if traces else 0
        }

    async def _check_sla_violations(self, process_name: str, trace: Dict[str, Any]):
        """Check for SLA violations"""
        sla_thresholds = {
            'response_time': 2000,  # 2 seconds
            'error_rate': 5.0,      # 5%
            'availability': 99.9    # 99.9%
        }

        violations = []

        # Response time violation
        if trace.get('response_time', 0) > sla_thresholds['response_time']:
            violations.append({
                'type': 'response_time',
                'value': trace['response_time'],
                'threshold': sla_thresholds['response_time'],
                'severity': 'high' if trace['response_time'] > sla_thresholds['response_time'] * 2 else 'medium'
            })

        # Error rate violation (check last 100 requests)
        recent_traces = list(self.transaction_traces[process_name])[-100:]
        if recent_traces:
            error_rate = (len([t for t in recent_traces if t.get('error')]) / len(recent_traces)) * 100
            if error_rate > sla_thresholds['error_rate']:
                violations.append({
                    'type': 'error_rate',
                    'value': error_rate,
                    'threshold': sla_thresholds['error_rate'],
                    'severity': 'critical'
                })

        if violations:
            self.sla_violations[process_name].extend(violations)

    def get_sla_report(self, process_name: str) -> Dict[str, Any]:
        """Generate SLA compliance report"""
        recent_violations = [
            v for v in self.sla_violations[process_name]
            if v.get('timestamp', datetime.now()) > datetime.now() - timedelta(hours=24)
        ]

        return {
            'violations_24h': len(recent_violations),
            'critical_violations': len([v for v in recent_violations if v.get('severity') == 'critical']),
            'sla_compliance': max(0, 100 - len(recent_violations)),
            'violations_by_type': self._group_violations_by_type(recent_violations)
        }

    def _group_violations_by_type(self, violations: List[Dict]) -> Dict[str, int]:
        """Group violations by type"""
        grouped = defaultdict(int)
        for violation in violations:
            grouped[violation['type']] += 1
        return dict(grouped)