// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, waitFor, act } from '../test/test-utils';

// Mock data
const mockOverview = {
  kpis: {
    total_users: { count: 150, growth: '+5 this month' },
    active_users: { count: 98, percentage: 65 },
    departments: { count: 12, growth: '+1' },
    roles: { count: 8, growth: '' },
    system_uptime: { count: '99.9%', growth: '' },
    storage_used: { percentage: 42, used: '2.1 GB', total: '5 GB' },
  },
  module_status: [
    { name: 'core', label: 'Core', status: 'Operational', is_critical: true },
    { name: 'billing', label: 'Billing', status: 'Operational', is_critical: true },
  ],
  database_storage: {
    storage_used_gb: 2.1,
    storage_total_gb: 5.0,
    database_status: 'Healthy',
    last_backup: '2026-06-10T00:00:00Z',
  },
  system_info: {
    python_version: '3.14',
    django_version: '5.2',
    server_time: '2026-06-11T20:00:00Z',
  },
  security_overview: { encryption: 'AES-256', audits: true },
};

const mockActivity = {
  system_overview_chart: [
    { date: '2026-06-05', logins: 42, transactions: 310, errors: 2 },
    { date: '2026-06-06', logins: 38, transactions: 290, errors: 1 },
  ],
  user_activity: [
    { username: 'admin', email: 'admin@medos.com', role: 'Admin', login_count: 15, last_active: '2026-06-10T12:00:00Z' },
  ],
  audit_summary: {
    total_logs: 1240,
    by_category: [
      { category: 'User Actions', count: 600 },
      { category: 'System', count: 400 },
    ],
    recent: [
      { id: '1', description: 'User logged in', author_name: 'admin', created_at: '2026-06-10T12:00:00Z' },
    ],
  },
};

const mockAlerts = {
  system_alerts: [
    { id: 'a1', title: 'High CPU', description: 'CPU > 90%', severity: 'warning', is_resolved: false, created_at: '2026-06-11T10:00:00Z' },
    { id: 'a2', title: 'Disk space', description: 'Low disk', severity: 'critical', is_resolved: true, created_at: '2026-06-10T08:00:00Z' },
  ],
  recent_activities: [
    { id: 'r1', description: 'New hospital onboarded', author_name: 'ops', hospital_name: 'City Care', created_at: '2026-06-11T14:00:00Z' },
  ],
};

// vi.mock is hoisted — factory stays inline
vi.mock('../api/internalApi', () => ({
  internalApi: {
    getDashboardOverview: vi.fn(),
    getDashboardActivity: vi.fn(),
    getDashboardAlerts: vi.fn(),
  },
}));

import AdminDashboard from './AdminDashboard';

// Helper to get the mocked module inside an async test
async function mockApi() {
  return (await import('../api/internalApi')).internalApi;
}

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    // Don't resolve — component stays loading
    renderWithProviders(<AdminDashboard />);
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders Overview tab by default with data', async () => {
    const api = await mockApi();
    (api.getDashboardOverview as any).mockResolvedValue({ data: mockOverview });
    (api.getDashboardActivity as any).mockResolvedValue({ data: mockActivity });
    (api.getDashboardAlerts as any).mockResolvedValue({ data: mockAlerts });

    renderWithProviders(<AdminDashboard />);

    await waitFor(() => expect(screen.getByText('Admin Dashboard')).toBeTruthy());
    expect(screen.getByText('Total Users')).toBeTruthy();
    expect(screen.getByText('150')).toBeTruthy();
    expect(screen.getByText('Module Status')).toBeTruthy();
    expect(screen.getByText('Core')).toBeTruthy();
    expect(screen.getByText('Database Storage')).toBeTruthy();
    expect(screen.getByText('System')).toBeTruthy();
  });

  it('switches to Activity tab', async () => {
    const api = await mockApi();
    (api.getDashboardOverview as any).mockResolvedValue({ data: mockOverview });
    (api.getDashboardActivity as any).mockResolvedValue({ data: mockActivity });
    (api.getDashboardAlerts as any).mockResolvedValue({ data: mockAlerts });

    renderWithProviders(<AdminDashboard />);

    await waitFor(() => expect(screen.getByText('Admin Dashboard')).toBeTruthy());

    await act(async () => { screen.getByText('Activity').click(); });

    expect(screen.getByText('Login Activity (7 days)')).toBeTruthy();
    expect(screen.getByText('Top Active Users (30 days)')).toBeTruthy();
    expect(screen.getByText((content) => content.startsWith('Audit Summary'))).toBeTruthy();
  });

  it('switches to Alerts tab', async () => {
    const api = await mockApi();
    (api.getDashboardOverview as any).mockResolvedValue({ data: mockOverview });
    (api.getDashboardActivity as any).mockResolvedValue({ data: mockActivity });
    (api.getDashboardAlerts as any).mockResolvedValue({ data: mockAlerts });

    renderWithProviders(<AdminDashboard />);

    await waitFor(() => expect(screen.getByText('Admin Dashboard')).toBeTruthy());

    await act(async () => { screen.getByText('Alerts').click(); });

    expect(screen.getByText('System Alerts')).toBeTruthy();
    expect(screen.getByText('High CPU')).toBeTruthy();
    expect(screen.getByText('Recent Activities')).toBeTruthy();
    expect(screen.getByText(/City Care/)).toBeTruthy();
  });

  it('shows error state when queries fail', async () => {
    const api = await mockApi();
    (api.getDashboardOverview as any).mockRejectedValue(new Error('fail'));
    (api.getDashboardActivity as any).mockRejectedValue(new Error('fail'));
    (api.getDashboardAlerts as any).mockRejectedValue(new Error('fail'));

    renderWithProviders(<AdminDashboard />);

    await waitFor(() => expect(screen.getByText('Failed to load dashboard')).toBeTruthy());
  });

  it('shows unresolved alert count on Alerts tab', async () => {
    const api = await mockApi();
    (api.getDashboardOverview as any).mockResolvedValue({ data: mockOverview });
    (api.getDashboardActivity as any).mockResolvedValue({ data: mockActivity });
    (api.getDashboardAlerts as any).mockResolvedValue({ data: mockAlerts });

    renderWithProviders(<AdminDashboard />);

    await waitFor(() => expect(screen.getByText('Admin Dashboard')).toBeTruthy());

    await act(async () => { screen.getByText('Alerts').click(); });

    expect(screen.getByText('1 unresolved')).toBeTruthy();
  });
});

export {};
