const fs = require('fs/promises');
const path = require('path');

class AuditLog {
  constructor(file) { this.file = file; }
  async record(event, fields = {}) {
    await fs.mkdir(path.dirname(this.file), { recursive: true });
    const safe = Object.fromEntries(Object.entries(fields).filter(([key]) => !/token|secret|password|session/i.test(key)));
    await fs.appendFile(this.file, `${JSON.stringify({ at: new Date().toISOString(), event, ...safe })}\n`, { mode: 0o600 });
  }
}

module.exports = { AuditLog };
