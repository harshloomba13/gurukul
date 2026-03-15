const express = require('express');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const PORT = process.env.PORT || 4000;
const DB_PATH =
  process.env.SQLITE_DB_PATH || path.join(__dirname, 'data', 'auth.db');
const SESSION_DAYS = 7;

app.use(express.json());

const corsOrigin = process.env.CORS_ORIGIN;
if (corsOrigin || process.env.NODE_ENV !== 'production') {
  app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', corsOrigin || 'http://localhost:3000');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    if (req.method === 'OPTIONS') {
      res.sendStatus(204);
      return;
    }
    next();
  });
}

fs.mkdirSync(path.dirname(DB_PATH), { recursive: true });
const db = new sqlite3.Database(DB_PATH);

db.serialize(() => {
  db.run(
    `CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL,
      created_at TEXT NOT NULL
    )`
  );
  db.run(
    `CREATE TABLE IF NOT EXISTS sessions (
      token TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      created_at TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id)
    )`
  );
});

const run = (sql, params = []) =>
  new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) {
        reject(err);
        return;
      }
      resolve(this);
    });
  });

const get = (sql, params = []) =>
  new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(row);
    });
  });

const normalizeEmail = (email) => (email || '').trim().toLowerCase();

const hashPassword = (password) => {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(password, salt, 64);
  return `${salt.toString('base64')}:${hash.toString('base64')}`;
};

const verifyPassword = (password, storedHash) => {
  const [saltB64, hashB64] = storedHash.split(':');
  if (!saltB64 || !hashB64) {
    return false;
  }
  const salt = Buffer.from(saltB64, 'base64');
  const expected = Buffer.from(hashB64, 'base64');
  const actual = crypto.scryptSync(password, salt, 64);
  return crypto.timingSafeEqual(expected, actual);
};

const createSession = async (userId) => {
  const token = crypto.randomBytes(32).toString('hex');
  const createdAt = new Date();
  const expiresAt = new Date(createdAt);
  expiresAt.setDate(expiresAt.getDate() + SESSION_DAYS);

  await run(
    `INSERT INTO sessions (token, user_id, created_at, expires_at)
     VALUES (?, ?, ?, ?)`,
    [token, userId, createdAt.toISOString(), expiresAt.toISOString()]
  );

  return token;
};

const getAuthToken = (req) => {
  const header = req.headers.authorization || '';
  if (header.startsWith('Bearer ')) {
    return header.slice(7);
  }
  return null;
};

const requireAuth = async (req, res, next) => {
  const token = getAuthToken(req);
  if (!token) {
    res.status(401).json({ error: 'Missing auth token.' });
    return;
  }

  try {
    const row = await get(
      `SELECT sessions.token, sessions.expires_at, users.id, users.name, users.email, users.role
       FROM sessions
       JOIN users ON users.id = sessions.user_id
       WHERE sessions.token = ?`,
      [token]
    );

    if (!row) {
      res.status(401).json({ error: 'Invalid session.' });
      return;
    }

    if (new Date(row.expires_at) <= new Date()) {
      await run('DELETE FROM sessions WHERE token = ?', [token]);
      res.status(401).json({ error: 'Session expired.' });
      return;
    }

    req.user = {
      id: row.id,
      name: row.name,
      email: row.email,
      role: row.role,
    };
    req.token = token;
    next();
  } catch (error) {
    res.status(500).json({ error: 'Failed to verify session.' });
  }
};

app.post('/api/signup', async (req, res) => {
  const name = (req.body.name || '').trim();
  const email = normalizeEmail(req.body.email);
  const password = req.body.password || '';
  const role = (req.body.role || 'Teacher').trim();

  if (!name || !email || !password) {
    res.status(400).json({ error: 'Name, email, and password are required.' });
    return;
  }

  if (password.length < 8) {
    res.status(400).json({ error: 'Password must be at least 8 characters.' });
    return;
  }

  try {
    const passwordHash = hashPassword(password);
    const createdAt = new Date().toISOString();
    const result = await run(
      `INSERT INTO users (name, email, password_hash, role, created_at)
       VALUES (?, ?, ?, ?, ?)`,
      [name, email, passwordHash, role, createdAt]
    );

    const token = await createSession(result.lastID);
    res.json({
      token,
      user: { id: result.lastID, name, email, role },
    });
  } catch (error) {
    if (error.code === 'SQLITE_CONSTRAINT') {
      res.status(409).json({ error: 'Account already exists for this email.' });
      return;
    }
    res.status(500).json({ error: 'Unable to create account.' });
  }
});

app.post('/api/login', async (req, res) => {
  const email = normalizeEmail(req.body.email);
  const password = req.body.password || '';

  if (!email || !password) {
    res.status(400).json({ error: 'Email and password are required.' });
    return;
  }

  try {
    const user = await get(
      `SELECT id, name, email, role, password_hash FROM users WHERE email = ?`,
      [email]
    );

    if (!user || !verifyPassword(password, user.password_hash)) {
      res.status(401).json({ error: 'Invalid email or password.' });
      return;
    }

    const token = await createSession(user.id);
    res.json({
      token,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
      },
    });
  } catch (error) {
    res.status(500).json({ error: 'Unable to sign in.' });
  }
});

app.post('/api/logout', requireAuth, async (req, res) => {
  try {
    await run('DELETE FROM sessions WHERE token = ?', [req.token]);
    res.json({ ok: true });
  } catch (error) {
    res.status(500).json({ error: 'Unable to sign out.' });
  }
});

app.get('/api/me', requireAuth, (req, res) => {
  res.json({ user: req.user });
});

app.get('/api/health', (req, res) => {
  res.json({ ok: true });
});

const buildPath = path.join(__dirname, 'build');
if (fs.existsSync(buildPath)) {
  app.use(express.static(buildPath));
  app.get('*', (req, res) => {
    res.sendFile(path.join(buildPath, 'index.html'));
  });
}

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`Server listening on port ${PORT}`);
});
