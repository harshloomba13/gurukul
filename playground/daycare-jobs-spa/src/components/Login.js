import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

function Login() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('Teacher');
  const [error, setError] = useState('');
  const { login, loginAsGuest } = useAuth();
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    setError('');

    if (!name.trim() && !email.trim()) {
      setError('Please enter a name or email to continue.');
      return;
    }

    login(name.trim(), email.trim(), role);
    navigate('/dashboard');
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
            search. Everything runs client-side so you can prototype analytics
            and monetization later without backend changes.
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
          <form onSubmit={handleLogin}>
            <label>
              Name
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Teacher name"
              />
            </label>
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
              Access type
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="Teacher">Teacher</option>
                <option value="Guest">Guest</option>
              </select>
            </label>
            {error && <div className="error-message">{error}</div>}
            <div className="login-actions">
              <button type="submit" className="btn btn-primary">
                Sign in
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleGuestLogin}
              >
                Continue as guest
              </button>
            </div>
          </form>
          <div className="status">
            <div className="dot"></div>
            Client-side auth only. No data leaves the browser.
          </div>
        </div>
      </section>
    </div>
  );
}

export default Login;

