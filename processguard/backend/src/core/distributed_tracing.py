import uuid
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import aiohttp

from ..utils.logging import get_logger

class DistributedTracing:
    """Distributed tracing for microservices and service mesh monitoring"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.active_traces = {}
        self.completed_traces = deque(maxlen=10000)
        self.service_map = defaultdict(set)
        self.dependency_graph = defaultdict(list)

    async def start_trace(self, service_name: str, operation_name: str,
                         parent_trace_id: Optional[str] = None) -> str:
        """Start a new distributed trace"""
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        trace = {
            'trace_id': trace_id,
            'span_id': span_id,
            'parent_span_id': parent_trace_id,
            'service_name': service_name,
            'operation_name': operation_name,
            'start_time': datetime.now(),
            'end_time': None,
            'duration': None,
            'status': 'active',
            'tags': {},
            'logs': [],
            'child_spans': []
        }

        self.active_traces[trace_id] = trace
        return trace_id

    async def finish_trace(self, trace_id: str, status: str = 'success',
                          error: Optional[str] = None):
        """Finish a distributed trace"""
        if trace_id not in self.active_traces:
            return

        trace = self.active_traces[trace_id]
        trace['end_time'] = datetime.now()
        trace['duration'] = (trace['end_time'] - trace['start_time']).total_seconds() * 1000
        trace['status'] = status

        if error:
            trace['error'] = error

        # Move to completed traces
        self.completed_traces.append(trace)
        del self.active_traces[trace_id]

        # Update service map
        self._update_service_map(trace)

    def add_trace_tag(self, trace_id: str, key: str, value: Any):
        """Add tag to trace"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id]['tags'][key] = value

    def add_trace_log(self, trace_id: str, message: str, level: str = 'info'):
        """Add log entry to trace"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id]['logs'].append({
                'timestamp': datetime.now(),
                'level': level,
                'message': message
            })

    def _update_service_map(self, trace: Dict[str, Any]):
        """Update service dependency map"""
        service = trace['service_name']

        # Add to service map
        self.service_map[service].add(trace['operation_name'])

        # Update dependency graph
        if trace.get('parent_span_id'):
            parent_trace = self._find_parent_trace(trace['parent_span_id'])
            if parent_trace:
                parent_service = parent_trace['service_name']
                if service not in [dep['service'] for dep in self.dependency_graph[parent_service]]:
                    self.dependency_graph[parent_service].append({
                        'service': service,
                        'operation': trace['operation_name'],
                        'first_seen': datetime.now()
                    })

    def _find_parent_trace(self, parent_span_id: str) -> Optional[Dict[str, Any]]:
        """Find parent trace by span ID"""
        for trace in list(self.completed_traces) + list(self.active_traces.values()):
            if trace['span_id'] == parent_span_id:
                return trace
        return None

    def get_service_map(self) -> Dict[str, Any]:
        """Get service dependency map"""
        return {
            'services': dict(self.service_map),
            'dependencies': dict(self.dependency_graph),
            'total_services': len(self.service_map)
        }

    def get_trace_analytics(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get trace analytics for time window"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)

        recent_traces = [
            trace for trace in self.completed_traces
            if trace['start_time'] > cutoff_time
        ]

        if not recent_traces:
            return {'status': 'no_data'}

        # Service performance
        service_performance = defaultdict(list)
        for trace in recent_traces:
            service_performance[trace['service_name']].append(trace['duration'])

        service_stats = {}
        for service, durations in service_performance.items():
            service_stats[service] = {
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'request_count': len(durations),
                'error_count': len([t for t in recent_traces
                                  if t['service_name'] == service and t['status'] == 'error'])
            }

        # Critical path analysis
        critical_paths = self._analyze_critical_paths(recent_traces)

        return {
            'total_traces': len(recent_traces),
            'service_performance': service_stats,
            'critical_paths': critical_paths,
            'error_rate': len([t for t in recent_traces if t['status'] == 'error']) / len(recent_traces) * 100,
            'avg_trace_duration': sum(t['duration'] for t in recent_traces) / len(recent_traces)
        }

    def _analyze_critical_paths(self, traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze critical paths in distributed traces"""
        # Group traces by root operation
        root_traces = defaultdict(list)

        for trace in traces:
            if not trace.get('parent_span_id'):  # Root trace
                root_traces[trace['operation_name']].append(trace)

        critical_paths = []
        for operation, operation_traces in root_traces.items():
            avg_duration = sum(t['duration'] for t in operation_traces) / len(operation_traces)
            critical_paths.append({
                'operation': operation,
                'avg_duration': avg_duration,
                'request_count': len(operation_traces),
                'services_involved': len(set(t['service_name'] for t in operation_traces))
            })

        return sorted(critical_paths, key=lambda x: x['avg_duration'], reverse=True)[:10]

    async def detect_service_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in service behavior"""
        anomalies = []

        # Get recent performance baselines
        recent_traces = list(self.completed_traces)[-1000:]
        service_baselines = defaultdict(list)

        for trace in recent_traces:
            service_baselines[trace['service_name']].append(trace['duration'])

        # Check for anomalies
        for service, durations in service_baselines.items():
            if len(durations) < 10:  # Need enough data
                continue

            avg_duration = sum(durations) / len(durations)
            recent_avg = sum(durations[-10:]) / 10

            # Check for performance degradation
            if recent_avg > avg_duration * 2:  # 100% slower
                anomalies.append({
                    'type': 'performance_degradation',
                    'service': service,
                    'baseline_avg': avg_duration,
                    'recent_avg': recent_avg,
                    'severity': 'high' if recent_avg > avg_duration * 3 else 'medium'
                })

        return anomalies