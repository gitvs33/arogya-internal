import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen } from '../test/test-utils';
import Layout from './Layout';

// Mock the client module
vi.mock('../api/client', () => ({
  getStoredUser: vi.fn(),
  clearStoredUser: vi.fn(),
  storeUser: vi.fn(),
}));

import * as client from '../api/client';

describe('Layout', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders nav links', () => {
    vi.mocked(client.getStoredUser).mockReturnValue(null);

    renderWithProviders(<Layout />);

    expect(screen.getByText('Hospitals')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Platform Stats')).toBeInTheDocument();
  });

  it('highlights active nav link', () => {
    vi.mocked(client.getStoredUser).mockReturnValue(null);

    renderWithProviders(<Layout />, { initialEntries: ['/dashboard'] });

    const dashboardLink = screen.getByText('Dashboard');
    expect(dashboardLink.className).toContain('font-medium');
  });

  it('shows username when logged in', () => {
    vi.mocked(client.getStoredUser).mockReturnValue({
      user: { username: 'admin', email: 'admin@test.com' },
    });

    renderWithProviders(<Layout />);

    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('admin@test.com')).toBeInTheDocument();
  });

  it('shows sign out button', () => {
    vi.mocked(client.getStoredUser).mockReturnValue(null);

    renderWithProviders(<Layout />);

    expect(screen.getByText('Sign out')).toBeInTheDocument();
  });
});
