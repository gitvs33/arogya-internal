// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, waitFor } from '../test/test-utils';
import { internalApi } from '../api/internalApi';
import Stats from './Stats';

vi.mock('../api/internalApi', () => ({
  internalApi: {
    getStats: vi.fn(),
  },
}));

vi.mock('../api/client', () => ({
  default: {},
}));

const mockData = {
  total_hospitals: 5,
  active_hospitals: 4,
  total_staff: 120,
  total_patients: 3500,
  total_encounters: 8900,
  total_invoices: 2100,
  patients_30d: 180,
  onboarding_30d: 1,
};

const healthData = {
  total_hospitals: 10,
  active_hospitals: 7,
  total_staff: 200,
  total_patients: 5000,
  total_encounters: 12000,
  total_invoices: 3000,
  patients_30d: 500,
  onboarding_30d: 2,
};

const zeroData = {
  total_hospitals: 0,
  active_hospitals: 0,
  total_staff: 0,
  total_patients: 0,
  total_encounters: 0,
  total_invoices: 0,
  patients_30d: 0,
  onboarding_30d: 0,
};

describe('Stats', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('shows loading state initially', () => {
    vi.mocked(internalApi.getStats).mockReturnValueOnce(new Promise(() => {}));

    renderWithProviders(<Stats />);

    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByText('Platform Statistics')).not.toBeInTheDocument();
  });

  it('renders stat cards when data loads', async () => {
    vi.mocked(internalApi.getStats).mockResolvedValueOnce({ data: mockData });

    renderWithProviders(<Stats />);

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Hospitals')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Active Hospitals')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('Total Staff')).toBeInTheDocument();
    expect(screen.getByText('3500')).toBeInTheDocument();
    expect(screen.getByText('Total Patients')).toBeInTheDocument();
    expect(screen.getByText('8900')).toBeInTheDocument();
    expect(screen.getByText('2100')).toBeInTheDocument();
  });

  it('shows growth section with correct numbers', async () => {
    vi.mocked(internalApi.getStats).mockResolvedValueOnce({ data: mockData });

    renderWithProviders(<Stats />);

    await waitFor(() => {
      expect(screen.getByText('180')).toBeInTheDocument();
    });

    expect(screen.getByText('New Patients')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('New Hospitals')).toBeInTheDocument();
  });

  it('shows health percentage correctly', async () => {
    vi.mocked(internalApi.getStats).mockResolvedValueOnce({ data: healthData });

    renderWithProviders(<Stats />);

    await waitFor(() => {
      expect(screen.getByText(/7 of 10 hospitals active/)).toBeInTheDocument();
    });

    expect(screen.getByText((content) => content.includes('70%'))).toBeInTheDocument();
  });

  it('handles zero hospitals without crash', async () => {
    vi.mocked(internalApi.getStats).mockResolvedValueOnce({ data: zeroData });

    renderWithProviders(<Stats />);

    await waitFor(() => {
      expect(screen.getByText('Platform Statistics')).toBeInTheDocument();
    });

    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(6);

    expect(screen.getByText((content) => content.includes('0%'))).toBeInTheDocument();
  });
});

export {};
