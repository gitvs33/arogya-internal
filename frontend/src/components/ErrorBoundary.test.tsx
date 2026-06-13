import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

function GoodComponent() {
  return <div>All good</div>;
}

function BadComponent() {
  throw new Error('Kaboom!');
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <GoodComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('All good')).toBeInTheDocument();
  });

  it('renders fallback UI on error', () => {
    // Suppress console.error from React's error logging
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <BadComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Kaboom!')).toBeInTheDocument();
    expect(screen.getByText('Reload page')).toBeInTheDocument();

    spy.mockRestore();
  });

  it('renders custom fallback when provided', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<div>Custom error view</div>}>
        <BadComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error view')).toBeInTheDocument();

    spy.mockRestore();
  });
});
