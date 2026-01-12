import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

function Login() {
  const [mode, setMode] = useState('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('Teacher');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, signup, loginAsGuest, authLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password) {
      setError('Email and password are required.');
      return;
    }

    if (mode === 'signup' && !name.trim()) {
      setError('Name is required to create an account.');
      return;
    }

    const result =
      mode === 'signup'
        ? await signup(name.trim(), email.trim(), password, role)
        : await login(email.trim(), password);

    if (result.ok) {
      navigate('/dashboard');
      return;
    }

    setError(result.error || 'Unable to sign in.');
  };

  const handleGuestLogin = () => {
    loginAsGuest();
    navigate('/dashboard');
  };

  return (
    <div className="page">
      <header className="header">
        <div className="brand">
          <div className="pill">
            <span>CareLink</span> Daycare Jobs Hub
          </div>
          <h1>Vancouver Metro Daycare Roles</h1>
          <p>
            A focused hiring dashboard for teachers looking across Vancouver,
            Surrey, Langley, Abbotsford, Chilliwack, and nearby areas.
          </p>
        </div>
      </header>

      <section className="hero">
        <div className="panel hero-content">
          <h2>Find your next classroom in minutes.</h2>
          <p>
            Browse pre-loaded openings by region, then refine with instant
            search. Sign in with a secure server-backed account to unlock a
            personalized job dashboard.
          </p>
          <div className="stat-grid">
            <div className="stat">
              <strong>50+</strong>
              <span>Open roles</span>
            </div>
            <div className="stat">
              <strong>6+</strong>
              <span>Featured regions</span>
            </div>
            <div className="stat">
              <strong>Same-day</strong>
              <span>Response goal</span>
            </div>
          </div>
        </div>

        <div className="panel login-card">
          <h3>Quick access</h3>
          <div className="auth-toggle">
            <button
              type="button"
              className={`toggle-btn ${mode === 'login' ? 'active' : ''}`}
              onClick={() => {
                setMode('login');
                setError('');
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              className={`toggle-btn ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => {
                setMode('signup');
                setError('');
              }}
            >
              Create account
            </button>
          </div>
          <form onSubmit={handleLogin}>
            {mode === 'signup' && (
              <label>
                Name
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Teacher name"
                />
              </label>
            )}
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teacher@email.com"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
              />
            </label>
            {mode === 'signup' && (
              <label>
                Access type
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="Teacher">Teacher</option>
                  <option value="Guest">Guest</option>
                </select>
              </label>
            )}
            {error && <div className="error-message">{error}</div>}
            <div className="login-actions">
              <button type="submit" className="btn btn-primary" disabled={authLoading}>
                {authLoading ? 'Working...' : mode === 'signup' ? 'Create account' : 'Sign in'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleGuestLogin}
                disabled={authLoading}
              >
                Continue as guest
              </button>
            </div>
          </form>
          <div className="status">
            <div className="dot"></div>
            Server-side auth with SQLite storage.
          </div>
        </div>
      </section>
    </div>
  );
}

export default Login;
