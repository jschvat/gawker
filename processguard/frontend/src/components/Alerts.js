import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Switch,
  Alert,
} from '@mui/material';
import {
  CheckCircle,
  Close,
  Info,
  Warning,
  Error,
} from '@mui/icons-material';
import { format } from 'date-fns';

import { alertApi } from '../services/api';

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [showResolved, setShowResolved] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, [showResolved]);

  const fetchAlerts = async () => {
    try {
      const response = await alertApi.getAll(!showResolved);
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    }
  };

  const handleAcknowledge = async (alertId) => {
    try {
      await alertApi.acknowledge(alertId);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  const handleResolve = async (alertId) => {
    try {
      await alertApi.resolve(alertId);
      fetchAlerts();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const getLevelColor = (level) => {
    switch (level) {
      case 'critical': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'default';
    }
  };

  const getLevelIcon = (level) => {
    switch (level) {
      case 'critical': return <Error />;
      case 'warning': return <Warning />;
      case 'info': return <Info />;
      default: return <Info />;
    }
  };

  const groupedAlerts = alerts.reduce((acc, alert) => {
    const level = alert.level;
    if (!acc[level]) acc[level] = [];
    acc[level].push(alert);
    return acc;
  }, {});

  const alertCounts = {
    critical: alerts.filter(a => a.level === 'critical').length,
    warning: alerts.filter(a => a.level === 'warning').length,
    info: alerts.filter(a => a.level === 'info').length,
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Alerts</Typography>
        <FormControlLabel
          control={
            <Switch
              checked={showResolved}
              onChange={(e) => setShowResolved(e.target.checked)}
            />
          }
          label="Show Resolved"
        />
      </Box>

      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Error color="error" sx={{ mr: 1 }} />
                <Box>
                  <Typography variant="h6">{alertCounts.critical}</Typography>
                  <Typography color="textSecondary">Critical</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Warning color="warning" sx={{ mr: 1 }} />
                <Box>
                  <Typography variant="h6">{alertCounts.warning}</Typography>
                  <Typography color="textSecondary">Warning</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Info color="info" sx={{ mr: 1 }} />
                <Box>
                  <Typography variant="h6">{alertCounts.info}</Typography>
                  <Typography color="textSecondary">Info</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {Object.entries(groupedAlerts).map(([level, levelAlerts]) => (
        <Box key={level} mb={3}>
          <Typography variant="h6" gutterBottom sx={{ textTransform: 'capitalize' }}>
            {level} Alerts ({levelAlerts.length})
          </Typography>
          <Grid container spacing={2}>
            {levelAlerts.map((alert) => (
              <Grid item xs={12} key={alert.id}>
                <Card
                  sx={{
                    border: alert.acknowledged ? 'none' : `2px solid`,
                    borderColor: alert.level === 'critical' ? 'error.main' :
                                alert.level === 'warning' ? 'warning.main' : 'info.main',
                    opacity: alert.acknowledged ? 0.7 : 1,
                  }}
                >
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                      <Box display="flex" alignItems="flex-start" flex={1}>
                        {getLevelIcon(alert.level)}
                        <Box ml={2} flex={1}>
                          <Typography variant="h6">{alert.title}</Typography>
                          <Typography color="textSecondary" gutterBottom>
                            {alert.message}
                          </Typography>
                          <Box display="flex" gap={1} mb={1}>
                            <Chip
                              label={alert.level}
                              color={getLevelColor(alert.level)}
                              size="small"
                            />
                            {alert.process_name && (
                              <Chip
                                label={`Process: ${alert.process_name}`}
                                variant="outlined"
                                size="small"
                              />
                            )}
                            {alert.acknowledged && (
                              <Chip
                                label="Acknowledged"
                                color="success"
                                size="small"
                              />
                            )}
                          </Box>
                          <Typography variant="body2" color="textSecondary">
                            {format(new Date(alert.timestamp), 'PPpp')}
                          </Typography>
                        </Box>
                      </Box>
                      <Box display="flex" gap={1}>
                        <Button
                          size="small"
                          onClick={() => setSelectedAlert(alert)}
                        >
                          Details
                        </Button>
                        {!alert.acknowledged && (
                          <IconButton
                            size="small"
                            onClick={() => handleAcknowledge(alert.id)}
                            title="Acknowledge"
                          >
                            <CheckCircle />
                          </IconButton>
                        )}
                        {!alert.resolved && (
                          <IconButton
                            size="small"
                            onClick={() => handleResolve(alert.id)}
                            title="Resolve"
                          >
                            <Close />
                          </IconButton>
                        )}
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}

      {alerts.length === 0 && (
        <Alert severity="success">
          No alerts to display. Your system is running smoothly!
        </Alert>
      )}

      <Dialog
        open={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedAlert && (
          <>
            <DialogTitle>{selectedAlert.title}</DialogTitle>
            <DialogContent>
              <Typography gutterBottom>{selectedAlert.message}</Typography>

              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                Details
              </Typography>
              <Typography><strong>Type:</strong> {selectedAlert.type}</Typography>
              <Typography><strong>Level:</strong> {selectedAlert.level}</Typography>
              <Typography><strong>Time:</strong> {format(new Date(selectedAlert.timestamp), 'PPpp')}</Typography>
              {selectedAlert.process_name && (
                <Typography><strong>Process:</strong> {selectedAlert.process_name}</Typography>
              )}

              {Object.keys(selectedAlert.metadata).length > 0 && (
                <>
                  <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                    Metadata
                  </Typography>
                  <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px' }}>
                    {JSON.stringify(selectedAlert.metadata, null, 2)}
                  </pre>
                </>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedAlert(null)}>Close</Button>
              {!selectedAlert.acknowledged && (
                <Button
                  variant="contained"
                  onClick={() => {
                    handleAcknowledge(selectedAlert.id);
                    setSelectedAlert(null);
                  }}
                >
                  Acknowledge
                </Button>
              )}
              {!selectedAlert.resolved && (
                <Button
                  variant="contained"
                  color="success"
                  onClick={() => {
                    handleResolve(selectedAlert.id);
                    setSelectedAlert(null);
                  }}
                >
                  Resolve
                </Button>
              )}
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
}

export default Alerts;