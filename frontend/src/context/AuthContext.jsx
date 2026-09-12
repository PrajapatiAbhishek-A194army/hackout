import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginUser, signupUser, fetchCurrentUserProfile } from '../services/api';

const AuthContext = createContext(null);

const STORAGE_TOKEN_KEY = 'renewable_ai_jwt_token';
const STORAGE_USER_KEY = 'renewable_ai_user_info';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_TOKEN_KEY) || null);
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Validate or hydrate existing session
    const initAuth = async () => {
      const storedToken = localStorage.getItem(STORAGE_TOKEN_KEY);
      if (storedToken) {
        try {
          const profile = await fetchCurrentUserProfile(storedToken);
          setUser(prev => ({ ...prev, ...profile }));
          localStorage.setItem(STORAGE_USER_KEY, JSON.stringify({ ...user, ...profile }));
        } catch (err) {
          console.warn('Session verification fallback (offline or expired):', err.message);
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    const data = await loginUser({ email, password });
    const userPayload = {
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      role: data.role,
      organization: data.organization || ''
    };
    setToken(data.access_token);
    setUser(userPayload);
    localStorage.setItem(STORAGE_TOKEN_KEY, data.access_token);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(userPayload));
    return userPayload;
  };

  const signup = async ({ email, password, full_name, role, organization }) => {
    const data = await signupUser({ email, password, full_name, role, organization });
    const userPayload = {
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      role: data.role,
      organization: data.organization || ''
    };
    setToken(data.access_token);
    setUser(userPayload);
    localStorage.setItem(STORAGE_TOKEN_KEY, data.access_token);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(userPayload));
    return userPayload;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
  };

  // Helper for judges / presenters to quickly experience other role views while keeping profile active
  const setTemporaryRole = (newRole) => {
    if (user) {
      const updated = { ...user, role: newRole };
      setUser(updated);
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(updated));
    }
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        role: user?.role || null,
        isAuthenticated: !!token && !!user,
        loading,
        login,
        signup,
        logout,
        setTemporaryRole
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

export default AuthContext;
