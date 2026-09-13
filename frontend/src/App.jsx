import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { AppLayout } from './components/layout/AppLayout';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SimulatorPage from './pages/SimulatorPage';
import AssessmentResultPage from './pages/AssessmentResultPage';
import TransactionsPage from './pages/TransactionsPage';
import TransactionDetailPage from './pages/TransactionDetailPage';
import AlertsPage from './pages/AlertsPage';
import DevicesPage from './pages/DevicesPage';
import AuditLogsPage from './pages/AuditLogsPage';
import UsersPage from './pages/UsersPage';

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-slate-400 text-sm">
        Initializing A.R.G.U.S. Security Gateway...
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'USER') {
    return <Navigate to="/simulator" replace />;
  }
  return <Navigate to="/dashboard" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Authentication Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Application Shell */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            {/* Root Intelligent Redirection */}
            <Route path="/" element={<RootRedirect />} />

            {/* Analyst & Operations Dashboard */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN', 'AUDITOR']}>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />

            {/* PaySim Simulator & Inference Result */}
            <Route
              path="/simulator"
              element={
                <ProtectedRoute allowedRoles={['USER', 'ANALYST', 'ADMIN']}>
                  <SimulatorPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/simulator/result/:id"
              element={
                <ProtectedRoute allowedRoles={['USER', 'ANALYST', 'ADMIN', 'AUDITOR']}>
                  <AssessmentResultPage />
                </ProtectedRoute>
              }
            />

            {/* Transaction Ledger & Forensic Inspector */}
            <Route
              path="/transactions"
              element={
                <ProtectedRoute allowedRoles={['USER', 'ANALYST', 'ADMIN', 'AUDITOR']}>
                  <TransactionsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/transactions/:id"
              element={
                <ProtectedRoute allowedRoles={['USER', 'ANALYST', 'ADMIN', 'AUDITOR']}>
                  <TransactionDetailPage />
                </ProtectedRoute>
              }
            />

            {/* Fraud Review Queue */}
            <Route
              path="/alerts"
              element={
                <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN', 'AUDITOR']}>
                  <AlertsPage />
                </ProtectedRoute>
              }
            />

            {/* IoT Edge Terminal Fleet */}
            <Route
              path="/devices"
              element={
                <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN', 'AUDITOR']}>
                  <DevicesPage />
                </ProtectedRoute>
              }
            />

            {/* Security Audit Explorer */}
            <Route
              path="/admin/audit"
              element={
                <ProtectedRoute allowedRoles={['ADMIN', 'AUDITOR']}>
                  <AuditLogsPage />
                </ProtectedRoute>
              }
            />

            {/* User Access & Roles */}
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute allowedRoles={['ADMIN']}>
                  <UsersPage />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Catch-all fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
