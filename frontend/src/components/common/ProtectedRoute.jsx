import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--text-secondary)' }}>
        Loading A.R.G.U.S. Security Context...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = user.role?.toUpperCase() || 'USER';
    if (!allowedRoles.includes(userRole)) {
      return (
        <div style={{ padding: '3rem', textAlign: 'center' }}>
          <div className="alert-banner alert-banner-danger" style={{ maxWidth: '600px', margin: '0 auto' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem' }}>403 Forbidden: Insufficient Permissions</div>
              <div style={{ marginTop: '0.25rem', fontSize: '0.85rem' }}>
                Your operational role (<strong>{userRole}</strong>) is not authorized to access this resource.
              </div>
            </div>
          </div>
        </div>
      );
    }
  }

  return children;
}
