import React, { createContext, useContext, useState, useEffect } from 'react';
import { login as apiLogin, register as apiRegister, getMe } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('argus_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('argus_token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function initAuth() {
      const storedToken = localStorage.getItem('argus_token');
      if (storedToken) {
        try {
          const profile = await getMe();
          setUser(profile);
          localStorage.setItem('argus_user', JSON.stringify(profile));
        } catch (err) {
          // Token invalid or expired
          localStorage.removeItem('argus_token');
          localStorage.removeItem('argus_user');
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    }

    initAuth();

    const handleUnauthorized = () => {
      setUser(null);
      setToken(null);
      localStorage.removeItem('argus_token');
      localStorage.removeItem('argus_user');
    };

    window.addEventListener('argus:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('argus:unauthorized', handleUnauthorized);
  }, []);

  const login = async (username, password) => {
    const data = await apiLogin(username, password);
    localStorage.setItem('argus_token', data.access_token);
    setToken(data.access_token);
    const profile = await getMe();
    setUser(profile);
    localStorage.setItem('argus_user', JSON.stringify(profile));
    return profile;
  };

  const register = async (userData) => {
    const user = await apiRegister(userData);
    return user;
  };

  const logout = () => {
    localStorage.removeItem('argus_token');
    localStorage.removeItem('argus_user');
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
