// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, screen, waitFor } from '../test/test-utils';
import { internalApi } from '../api/internalApi';
import Login from './Login';

// Mock the entire internalApi module
vi.mock('../api/internalApi', () => ({
  internalApi: {
    login: vi.fn(),
  },
}));

// Mock client.setStoredUser — it touches localStorage
const setStoredUser = vi.fn();
vi.mock('../api/client', () => ({
  setStoredUser: (data: any) => setStoredUser(data),
  getStoredUser: () => null,
  clearStoredUser: () => {},
  default: {},
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders the login form', () => {
    renderWithProviders(<Login />);

    expect(screen.getByText('MedOS Operations')).toBeInTheDocument();
    expect(screen.getByText('Staff login — internal use only')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('your username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('your password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows error message on failed login', async () => {
    const mockError = { response: { data: { error: 'Invalid credentials' } } };
    vi.mocked(internalApi.login).mockRejectedValueOnce(mockError);
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText('your username'), 'baduser');
    await user.type(screen.getByPlaceholderText('your password'), 'badpass');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('navigates to / on successful login', async () => {
    vi.mocked(internalApi.login).mockResolvedValueOnce({} as any);
    renderWithProviders(<Login />);
    const user = userEvent.setup();

    await user.type(screen.getByPlaceholderText('your username'), 'admin');
    await user.type(screen.getByPlaceholderText('your password'), 'secret');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });
});
