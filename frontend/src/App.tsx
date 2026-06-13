import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { getStoredUser, setToastHook } from './api/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider, useToast } from './components/Toast';
import Layout from './components/Layout';
import Login from './pages/Login';

const HospitalsDashboard = lazy(() => import('./pages/HospitalsDashboard'));
const HospitalDetail = lazy(() => import('./pages/HospitalDetail'));
const NewHospitalWizard = lazy(() => import('./pages/NewHospitalWizard'));
const Stats = lazy(() => import('./pages/Stats'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = getStoredUser();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function ToastInitializer({ children }: { children: React.ReactNode }) {
  const { addToast } = useToast();
  useEffect(() => { setToastHook(addToast); }, [addToast]);
  return <>{children}</>;
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastProvider>
            <ToastInitializer>
              <Suspense fallback={
                <div className="flex items-center justify-center min-h-screen bg-gray-50">
                  <div className="animate-spin w-8 h-8 border-2 border-[#1D4B42] border-t-transparent rounded-full" />
                </div>
              }>
              <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<HospitalsDashboard />} />
            <Route path="hospitals/new" element={<NewHospitalWizard />} />
            <Route path="hospitals/:id" element={<HospitalDetail />} />
            <Route path="dashboard" element={<AdminDashboard />} />
            <Route path="stats" element={<Stats />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
              </Suspense>
            </ToastInitializer>
          </ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
