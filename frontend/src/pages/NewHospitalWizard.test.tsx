// @ts-nocheck
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithProviders, screen, waitFor, act } from '../test/test-utils';

vi.mock('../api/internalApi', () => ({
  internalApi: {
    createHospital: vi.fn(),
  },
}));

import NewHospitalWizard from './NewHospitalWizard';

async function mockApi() {
  return (await import('../api/internalApi')).internalApi;
}

/** Set native input value and dispatch an input event. */
function setInputValue(input: HTMLElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value',
  )?.set;
  if (setter) {
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
}

describe('NewHospitalWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders step 1 (hospital details) by default', () => {
    renderWithProviders(<NewHospitalWizard />);
    expect(screen.getByText('Hospital Details')).toBeTruthy();
    expect(screen.getByText('Hospital Name *')).toBeTruthy();
    expect(screen.getByText('Slug *')).toBeTruthy();
    expect(screen.getByText('Plan')).toBeTruthy();
    expect(screen.getByText('Next — Admin Account')).toBeTruthy();
  });

  it('disables Next button when name is empty', () => {
    renderWithProviders(<NewHospitalWizard />);
    expect(screen.getByText('Next — Admin Account').closest('button')?.disabled).toBe(true);
  });

  it('enables Next when name is filled (slug auto-generated)', async () => {
    renderWithProviders(<NewHospitalWizard />);
    const nameInput = screen.getByPlaceholderText('e.g. City Care Hospital');

    await act(async () => {
      setInputValue(nameInput, 'Test Hospital');
    });

    expect(screen.getByText('Next — Admin Account').closest('button')?.disabled).toBe(false);
  });

  it('auto-generates slug from name', async () => {
    renderWithProviders(<NewHospitalWizard />);
    const nameInput = screen.getByPlaceholderText('e.g. City Care Hospital');
    const slugInput = screen.getByPlaceholderText('city-care-hospital') as HTMLInputElement;

    await act(async () => {
      setInputValue(nameInput, 'My Test Hospital');
    });

    expect(slugInput.value).toBe('my-test-hospital');
  });

  it('advances to step 2 (admin account) on Next click', async () => {
    renderWithProviders(<NewHospitalWizard />);
    const nameInput = screen.getByPlaceholderText('e.g. City Care Hospital');

    await act(async () => setInputValue(nameInput, 'Test Hospital'));
    await act(async () => { screen.getByText('Next — Admin Account').click(); });

    expect(screen.getByText('Admin Account')).toBeTruthy();
    expect(screen.getByPlaceholderText('John Smith')).toBeTruthy();
    expect(screen.getByPlaceholderText('admin@citycare.com')).toBeTruthy();
    expect(screen.getByText(/Create Hospital/)).toBeTruthy();
  });

  it('calls createHospital on form submit', async () => {
    const api = await mockApi();
    (api.createHospital as any).mockResolvedValue({} as any);

    renderWithProviders(<NewHospitalWizard />);
    const nameInput = screen.getByPlaceholderText('e.g. City Care Hospital');

    // Step 1
    await act(async () => setInputValue(nameInput, 'Test Hospital'));
    await act(async () => { screen.getByText('Next — Admin Account').click(); });

    // Step 2
    await act(async () => setInputValue(screen.getByPlaceholderText('John Smith'), 'Dr Admin'));
    await act(async () => setInputValue(screen.getByPlaceholderText('admin@citycare.com'), 'admin@test.com'));
    await act(async () => setInputValue(screen.getByPlaceholderText('At least 8 characters'), 'password123'));

    await act(async () => { screen.getByText('Create Hospital & Send Credentials').click(); });

    await waitFor(() => {
      expect((api.createHospital as any)).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test Hospital',
          admin_name: 'Dr Admin',
          admin_email: 'admin@test.com',
          admin_password: 'password123',
        })
      );
    });
  });

  it('shows error message on API failure', async () => {
    const api = await mockApi();
    (api.createHospital as any).mockRejectedValue({
      response: { data: { error: 'Slug already taken' } },
    });

    renderWithProviders(<NewHospitalWizard />);
    const nameInput = screen.getByPlaceholderText('e.g. City Care Hospital');

    await act(async () => setInputValue(nameInput, 'Test'));
    await act(async () => { screen.getByText('Next — Admin Account').click(); });

    await act(async () => setInputValue(screen.getByPlaceholderText('John Smith'), 'Admin'));
    await act(async () => setInputValue(screen.getByPlaceholderText('admin@citycare.com'), 'a@b.com'));
    await act(async () => setInputValue(screen.getByPlaceholderText('At least 8 characters'), 'pass1234'));

    await act(async () => { screen.getByText('Create Hospital & Send Credentials').click(); });

    await waitFor(() => expect(screen.getByText('Slug already taken')).toBeTruthy());
  });

  it('shows loading state while submitting', async () => {
    const api = await mockApi();
    (api.createHospital as any).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<NewHospitalWizard />);
    const nameInput = screen.getByPlaceholderText('e.g. City Care Hospital');

    await act(async () => setInputValue(nameInput, 'Test'));
    await act(async () => { screen.getByText('Next — Admin Account').click(); });

    await act(async () => setInputValue(screen.getByPlaceholderText('John Smith'), 'Admin'));
    await act(async () => setInputValue(screen.getByPlaceholderText('admin@citycare.com'), 'a@b.com'));
    await act(async () => setInputValue(screen.getByPlaceholderText('At least 8 characters'), 'pass1234'));

    await act(async () => { screen.getByText('Create Hospital & Send Credentials').click(); });

    expect(screen.getByText('Creating...')).toBeTruthy();
  });
});
