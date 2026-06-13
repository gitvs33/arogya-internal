// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, waitFor } from '../test/test-utils';
import { Route, Routes } from 'react-router-dom';

const mockHospital = {
  id: 'h1',
  name: 'City Care Hospital',
  slug: 'city-care',
  plan: 'enterprise',
  is_active: true,
  address: '123 Main St',
  phone: '+1 555-0100',
  email: 'info@citycare.com',
  created_at: '2024-01-15T00:00:00Z',
  stats: { patients: 1200, encounters_30d: 340, invoices: 890 },
  admin: {
    first_name: 'John',
    last_name: 'Smith',
    email: 'admin@citycare.com',
    last_login: '2026-06-10T12:00:00Z',
  },
  staff_breakdown: {
    total: 45,
    by_role: { Admin: 2, Doctor: 15, Nurse: 20, Technician: 8 },
  },
};

vi.mock('../api/internalApi', () => ({
  internalApi: {
    getHospital: vi.fn(),
    activateHospital: vi.fn(),
    deactivateHospital: vi.fn(),
    impersonateHospital: vi.fn(),
  },
}));

import HospitalDetail from './HospitalDetail';

async function mockApi() {
  return (await import('../api/internalApi')).internalApi;
}

function renderWithRoute(entries = ['/hospitals/h1']) {
  return renderWithProviders(
    <Routes>
      <Route path="hospitals/:id" element={<HospitalDetail />} />
    </Routes>,
    { initialEntries: entries }
  );
}

describe('HospitalDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while fetching', () => {
    renderWithRoute();
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders hospital details when data loads', async () => {
    (await mockApi()).getHospital.mockReturnValue(Promise.resolve({ data: mockHospital }));

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('City Care Hospital')).toBeTruthy();
    });

    expect(screen.getByText('city-care')).toBeTruthy();
    expect(screen.getByText('Active')).toBeTruthy();
    expect(screen.getByText('enterprise')).toBeTruthy();
    expect(screen.getByText('1200')).toBeTruthy();
    expect(screen.getByText('340')).toBeTruthy();
    expect(screen.getByText('890')).toBeTruthy();
    expect(screen.getByText(/John/)).toBeTruthy();
    expect(screen.getByText('admin@citycare.com')).toBeTruthy();
    expect(screen.getByText('Staff')).toBeTruthy();
    expect(screen.getByText('Doctor')).toBeTruthy();
    expect(screen.getByText('Nurse')).toBeTruthy();
    expect(screen.getByText('Technician')).toBeTruthy();
  });

  it('shows deactivate button for active hospital', async () => {
    (await mockApi()).getHospital.mockReturnValue(Promise.resolve({ data: mockHospital }));

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Deactivate')).toBeTruthy();
    });
  });

  it('shows activate button for inactive hospital', async () => {
    (await mockApi()).getHospital.mockReturnValue(Promise.resolve({
      data: { ...mockHospital, is_active: false },
    }));

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Activate')).toBeTruthy();
    });
  });

  it('renders "not found" when hospital is null', async () => {
    (await mockApi()).getHospital.mockReturnValue(Promise.resolve({ data: null }));

    renderWithRoute(['/hospitals/unknown']);

    await waitFor(() => {
      expect(screen.getByText('Hospital not found.')).toBeTruthy();
    });
  });
});

export {};
