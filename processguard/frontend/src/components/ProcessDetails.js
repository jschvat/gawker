import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  Alert,
  CircularProgress
} from '@mui/material';
import { processApi } from '../services/api';

function ProcessDetails() {
  const { processName } = useParams();
  const [process, setProcess] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProcessDetails();
  }, [processName]);

  const loadProcessDetails = async () => {
    try {
      setLoading(true);
      const response = await processApi.get(processName);
      setProcess(response.data);
    } catch (err) {
      setError('Failed to load process details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!process) {
    return (
      <Alert severity="warning" sx={{ mt: 2 }}>
        Process not found
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Process: {process.name}
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Status
              </Typography>
              <Chip
                label={process.status}
                color={process.status === 'running' ? 'success' : 'error'}
                sx={{ mb: 2 }}
              />
              <Typography variant="body2">
                <strong>PID:</strong> {process.pid || 'N/A'}
              </Typography>
              <Typography variant="body2">
                <strong>Started:</strong> {process.started_at ? new Date(process.started_at).toLocaleString() : 'N/A'}
              </Typography>
              <Typography variant="body2">
                <strong>Restarts:</strong> {process.restart_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configuration
              </Typography>
              <Typography variant="body2">
                <strong>Command:</strong> {process.config.command}
              </Typography>
              <Typography variant="body2">
                <strong>Working Dir:</strong> {process.config.working_dir}
              </Typography>
              <Typography variant="body2">
                <strong>Auto Restart:</strong> {process.config.auto_restart ? 'Yes' : 'No'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {process.latest_metrics && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Metrics
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2">
                      <strong>CPU:</strong> {process.latest_metrics.cpu_percent.toFixed(1)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2">
                      <strong>Memory:</strong> {process.latest_metrics.memory_percent.toFixed(1)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2">
                      <strong>Memory (MB):</strong> {process.latest_metrics.memory_mb.toFixed(1)}
                    </Typography>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2">
                      <strong>Uptime:</strong> {(process.latest_metrics.uptime / 3600).toFixed(1)}h
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        <Grid item xs={12}>
          <Box display="flex" gap={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => processApi.start(processName)}
              disabled={process.status === 'running'}
            >
              Start
            </Button>
            <Button
              variant="contained"
              color="warning"
              onClick={() => processApi.restart(processName)}
              disabled={process.status !== 'running'}
            >
              Restart
            </Button>
            <Button
              variant="contained"
              color="error"
              onClick={() => processApi.stop(processName)}
              disabled={process.status !== 'running'}
            >
              Stop
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

export default ProcessDetails;