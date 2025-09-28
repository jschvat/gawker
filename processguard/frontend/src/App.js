import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, AppBar, Toolbar, Typography, Container } from '@mui/material';

import Dashboard from './components/Dashboard';
import ProcessList from './components/ProcessList';
import ProcessDetails from './components/ProcessDetails';
import SystemMetrics from './components/SystemMetrics';
import Alerts from './components/Alerts';
import Logs from './components/Logs';
import AppWizard from './components/AppWizard';
import Navigation from './components/Navigation';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex' }}>
          <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
            <Toolbar>
              <Typography variant="h6" noWrap component="div">
                ProcessGuard
              </Typography>
            </Toolbar>
          </AppBar>

          <Navigation />

          <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
            <Toolbar />
            <Container maxWidth="xl">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/processes" element={<ProcessList />} />
                <Route path="/processes/:processName" element={<ProcessDetails />} />
                <Route path="/wizard" element={<AppWizard />} />
                <Route path="/system" element={<SystemMetrics />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/logs" element={<Logs />} />
              </Routes>
            </Container>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;