import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  Delete,
  Add,
  Visibility,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import { processApi } from '../services/api';

function ProcessList() {
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newProcess, setNewProcess] = useState({
    name: '',
    command: '',
    working_dir: '',
    process_type: 'generic',
    auto_restart: true,
    redirect_output: true,
    cpu_threshold: 80,
    memory_threshold: 80,
  });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const navigate = useNavigate();

  useEffect(() => {
    fetchProcesses();
    const interval = setInterval(fetchProcesses, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchProcesses = async () => {
    try {
      const response = await processApi.getAll();
      setProcesses(response.data);
    } catch (error) {
      showSnackbar('Failed to fetch processes', 'error');
    }
    setLoading(false);
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleProcessAction = async (action, processName) => {
    try {
      let response;
      switch (action) {
        case 'start':
          response = await processApi.start(processName);
          break;
        case 'stop':
          response = await processApi.stop(processName);
          break;
        case 'restart':
          response = await processApi.restart(processName);
          break;
        case 'delete':
          if (window.confirm(`Are you sure you want to delete process "${processName}"?`)) {
            response = await processApi.delete(processName);
          } else {
            return;
          }
          break;
        default:
          return;
      }
      showSnackbar(response.data.message, 'success');
      fetchProcesses();
    } catch (error) {
      showSnackbar(error.response?.data?.detail || `Failed to ${action} process`, 'error');
    }
  };

  const handleCreateProcess = async () => {
    try {
      await processApi.create(newProcess);
      showSnackbar('Process created successfully', 'success');
      setOpenDialog(false);
      setNewProcess({
        name: '',
        command: '',
        working_dir: '',
        process_type: 'generic',
        auto_restart: true,
        redirect_output: true,
        cpu_threshold: 80,
        memory_threshold: 80,
      });
      fetchProcesses();
    } catch (error) {
      showSnackbar(error.response?.data?.detail || 'Failed to create process', 'error');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'success';
      case 'stopped': return 'default';
      case 'failed': return 'error';
      case 'starting': return 'warning';
      case 'stopping': return 'warning';
      default: return 'default';
    }
  };

  const formatUptime = (seconds) => {
    if (!seconds) return '0s';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Processes</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setOpenDialog(true)}
        >
          Add Process
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>PID</TableCell>
              <TableCell>CPU %</TableCell>
              <TableCell>Memory</TableCell>
              <TableCell>Uptime</TableCell>
              <TableCell>Restarts</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {processes.map((process) => (
              <TableRow key={process.name}>
                <TableCell>
                  <Typography variant="subtitle1">{process.name}</Typography>
                  <Typography variant="body2" color="textSecondary">
                    {process.config.process_type}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={process.status}
                    color={getStatusColor(process.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>{process.pid || '-'}</TableCell>
                <TableCell>
                  {process.latest_metrics?.cpu_percent?.toFixed(1) || 0}%
                </TableCell>
                <TableCell>
                  {process.latest_metrics?.memory_mb?.toFixed(1) || 0} MB
                </TableCell>
                <TableCell>
                  {formatUptime(process.latest_metrics?.uptime)}
                </TableCell>
                <TableCell>{process.restart_count}</TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => navigate(`/processes/${process.name}`)}
                    title="View Details"
                  >
                    <Visibility />
                  </IconButton>
                  {process.status === 'stopped' || process.status === 'failed' ? (
                    <IconButton
                      size="small"
                      onClick={() => handleProcessAction('start', process.name)}
                      title="Start"
                    >
                      <PlayArrow />
                    </IconButton>
                  ) : (
                    <IconButton
                      size="small"
                      onClick={() => handleProcessAction('stop', process.name)}
                      title="Stop"
                    >
                      <Stop />
                    </IconButton>
                  )}
                  <IconButton
                    size="small"
                    onClick={() => handleProcessAction('restart', process.name)}
                    title="Restart"
                  >
                    <Refresh />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleProcessAction('delete', process.name)}
                    title="Delete"
                  >
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Process</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Process Name"
                value={newProcess.name}
                onChange={(e) => setNewProcess({ ...newProcess, name: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Process Type</InputLabel>
                <Select
                  value={newProcess.process_type}
                  onChange={(e) => setNewProcess({ ...newProcess, process_type: e.target.value })}
                >
                  <MenuItem value="generic">Generic</MenuItem>
                  <MenuItem value="nodejs">Node.js</MenuItem>
                  <MenuItem value="python">Python</MenuItem>
                  <MenuItem value="java">Java</MenuItem>
                  <MenuItem value="go">Go</MenuItem>
                  <MenuItem value="rust">Rust</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Command"
                value={newProcess.command}
                onChange={(e) => setNewProcess({ ...newProcess, command: e.target.value })}
                placeholder="e.g., node server.js"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Working Directory"
                value={newProcess.working_dir}
                onChange={(e) => setNewProcess({ ...newProcess, working_dir: e.target.value })}
                placeholder="e.g., /home/user/myapp"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="CPU Threshold (%)"
                value={newProcess.cpu_threshold}
                onChange={(e) => setNewProcess({ ...newProcess, cpu_threshold: parseFloat(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Memory Threshold (%)"
                value={newProcess.memory_threshold}
                onChange={(e) => setNewProcess({ ...newProcess, memory_threshold: parseFloat(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newProcess.auto_restart}
                    onChange={(e) => setNewProcess({ ...newProcess, auto_restart: e.target.checked })}
                  />
                }
                label="Auto Restart on Failure"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={newProcess.redirect_output}
                    onChange={(e) => setNewProcess({ ...newProcess, redirect_output: e.target.checked })}
                  />
                }
                label="Redirect Output to Logs"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateProcess}>
            Create Process
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
}

export default ProcessList;