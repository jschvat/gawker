import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Alert,
  Card,
  CardContent
} from '@mui/material';
import { processApi } from '../services/api';

function Logs() {
  const [processes, setProcesses] = useState([]);
  const [selectedProcess, setSelectedProcess] = useState('');
  const [logs, setLogs] = useState([]);
  const [lines, setLines] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProcesses();
  }, []);

  const loadProcesses = async () => {
    try {
      const response = await processApi.getAll();
      setProcesses(response.data);
    } catch (err) {
      setError('Failed to load processes');
    }
  };

  const loadLogs = async () => {
    if (!selectedProcess) return;

    try {
      setLoading(true);
      const response = await processApi.getLogs(selectedProcess, lines);
      setLogs(response.data.logs || []);
      setError('');
    } catch (err) {
      setError('Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Process Logs
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Process</InputLabel>
            <Select
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value)}
              label="Process"
            >
              {processes.map((process) => (
                <MenuItem key={process.name} value={process.name}>
                  {process.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            size="small"
            label="Lines"
            type="number"
            value={lines}
            onChange={(e) => setLines(parseInt(e.target.value) || 100)}
            sx={{ width: 100 }}
          />

          <Button
            variant="contained"
            onClick={loadLogs}
            disabled={!selectedProcess || loading}
          >
            {loading ? 'Loading...' : 'Load Logs'}
          </Button>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {logs.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Logs for {selectedProcess}
            </Typography>
            <Box
              component="pre"
              sx={{
                backgroundColor: '#000',
                color: '#fff',
                p: 2,
                borderRadius: 1,
                fontSize: '0.875rem',
                fontFamily: 'monospace',
                maxHeight: '500px',
                overflow: 'auto',
                whiteSpace: 'pre-wrap'
              }}
            >
              {Array.isArray(logs) ? logs.join('\n') : logs}
            </Box>
          </CardContent>
        </Card>
      )}

      {logs.length === 0 && selectedProcess && !loading && (
        <Alert severity="info">
          No logs available for {selectedProcess}
        </Alert>
      )}
    </Box>
  );
}

export default Logs;