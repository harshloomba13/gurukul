FROM node:20-bookworm
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev && npx playwright install --with-deps chromium && npm cache clean --force
COPY src ./src
ENV PORT=10000 SESSION_DIR=/var/data/sessions AUDIT_LOG=/var/data/audit/events.jsonl
EXPOSE 10000
CMD ["node", "src/server.js"]
