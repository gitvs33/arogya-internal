import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { RenderOptions } from '@testing-library/react';
import { ToastProvider } from '../components/Toast';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });
}

interface WrapperOptions {
  initialEntries?: string[];
}

export function renderWithProviders(
  ui: ReactNode,
  options?: WrapperOptions & Omit<RenderOptions, 'wrapper'>,
) {
  const { initialEntries = ['/'], ...renderOptions } = options ?? {};
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <ToastProvider>
            {children}
          </ToastProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }), queryClient };
}

export { screen, waitFor, act } from '@testing-library/react';
