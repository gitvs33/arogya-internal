import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ToastProvider, useToast } from './Toast';

function TestConsumer({ message, type }: { message: string; type?: 'success' | 'error' | 'info' | 'warning' }) {
  const { addToast, removeToast, toasts } = useToast();
  return (
    <div>
      <button onClick={() => addToast(message, type)}>Add toast</button>
      <button onClick={() => toasts[0] && removeToast(toasts[0].id)}>Remove toast</button>
      <div data-testid="toast-count">{toasts.length}</div>
    </div>
  );
}

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('adds a toast', () => {
    render(
      <ToastProvider>
        <TestConsumer message="Hello" />
      </ToastProvider>
    );

    act(() => { screen.getByText('Add toast').click(); });

    expect(screen.getByTestId('toast-count').textContent).toBe('1');
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('removes a toast on close', () => {
    render(
      <ToastProvider>
        <TestConsumer message="Dismiss me" />
      </ToastProvider>
    );

    act(() => { screen.getByText('Add toast').click(); });
    expect(screen.getByText('Dismiss me')).toBeInTheDocument();

    act(() => { screen.getByText('×').click(); });
    expect(screen.queryByText('Dismiss me')).not.toBeInTheDocument();
  });

  it('auto-dismisses after 5 seconds', () => {
    render(
      <ToastProvider>
        <TestConsumer message="Auto" />
      </ToastProvider>
    );

    act(() => { screen.getByText('Add toast').click(); });
    expect(screen.getByText('Auto')).toBeInTheDocument();

    // Advance past the 5s timeout
    act(() => { vi.advanceTimersByTime(5000); });
    expect(screen.queryByText('Auto')).not.toBeInTheDocument();
  });

  it('allows multiple toasts', () => {
    render(
      <ToastProvider>
        <TestConsumer message="First" />
        <TestConsumer message="Second" />
      </ToastProvider>
    );

    // Add two toasts via the first consumer
    act(() => { screen.getAllByText('Add toast')[0].click(); });
    act(() => { screen.getAllByText('Add toast')[0].click(); });

    // Check count (use the first consumer's count)
    const counts = screen.getAllByTestId('toast-count');
    // The ToastProvider is global, so both consumers see the same toasts
    expect(counts[0].textContent).toBe('2');
  });
});
