import React, { createContext, useState, useContext, useEffect } from 'react';

const AuthContext = createContext();

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
    const storedAuth = localStorage.getItem('carelink-auth');
    if (storedAuth) {
      try {
        const authData = JSON.parse(storedAuth);
        setUser(authData);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Error parsing stored auth:', error);
        localStorage.removeItem('carelink-auth');
      }
    }
  }, []);

  const login = (name, email, role = 'Teacher') => {
    const userData = {
      name: name || 'Teacher',
      email: email || '',
      role: role,
      loginTime: new Date().toISOString(),
    };
    setUser(userData);
    setIsAuthenticated(true);
    localStorage.setItem('carelink-auth', JSON.stringify(userData));
    
    // Track login event (for future analytics)
    trackEvent('login', { role, hasEmail: !!email }, userData);
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
    localStorage.setItem('carelink-auth', JSON.stringify(userData));
    
    // Track guest login event
    trackEvent('guest_login', {}, userData);
  };

  const logout = () => {
    trackEvent('logout', { role: user?.role });
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('carelink-auth');
  };

  const value = {
    user,
    isAuthenticated,
    login,
    loginAsGuest,
    logout,
    trackEvent,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

