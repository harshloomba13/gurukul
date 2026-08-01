FROM node:20-bookworm

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev \
    && npx playwright install --with-deps chromium \
    && npm cache clean --force

COPY src ./src
COPY openapi.yaml ./openapi.yaml

ENV NODE_ENV=production
ENV PORT=10000
EXPOSE 10000

CMD ["node", "src/server.js"]
