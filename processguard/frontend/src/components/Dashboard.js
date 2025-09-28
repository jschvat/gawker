import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip,
  Alert,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

import { processApi, systemApi, alertApi, createWebSocket } from '../services/api';

function Dashboard() {
  const [systemMetrics, setSystemMetrics] = useState(null);
  const [processes, setProcesses] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [metricsHistory, setMetricsHistory] = useState([]);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    fetchInitialData();
    setupWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const fetchInitialData = async () => {
    try {
      const [systemRes, processesRes, alertsRes] = await Promise.all([
        systemApi.getMetrics(),
        processApi.getAll(),
        alertApi.getAll(),
      ]);

      setSystemMetrics(systemRes.data);
      setProcesses(processesRes.data);
      setAlerts(alertsRes.data);
    } catch (error) {
      console.error('Failed to fetch initial data:', error);
    }
  };

  const setupWebSocket = () => {
    const websocket = createWebSocket();

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setSystemMetrics(data.system);
      setProcesses(Object.entries(data.processes).map(([name, metrics]) => ({
        name,
        ...metrics,
      })));
      setAlerts(data.alerts);

      setMetricsHistory((prev) => {
        const newHistory = [...prev, {
          timestamp: data.timestamp,
          cpu: data.system.cpu_percent,
          memory: data.system.memory_percent,
        }];
        return newHistory.slice(-20);
      });
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'success';
      case 'stopped': return 'default';
      case 'failed': return 'error';
      case 'starting': return 'warning';
      default: return 'default';
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const processStatusData = processes.reduce((acc, process) => {
    acc[process.status] = (acc[process.status] || 0) + 1;
    return acc;
  }, {});

  const pieData = Object.entries(processStatusData).map(([status, count]) => ({
    name: status,
    value: count,
  }));

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  if (!systemMetrics) {
    return <LinearProgress />;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      {alerts.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You have {alerts.length} active alert(s) requiring attention.
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                CPU Usage
              </Typography>
              <Typography variant="h4">
                {systemMetrics.cpu_percent.toFixed(1)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={systemMetrics.cpu_percent}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Memory Usage
              </Typography>
              <Typography variant="h4">
                {systemMetrics.memory_percent.toFixed(1)}%
              </Typography>
              <Typography variant="body2">
                {formatBytes(systemMetrics.memory_total - systemMetrics.memory_available)} / {formatBytes(systemMetrics.memory_total)}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={systemMetrics.memory_percent}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Processes
              </Typography>
              <Typography variant="h4">
                {processes.length}
              </Typography>
              <Typography variant="body2">
                Running: {processes.filter(p => p.status === 'running').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Alerts
              </Typography>
              <Typography variant="h4">
                {alerts.length}
              </Typography>
              <Typography variant="body2">
                Critical: {alerts.filter(a => a.level === 'critical').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Metrics Over Time
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={metricsHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="timestamp"
                    tickFormatter={(time) => new Date(time).toLocaleTimeString()}
                  />
                  <YAxis />
                  <Tooltip labelFormatter={(time) => new Date(time).toLocaleString()} />
                  <Line type="monotone" dataKey="cpu" stroke="#8884d8" name="CPU %" />
                  <Line type="monotone" dataKey="memory" stroke="#82ca9d" name="Memory %" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Process Status Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Process Activity
              </Typography>
              <Grid container spacing={2}>
                {processes.slice(0, 6).map((process) => (
                  <Grid item xs={12} sm={6} md={4} key={process.name}>
                    <Card variant="outlined">
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="center">
                          <Typography variant="h6">
                            {process.name}
                          </Typography>
                          <Chip
                            label={process.status}
                            color={getStatusColor(process.status)}
                            size="small"
                          />
                        </Box>
                        <Typography variant="body2" color="textSecondary">
                          CPU: {process.cpu_percent?.toFixed(1) || 0}%
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Memory: {process.memory_mb?.toFixed(1) || 0} MB
                        </Typography>
                        <Typography variant="body2" color="textSecondary">
                          Uptime: {Math.floor((process.uptime || 0) / 60)} min
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;