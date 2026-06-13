import client from '../client';


export const dashboardApi = {
  // Stats
  getStats: (): Promise<any> =>
    client.get('/internal/stats/'),

  // Dashboard composite endpoints
  getDashboardOverview: (): Promise<any> =>
    client.get('/internal/admin/dashboard/overview/'),

  getDashboardActivity: (): Promise<any> =>
    client.get('/internal/admin/dashboard/activity/'),

  getDashboardAlerts: (): Promise<any> =>
    client.get('/internal/admin/dashboard/alerts/'),
};
