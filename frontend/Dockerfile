# AgentTrace frontend image — multi-stage build producing a minimal
# "standalone" Next.js server (see next.config.js's `output: "standalone"`).

FROM node:20-slim AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
# Baked in at build time since Next.js inlines NEXT_PUBLIC_* vars into
# the client bundle; override via docker-compose.yml's build args if
# the backend isn't reachable at localhost:8000 from the browser.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
