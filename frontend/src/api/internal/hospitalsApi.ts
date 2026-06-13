import client from '../client';
import type { HospitalListItem, PaginatedResponse } from '../types';

export const hospitalsApi = {
  getHospitals: (page?: number) =>
    client.get<PaginatedResponse<HospitalListItem>>('/internal/hospitals/', {
      params: page ? { page } : undefined,
    }),

  createHospital: (data: {
    name: string;
    slug: string;
    plan: string;
    admin_name: string;
    admin_email: string;
    admin_password: string;
    address?: string;
    phone?: string;
    email?: string;
  }) => client.post('/internal/hospitals/create/', data) as Promise<any>,

  getHospital: (id: string): Promise<any> =>
    client.get(`/internal/hospitals/${id}/`),

  updateHospital: (id: string, data: Record<string, any>): Promise<any> =>
    client.patch(`/internal/hospitals/${id}/update/`, data),

  activateHospital: (id: string): Promise<any> =>
    client.post(`/internal/hospitals/${id}/activate/`),

  deactivateHospital: (id: string): Promise<any> =>
    client.post(`/internal/hospitals/${id}/deactivate/`),

  impersonateHospital: (id: string): Promise<any> =>
    client.post(`/internal/hospitals/${id}/impersonate/`),
};
