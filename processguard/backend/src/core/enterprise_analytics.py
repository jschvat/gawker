import asyncio
import statistics
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
import json

from ..utils.logging import get_logger

@dataclass
class TrendAnalysis:
    metric_name: str
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    slope: float
    confidence: float
    prediction_24h: float

class EnterpriseAnalytics:
    """Advanced analytics and reporting for enterprise monitoring"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.metrics_buffer = defaultdict(lambda: deque(maxlen=10000))
        self.anomaly_models = {}
        self.capacity_models = {}
        self.performance_baselines = {}

    async def ingest_metrics(self, service_name: str, metrics: Dict[str, Any]):
        """Ingest metrics for analysis"""
        timestamp = datetime.now()

        metric_point = {
            'timestamp': timestamp,
            'service_name': service_name,
            **metrics
        }

        self.metrics_buffer[service_name].append(metric_point)

        # Trigger real-time analysis
        await self._real_time_analysis(service_name, metric_point)

    async def _real_time_analysis(self, service_name: str, metric_point: Dict[str, Any]):
        """Perform real-time analysis on incoming metrics"""
        # Anomaly detection
        anomalies = await self._detect_anomalies(service_name, metric_point)

        # Capacity planning
        capacity_alerts = await self._check_capacity_thresholds(service_name, metric_point)

        # Performance regression detection
        performance_issues = await self._detect_performance_regression(service_name, metric_point)

    async def _detect_anomalies(self, service_name: str, metric_point: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect anomalies using statistical methods"""
        anomalies = []

        recent_metrics = list(self.metrics_buffer[service_name])[-100:]  # Last 100 points

        if len(recent_metrics) < 20:  # Need enough data
            return anomalies

        for metric_name, value in metric_point.items():
            if metric_name in ['timestamp', 'service_name'] or not isinstance(value, (int, float)):
                continue

            # Get historical values
            historical_values = [m.get(metric_name, 0) for m in recent_metrics if isinstance(m.get(metric_name), (int, float))]

            if len(historical_values) < 10:
                continue

            # Statistical anomaly detection
            mean_val = statistics.mean(historical_values)
            std_val = statistics.stdev(historical_values) if len(historical_values) > 1 else 0

            if std_val > 0:
                z_score = abs(value - mean_val) / std_val

                if z_score > 3:  # 3-sigma rule
                    anomalies.append({
                        'type': 'statistical_anomaly',
                        'metric': metric_name,
                        'current_value': value,
                        'expected_value': mean_val,
                        'z_score': z_score,
                        'severity': 'high' if z_score > 4 else 'medium'
                    })

        return anomalies

    async def generate_trend_analysis(self, service_name: str, time_window: int = 86400) -> Dict[str, TrendAnalysis]:
        """Generate trend analysis for service metrics"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)

        recent_metrics = [
            m for m in self.metrics_buffer[service_name]
            if m['timestamp'] > cutoff_time
        ]

        if len(recent_metrics) < 10:
            return {}

        trends = {}

        # Analyze each numeric metric
        metric_names = set()
        for metric in recent_metrics:
            for key, value in metric.items():
                if key not in ['timestamp', 'service_name'] and isinstance(value, (int, float)):
                    metric_names.add(key)

        for metric_name in metric_names:
            trend = await self._calculate_trend(recent_metrics, metric_name)
            if trend:
                trends[metric_name] = trend

        return trends

    async def _calculate_trend(self, metrics: List[Dict[str, Any]], metric_name: str) -> Optional[TrendAnalysis]:
        """Calculate trend for a specific metric"""
        try:
            # Extract time series data
            data_points = []
            for metric in metrics:
                if metric_name in metric and isinstance(metric[metric_name], (int, float)):
                    timestamp = metric['timestamp'].timestamp()
                    value = metric[metric_name]
                    data_points.append((timestamp, value))

            if len(data_points) < 5:
                return None

            # Sort by timestamp
            data_points.sort(key=lambda x: x[0])

            # Extract x and y values
            x_values = np.array([dp[0] for dp in data_points])
            y_values = np.array([dp[1] for dp in data_points])

            # Normalize x values to start from 0
            x_values = x_values - x_values[0]

            # Calculate linear regression
            slope, intercept = np.polyfit(x_values, y_values, 1)

            # Calculate R-squared for confidence
            y_pred = slope * x_values + intercept
            ss_res = np.sum((y_values - y_pred) ** 2)
            ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            # Determine trend direction
            if abs(slope) < 0.01:  # Threshold for stable
                trend_direction = 'stable'
            elif slope > 0:
                trend_direction = 'increasing'
            else:
                trend_direction = 'decreasing'

            # Predict 24h ahead
            seconds_24h = 24 * 3600
            prediction_24h = slope * (x_values[-1] + seconds_24h) + intercept

            return TrendAnalysis(
                metric_name=metric_name,
                trend_direction=trend_direction,
                slope=slope,
                confidence=r_squared,
                prediction_24h=prediction_24h
            )

        except Exception as e:
            self.logger.error(f"Trend calculation failed for {metric_name}: {e}")
            return None

    async def generate_capacity_forecast(self, service_name: str) -> Dict[str, Any]:
        """Generate capacity planning forecast"""
        trends = await self.generate_trend_analysis(service_name)

        capacity_forecast = {
            'service_name': service_name,
            'forecast_horizon_days': 30,
            'metrics': {},
            'recommendations': []
        }

        # Define capacity thresholds
        capacity_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_usage_percent': 90,
            'connection_count': 1000
        }

        for metric_name, trend in trends.items():
            if metric_name in capacity_thresholds:
                threshold = capacity_thresholds[metric_name]

                # Calculate days until threshold
                current_value = self._get_latest_metric_value(service_name, metric_name)
                if current_value is None:
                    continue

                days_to_threshold = None
                if trend.trend_direction == 'increasing' and trend.slope > 0:
                    # Calculate when it will hit threshold
                    time_to_threshold = (threshold - current_value) / (trend.slope * 86400)  # slope per day
                    days_to_threshold = time_to_threshold if time_to_threshold > 0 else None

                capacity_forecast['metrics'][metric_name] = {
                    'current_value': current_value,
                    'threshold': threshold,
                    'trend_direction': trend.trend_direction,
                    'days_to_threshold': days_to_threshold,
                    'predicted_30d': trend.prediction_24h,  # Simplified
                    'utilization_percent': (current_value / threshold) * 100
                }

                # Generate recommendations
                if days_to_threshold and days_to_threshold < 30:
                    severity = 'critical' if days_to_threshold < 7 else 'warning'
                    capacity_forecast['recommendations'].append({
                        'metric': metric_name,
                        'severity': severity,
                        'message': f'{metric_name} will reach capacity in {days_to_threshold:.1f} days',
                        'action': f'Scale up {metric_name.split("_")[0]} resources'
                    })

        return capacity_forecast

    def _get_latest_metric_value(self, service_name: str, metric_name: str) -> Optional[float]:
        """Get latest value for a metric"""
        recent_metrics = list(self.metrics_buffer[service_name])
        for metric in reversed(recent_metrics):
            if metric_name in metric and isinstance(metric[metric_name], (int, float)):
                return metric[metric_name]
        return None

    async def generate_performance_report(self, service_name: str, time_window: int = 86400) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)

        recent_metrics = [
            m for m in self.metrics_buffer[service_name]
            if m['timestamp'] > cutoff_time
        ]

        if not recent_metrics:
            return {'status': 'no_data'}

        # Calculate performance statistics
        report = {
            'service_name': service_name,
            'time_window_hours': time_window / 3600,
            'data_points': len(recent_metrics),
            'performance_summary': {},
            'sla_compliance': {},
            'recommendations': []
        }

        # Performance metrics analysis
        performance_metrics = ['cpu_percent', 'memory_percent', 'response_time', 'throughput']

        for metric in performance_metrics:
            values = [m.get(metric) for m in recent_metrics if m.get(metric) is not None]

            if values:
                report['performance_summary'][metric] = {
                    'average': statistics.mean(values),
                    'median': statistics.median(values),
                    'p95': self._percentile(values, 95),
                    'p99': self._percentile(values, 99),
                    'min': min(values),
                    'max': max(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0
                }

        # SLA compliance check
        sla_thresholds = {
            'response_time': 1000,  # ms
            'availability': 99.9,    # %
            'error_rate': 1.0       # %
        }

        for sla_metric, threshold in sla_thresholds.items():
            if sla_metric in report['performance_summary']:
                avg_value = report['performance_summary'][sla_metric]['average']
                compliant = avg_value <= threshold

                report['sla_compliance'][sla_metric] = {
                    'threshold': threshold,
                    'current_value': avg_value,
                    'compliant': compliant,
                    'compliance_percentage': min(100, (threshold / avg_value) * 100) if avg_value > 0 else 100
                }

        return report

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def generate_cost_analysis(self, service_name: str) -> Dict[str, Any]:
        """Generate cost analysis and optimization recommendations"""
        # This would integrate with cloud provider APIs for actual costs
        cost_analysis = {
            'service_name': service_name,
            'current_monthly_cost': 0,  # Would be calculated from actual usage
            'cost_breakdown': {
                'compute': 0,
                'storage': 0,
                'network': 0,
                'monitoring': 0
            },
            'optimization_opportunities': [],
            'projected_savings': 0
        }

        # Analyze resource utilization for cost optimization
        latest_metrics = list(self.metrics_buffer[service_name])[-100:]

        if latest_metrics:
            avg_cpu = statistics.mean([m.get('cpu_percent', 0) for m in latest_metrics])
            avg_memory = statistics.mean([m.get('memory_percent', 0) for m in latest_metrics])

            # Generate cost optimization recommendations
            if avg_cpu < 30:
                cost_analysis['optimization_opportunities'].append({
                    'type': 'rightsizing',
                    'description': 'CPU utilization is low - consider downsizing instance',
                    'potential_savings_percent': 25,
                    'current_utilization': avg_cpu
                })

            if avg_memory < 40:
                cost_analysis['optimization_opportunities'].append({
                    'type': 'rightsizing',
                    'description': 'Memory utilization is low - consider memory-optimized instance',
                    'potential_savings_percent': 15,
                    'current_utilization': avg_memory
                })

        return cost_analysis

    async def generate_executive_dashboard(self) -> Dict[str, Any]:
        """Generate executive-level dashboard data"""
        dashboard = {
            'timestamp': datetime.now(),
            'services_monitored': len(self.metrics_buffer),
            'overall_health': 'healthy',  # Would be calculated
            'key_metrics': {
                'availability': 99.95,
                'performance_score': 85,
                'cost_efficiency': 78,
                'security_score': 92
            },
            'active_incidents': 0,
            'monthly_trends': {},
            'cost_summary': {
                'current_month': 0,
                'projected_month': 0,
                'savings_opportunities': 0
            },
            'recommendations': [
                {
                    'priority': 'high',
                    'category': 'performance',
                    'description': 'Optimize database queries for 15% performance improvement'
                },
                {
                    'priority': 'medium',
                    'category': 'cost',
                    'description': 'Right-size underutilized instances to save 20% on compute costs'
                }
            ]
        }

        return dashboard