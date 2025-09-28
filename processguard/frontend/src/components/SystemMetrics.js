import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  LinearProgress,
  Alert
} from '@mui/material';
import { systemApi } from '../services/api';

function SystemMetrics() {
  const [systemInfo, setSystemInfo] = useState(null);
  const [systemMetrics, setSystemMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadSystemData();
    const interval = setInterval(loadSystemData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadSystemData = async () => {
    try {
      const [infoResponse, metricsResponse] = await Promise.all([
        systemApi.getInfo(),
        systemApi.getMetrics()
      ]);

      setSystemInfo(infoResponse.data);
      setSystemMetrics(metricsResponse.data);
      setError('');
    } catch (err) {
      setError('Failed to load system metrics');
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        System Metrics
      </Typography>

      {systemInfo && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Information
                </Typography>
                <Typography variant="body2">
                  <strong>Hostname:</strong> {systemInfo.hostname}
                </Typography>
                <Typography variant="body2">
                  <strong>Platform:</strong> {systemInfo.platform}
                </Typography>
                <Typography variant="body2">
                  <strong>Architecture:</strong> {systemInfo.architecture}
                </Typography>
                <Typography variant="body2">
                  <strong>CPU Cores:</strong> {systemInfo.cpu_count}
                </Typography>
                <Typography variant="body2">
                  <strong>Total Memory:</strong> {(systemInfo.total_memory / (1024**3)).toFixed(1)} GB
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {systemMetrics && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  CPU Usage
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    {systemMetrics.cpu_percent.toFixed(1)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={systemMetrics.cpu_percent}
                    color={systemMetrics.cpu_percent > 80 ? 'error' : systemMetrics.cpu_percent > 60 ? 'warning' : 'primary'}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Memory Usage
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    {systemMetrics.memory_percent.toFixed(1)}%
                    ({(systemMetrics.memory_total / (1024**3)).toFixed(1)} GB total)
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={systemMetrics.memory_percent}
                    color={systemMetrics.memory_percent > 80 ? 'error' : systemMetrics.memory_percent > 60 ? 'warning' : 'primary'}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {systemMetrics.load_average && (
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Load Average
                  </Typography>
                  <Typography variant="body2">
                    1m: {systemMetrics.load_average[0]?.toFixed(2) || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    5m: {systemMetrics.load_average[1]?.toFixed(2) || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    15m: {systemMetrics.load_average[2]?.toFixed(2) || 'N/A'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )}

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Stats
                </Typography>
                <Typography variant="body2">
                  <strong>Uptime:</strong> {(systemMetrics.uptime / 3600).toFixed(1)} hours
                </Typography>
                <Typography variant="body2">
                  <strong>Active Connections:</strong> {systemMetrics.active_connections || 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default SystemMetrics;