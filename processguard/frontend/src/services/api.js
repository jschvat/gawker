import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const processApi = {
  getAll: () => api.get('/processes'),
  get: (name) => api.get(`/processes/${name}`),
  create: (config) => api.post('/processes', config),
  start: (name) => api.post(`/processes/${name}/start`),
  stop: (name, force = false) => api.post(`/processes/${name}/stop`, null, { params: { force } }),
  restart: (name) => api.post(`/processes/${name}/restart`),
  delete: (name) => api.delete(`/processes/${name}`),
  getLogs: (name, lines = 100) => api.get(`/processes/${name}/logs/recent`, { params: { lines } }),
  getLogFiles: (name) => api.get(`/processes/${name}/logs`),
};

export const systemApi = {
  getInfo: () => api.get('/system/info'),
  getMetrics: () => api.get('/system/metrics'),
};

export const alertApi = {
  getAll: (activeOnly = true) => api.get('/alerts', { params: { active_only: activeOnly } }),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge`),
  resolve: (id) => api.post(`/alerts/${id}/resolve`),
};

export const wizardApi = {
  analyzeProject: (projectPath) => api.post('/wizard/analyze', { project_path: projectPath }),
  generateScripts: (config) => api.post('/wizard/generate-scripts', config),
  getSupportedTypes: () => api.get('/wizard/supported-types'),
};

export const createWebSocket = () => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws/metrics`;
  return new WebSocket(wsUrl);
};

export default api;