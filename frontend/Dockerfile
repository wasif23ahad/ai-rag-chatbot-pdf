# ==============================================================================
# Frontend Dockerfile — RAG Document Chatbot
# ==============================================================================
# Multi-stage: Node build → Nginx static serve
# For Render: uses $PORT via envsubst in nginx config
# ==============================================================================

# ── Stage 1: Build the React app ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# VITE_API_URL is set at build-time via Render env vars or defaults to empty
# (empty = same-origin, which is what we want when Nginx proxies /api)
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Serve with Nginx ────────────────────────────────────────────────
FROM nginx:1.25-alpine

# Remove default config
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy the template (uses $PORT and $BACKEND_URL)
COPY nginx.render.conf /etc/nginx/templates/default.conf.template

# Copy built React assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Render injects $PORT — Nginx needs to listen on it
ENV PORT=80
ENV BACKEND_URL=http://localhost:8000

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
