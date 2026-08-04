const SENSITIVE_KEY_PATTERN = /(address|api[_-]?key|authorization|card|cookie|email|payment|phone|secret|session|token)/i;

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;

  return Object.fromEntries(Object.entries(value).map(([key, nested]) => [
    key,
    SENSITIVE_KEY_PATTERN.test(key) ? '[REDACTED]' : redact(nested),
  ]));
}

class ConsoleAuditLogger {
  async record(event, details = {}) {
    console.log(JSON.stringify({
      audit: true,
      event,
      at: new Date().toISOString(),
      ...redact(details),
    }));
  }
}

class MemoryAuditLogger {
  constructor() {
    this.records = [];
  }

  async record(event, details = {}) {
    this.records.push({ event, ...redact(details) });
  }
}

module.exports = { ConsoleAuditLogger, MemoryAuditLogger, redact };
