const crypto = require('crypto');
const fs = require('fs/promises');
const path = require('path');

class EncryptedSessionStore {
  constructor(directory, key) {
    this.directory = directory;
    this.key = crypto.createHash('sha256').update(key).digest();
  }

  file(id) {
    return path.join(this.directory, `${crypto.createHash('sha256').update(id).digest('hex')}.session`);
  }

  async put(id, value) {
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv('aes-256-gcm', this.key, iv);
    const ciphertext = Buffer.concat([cipher.update(JSON.stringify(value)), cipher.final()]);
    await fs.mkdir(this.directory, { recursive: true, mode: 0o700 });
    await fs.writeFile(this.file(id), Buffer.concat([iv, cipher.getAuthTag(), ciphertext]), { mode: 0o600 });
  }

  async get(id) {
    const data = await fs.readFile(this.file(id));
    const decipher = crypto.createDecipheriv('aes-256-gcm', this.key, data.subarray(0, 12));
    decipher.setAuthTag(data.subarray(12, 28));
    return JSON.parse(Buffer.concat([decipher.update(data.subarray(28)), decipher.final()]).toString());
  }
}

module.exports = { EncryptedSessionStore };
