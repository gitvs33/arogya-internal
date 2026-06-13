export * from './types';
import { authApi } from './internal/authApi';
import { hospitalsApi } from './internal/hospitalsApi';
import { dashboardApi } from './internal/dashboardApi';

export const internalApi = {
  ...authApi,
  ...hospitalsApi,
  ...dashboardApi,
};
