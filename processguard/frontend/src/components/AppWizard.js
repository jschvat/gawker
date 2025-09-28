import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Chip,
  Grid,
  Card,
  CardContent,
  CardActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Divider
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Folder as FolderIcon,
  Code as CodeIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Settings as SettingsIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon,
  ContentCopy as CopyIcon
} from '@mui/icons-material';
import { wizardApi, processApi } from '../services/api';

const steps = ['Project Analysis', 'Configuration', 'Script Generation', 'Review & Deploy'];

function AppWizard() {
  const [activeStep, setActiveStep] = useState(0);
  const [projectPath, setProjectPath] = useState('/host/root/home/user/myapp');
  const [projectAnalysis, setProjectAnalysis] = useState(null);
  const [supportedTypes, setSupportedTypes] = useState([]);
  const [selectedAppType, setSelectedAppType] = useState('');
  const [processName, setProcessName] = useState('');
  const [environment, setEnvironment] = useState('development');
  const [customCommand, setCustomCommand] = useState('');
  const [customEnvVars, setCustomEnvVars] = useState({});
  const [customPorts, setCustomPorts] = useState([]);
  const [generatedScripts, setGeneratedScripts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [scriptDialog, setScriptDialog] = useState({ open: false, title: '', content: '' });
  const [envVarKey, setEnvVarKey] = useState('');
  const [envVarValue, setEnvVarValue] = useState('');
  const [portInput, setPortInput] = useState('');

  useEffect(() => {
    loadSupportedTypes();
  }, []);

  const loadSupportedTypes = async () => {
    try {
      const response = await wizardApi.getSupportedTypes();
      setSupportedTypes(response.data.supported_types);
    } catch (err) {
      setError('Failed to load supported application types');
    }
  };

  const handleAnalyzeProject = async () => {
    if (!projectPath.trim()) {
      setError('Please enter a project path');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await wizardApi.analyzeProject(projectPath);
      const analysis = response.data;

      setProjectAnalysis(analysis);
      setSelectedAppType(analysis.app_type);
      setProcessName(projectPath.split('/').pop() || 'my-app');

      // Auto-populate custom command if available
      if (analysis.suggested_commands.start) {
        setCustomCommand(analysis.suggested_commands.start);
      }

      setActiveStep(1);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze project');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateScripts = async () => {
    if (!processName.trim()) {
      setError('Please enter a process name');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const config = {
        project_path: projectPath,
        app_type: selectedAppType,
        process_name: processName,
        environment: environment,
        custom_command: customCommand || null,
        custom_env_vars: Object.keys(customEnvVars).length > 0 ? customEnvVars : null,
        custom_ports: customPorts.length > 0 ? customPorts : null
      };

      const response = await wizardApi.generateScripts(config);
      setGeneratedScripts(response.data);
      setActiveStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate scripts');
    } finally {
      setLoading(false);
    }
  };

  const handleDeployProcess = async () => {
    if (!generatedScripts) return;

    setLoading(true);
    setError('');

    try {
      await processApi.create(generatedScripts.process_config);
      setSuccess(`Process "${processName}" has been deployed successfully!`);
      setActiveStep(0);
      // Reset form
      setProjectPath('/host/root/home/user/myapp');
      setProjectAnalysis(null);
      setSelectedAppType('');
      setProcessName('');
      setCustomCommand('');
      setCustomEnvVars({});
      setCustomPorts([]);
      setGeneratedScripts(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to deploy process');
    } finally {
      setLoading(false);
    }
  };

  const addEnvironmentVariable = () => {
    if (envVarKey.trim() && envVarValue.trim()) {
      setCustomEnvVars({ ...customEnvVars, [envVarKey]: envVarValue });
      setEnvVarKey('');
      setEnvVarValue('');
    }
  };

  const removeEnvironmentVariable = (key) => {
    const newEnvVars = { ...customEnvVars };
    delete newEnvVars[key];
    setCustomEnvVars(newEnvVars);
  };

  const addPort = () => {
    const port = parseInt(portInput);
    if (port && port > 0 && port <= 65535 && !customPorts.includes(port)) {
      setCustomPorts([...customPorts, port]);
      setPortInput('');
    }
  };

  const removePort = (port) => {
    setCustomPorts(customPorts.filter(p => p !== port));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
  };

  const showScript = (title, content) => {
    setScriptDialog({ open: true, title, content });
  };

  const downloadScript = (filename, content) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        App Wizard
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Create launch scripts, kill scripts, and monitoring patterns for your applications
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* Step 0: Project Analysis */}
        {activeStep === 0 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Project Analysis
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Enter the path to your project directory. The wizard will analyze your project and detect the application type.
            </Typography>

            <TextField
              fullWidth
              label="Project Path"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              placeholder="/host/root/home/user/myapp"
              sx={{ mb: 3 }}
              InputProps={{
                startAdornment: <FolderIcon sx={{ mr: 1, color: 'text.secondary' }} />
              }}
            />

            <Button
              variant="contained"
              onClick={handleAnalyzeProject}
              disabled={loading || !projectPath.trim()}
              startIcon={loading ? <CircularProgress size={20} /> : <CodeIcon />}
            >
              {loading ? 'Analyzing...' : 'Analyze Project'}
            </Button>
          </Box>
        )}

        {/* Step 1: Configuration */}
        {activeStep === 1 && projectAnalysis && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Project Configuration
            </Typography>

            {/* Analysis Results */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Analysis Results
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">App Type:</Typography>
                    <Chip label={projectAnalysis.app_type} color="primary" sx={{ mb: 1 }} />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Detected Frameworks:</Typography>
                    <Box>
                      {projectAnalysis.detected_frameworks.map((framework) => (
                        <Chip key={framework} label={framework} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                      ))}
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Package Managers:</Typography>
                    <Box>
                      {projectAnalysis.package_managers.map((pm) => (
                        <Chip key={pm} label={pm} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                      ))}
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" color="text.secondary">Detected Ports:</Typography>
                    <Box>
                      {projectAnalysis.ports.map((port) => (
                        <Chip key={port} label={port} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                      ))}
                    </Box>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Process Name"
                  value={processName}
                  onChange={(e) => setProcessName(e.target.value)}
                  sx={{ mb: 2 }}
                />

                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Application Type</InputLabel>
                  <Select
                    value={selectedAppType}
                    onChange={(e) => setSelectedAppType(e.target.value)}
                    label="Application Type"
                  >
                    {supportedTypes.map((type) => (
                      <MenuItem key={type.type} value={type.type}>
                        {type.name} - {type.description}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Environment</InputLabel>
                  <Select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    label="Environment"
                  >
                    <MenuItem value="development">Development</MenuItem>
                    <MenuItem value="staging">Staging</MenuItem>
                    <MenuItem value="production">Production</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  label="Custom Command (optional)"
                  value={customCommand}
                  onChange={(e) => setCustomCommand(e.target.value)}
                  placeholder={projectAnalysis.suggested_commands.start || 'npm start'}
                  sx={{ mb: 2 }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                {/* Environment Variables */}
                <Typography variant="h6" gutterBottom>
                  Environment Variables
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Grid container spacing={1} sx={{ mb: 1 }}>
                    <Grid item xs={5}>
                      <TextField
                        size="small"
                        label="Key"
                        value={envVarKey}
                        onChange={(e) => setEnvVarKey(e.target.value)}
                      />
                    </Grid>
                    <Grid item xs={5}>
                      <TextField
                        size="small"
                        label="Value"
                        value={envVarValue}
                        onChange={(e) => setEnvVarValue(e.target.value)}
                      />
                    </Grid>
                    <Grid item xs={2}>
                      <Button
                        variant="outlined"
                        onClick={addEnvironmentVariable}
                        disabled={!envVarKey.trim() || !envVarValue.trim()}
                      >
                        Add
                      </Button>
                    </Grid>
                  </Grid>
                  {Object.entries(customEnvVars).map(([key, value]) => (
                    <Chip
                      key={key}
                      label={`${key}=${value}`}
                      onDelete={() => removeEnvironmentVariable(key)}
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>

                {/* Custom Ports */}
                <Typography variant="h6" gutterBottom>
                  Custom Ports
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Grid container spacing={1} sx={{ mb: 1 }}>
                    <Grid item xs={8}>
                      <TextField
                        size="small"
                        label="Port"
                        type="number"
                        value={portInput}
                        onChange={(e) => setPortInput(e.target.value)}
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <Button
                        variant="outlined"
                        onClick={addPort}
                        disabled={!portInput.trim()}
                      >
                        Add
                      </Button>
                    </Grid>
                  </Grid>
                  {customPorts.map((port) => (
                    <Chip
                      key={port}
                      label={port}
                      onDelete={() => removePort(port)}
                      sx={{ mr: 0.5, mb: 0.5 }}
                    />
                  ))}
                </Box>
              </Grid>
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
              <Button onClick={() => setActiveStep(0)}>
                Back
              </Button>
              <Button
                variant="contained"
                onClick={() => setActiveStep(2)}
                disabled={!processName.trim()}
              >
                Next
              </Button>
            </Box>
          </Box>
        )}

        {/* Step 2: Script Generation */}
        {activeStep === 2 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Script Generation
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Review your configuration and generate the launch and kill scripts.
            </Typography>

            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Configuration Summary</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2"><strong>Process Name:</strong> {processName}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2"><strong>App Type:</strong> {selectedAppType}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2"><strong>Environment:</strong> {environment}</Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2"><strong>Project Path:</strong> {projectPath}</Typography>
                  </Grid>
                  {customCommand && (
                    <Grid item xs={12}>
                      <Typography variant="body2"><strong>Command:</strong> {customCommand}</Typography>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setActiveStep(1)}>
                Back
              </Button>
              <Button
                variant="contained"
                onClick={handleGenerateScripts}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <SettingsIcon />}
              >
                {loading ? 'Generating...' : 'Generate Scripts'}
              </Button>
            </Box>
          </Box>
        )}

        {/* Step 3: Review & Deploy */}
        {activeStep === 3 && generatedScripts && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Review & Deploy
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Review the generated scripts and deploy your process to ProcessGuard.
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Launch Script
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Script to start your application
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<VisibilityIcon />}
                      onClick={() => showScript('Launch Script', generatedScripts.launch_script)}
                    >
                      View
                    </Button>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={() => downloadScript(`launch-${processName}.sh`, generatedScripts.launch_script)}
                    >
                      Download
                    </Button>
                    <Button
                      size="small"
                      startIcon={<CopyIcon />}
                      onClick={() => copyToClipboard(generatedScripts.launch_script)}
                    >
                      Copy
                    </Button>
                  </CardActions>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Kill Script
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Script to stop your application
                    </Typography>
                  </CardContent>
                  <CardActions>
                    <Button
                      size="small"
                      startIcon={<VisibilityIcon />}
                      onClick={() => showScript('Kill Script', generatedScripts.kill_script)}
                    >
                      View
                    </Button>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={() => downloadScript(`kill-${processName}.sh`, generatedScripts.kill_script)}
                    >
                      Download
                    </Button>
                    <Button
                      size="small"
                      startIcon={<CopyIcon />}
                      onClick={() => copyToClipboard(generatedScripts.kill_script)}
                    >
                      Copy
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            </Grid>

            <Accordion sx={{ mt: 3 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>ProcessGuard Configuration</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <pre style={{ fontSize: '12px', overflow: 'auto' }}>
                  {JSON.stringify(generatedScripts.process_config, null, 2)}
                </pre>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Monitoring Configuration</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <pre style={{ fontSize: '12px', overflow: 'auto' }}>
                  {JSON.stringify(generatedScripts.monitoring_config, null, 2)}
                </pre>
              </AccordionDetails>
            </Accordion>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
              <Button onClick={() => setActiveStep(2)}>
                Back
              </Button>
              <Button
                variant="contained"
                onClick={handleDeployProcess}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : <PlayIcon />}
              >
                {loading ? 'Deploying...' : 'Deploy to ProcessGuard'}
              </Button>
            </Box>
          </Box>
        )}
      </Paper>

      {/* Script Dialog */}
      <Dialog
        open={scriptDialog.open}
        onClose={() => setScriptDialog({ open: false, title: '', content: '' })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{scriptDialog.title}</DialogTitle>
        <DialogContent>
          <pre style={{ fontSize: '12px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
            {scriptDialog.content}
          </pre>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => copyToClipboard(scriptDialog.content)}>
            Copy
          </Button>
          <Button onClick={() => setScriptDialog({ open: false, title: '', content: '' })}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Error Snackbar */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError('')}
      >
        <Alert severity="error" onClose={() => setError('')}>
          {error}
        </Alert>
      </Snackbar>

      {/* Success Snackbar */}
      <Snackbar
        open={!!success}
        autoHideDuration={4000}
        onClose={() => setSuccess('')}
      >
        <Alert severity="success" onClose={() => setSuccess('')}>
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default AppWizard;