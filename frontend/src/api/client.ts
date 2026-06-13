import axios from 'axios';

const STORAGE_KEY = 'medos_ops_user';

const client = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Module-level hook so outside-React code (interceptors) can fire toasts.
 * Set by ``<App>`` on mount via ``setToastHook``.
 */
export let showToast: ((msg: string, type?: 'success' | 'error' | 'info' | 'warning') => void) | null = null;

export function setToastHook(fn: typeof showToast) {
  showToast = fn;
}

client.interceptors.request.use((config) => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    const data = JSON.parse(stored);
    if (data.token) {
      config.headers['Authorization'] = `Token ${data.token}`;
    }
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(STORAGE_KEY);
      // Show a warning before redirecting — gives the user context
      if (showToast) {
        showToast('Your session has expired. Please log in again.', 'warning');
      }
      setTimeout(() => { window.location.href = '/login'; }, 1500);
    } else if (error.response?.status && error.response.status >= 500) {
      if (showToast) {
        showToast(`Server error (${error.response.status}). Please try again later.`, 'error');
      }
    } else if (!error.response && error.message === 'Network Error') {
      if (showToast) {
        showToast('Network error. Check your connection.', 'error');
      }
    }
    return Promise.reject(error);
  }
);

export function getStoredUser() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored ? JSON.parse(stored) : null;
}

export function setStoredUser(data: { token: string; user: any }) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function clearStoredUser() {
  localStorage.removeItem(STORAGE_KEY);
}

export default client;
