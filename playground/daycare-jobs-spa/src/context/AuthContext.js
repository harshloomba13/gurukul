import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext();
const AUTH_TOKEN_KEY = 'carelink-token';
const AUTH_USER_KEY = 'carelink-user';
const API_BASE = process.env.REACT_APP_API_BASE || '';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);

  // Analytics tracking function (ready for future implementation)
  const trackEvent = (eventName, data = {}, currentUser = user) => {
    // Store events in localStorage for now (can be sent to analytics service later)
    const events = JSON.parse(localStorage.getItem('carelink-analytics') || '[]');
    events.push({
      event: eventName,
      timestamp: new Date().toISOString(),
      user: currentUser ? { role: currentUser.role, hasEmail: !!currentUser.email } : null,
      data,
    });
    localStorage.setItem('carelink-analytics', JSON.stringify(events.slice(-1000))); // Keep last 1000 events
  };

  useEffect(() => {
    // Check for stored auth on mount
    const storedUser = localStorage.getItem(AUTH_USER_KEY);
    const token = localStorage.getItem(AUTH_TOKEN_KEY);

    if (storedUser) {
      try {
        const authData = JSON.parse(storedUser);
        setUser(authData);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Error parsing stored auth:', error);
        localStorage.removeItem(AUTH_USER_KEY);
      }
    }

    if (token) {
      verifySession(token);
    }
  }, []);

  const persistAuth = (authPayload) => {
    setUser(authPayload.user);
    setIsAuthenticated(true);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(authPayload.user));
    localStorage.setItem(AUTH_TOKEN_KEY, authPayload.token);
  };

  const clearAuth = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem(AUTH_TOKEN_KEY);
  };

  const requestJson = async (url, options = {}) => {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || 'Request failed');
    }
    return data;
  };

  const verifySession = async (token) => {
    try {
      const data = await requestJson('/api/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUser(data.user);
      setIsAuthenticated(true);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(data.user));
    } catch (error) {
      clearAuth();
    }
  };

  const login = async (email, password) => {
    setAuthLoading(true);
    try {
      const data = await requestJson('/api/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      persistAuth(data);
      trackEvent('login', { role: data.user.role, hasEmail: !!data.user.email }, data.user);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: error.message };
    } finally {
      setAuthLoading(false);
    }
  };

  const signup = async (name, email, password, role = 'Teacher') => {
    setAuthLoading(true);
    try {
      const data = await requestJson('/api/signup', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role }),
      });
      persistAuth(data);
      trackEvent('signup', { role, hasEmail: !!email }, data.user);
      return { ok: true };
    } catch (error) {
      return { ok: false, error: error.message };
    } finally {
      setAuthLoading(false);
    }
  };

  const loginAsGuest = () => {
    const userData = {
      name: 'Guest',
      email: '',
      role: 'Guest',
      loginTime: new Date().toISOString(),
    };
    setUser(userData);
    setIsAuthenticated(true);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(userData));
    localStorage.removeItem(AUTH_TOKEN_KEY);
    
    // Track guest login event
    trackEvent('guest_login', {}, userData);
  };

  const logout = () => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      fetch(`${API_BASE}/api/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }
    trackEvent('logout', { role: user?.role });
    clearAuth();
  };

  const value = {
    user,
    isAuthenticated,
    authLoading,
    login,
    signup,
    loginAsGuest,
    logout,
    trackEvent,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
