# ==============================================================================
# Frontend Dockerfile - RAG Document Chatbot
# ==============================================================================
# Multi-stage build: Build stage + Nginx serving stage
# ==============================================================================

# ==============================================================================
# Build stage
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build the Vite app
# Note: VITE_API_URL should be set to the backend URL for production
ENV VITE_API_URL=http://localhost:8000
RUN npm run build

# ==============================================================================
# Nginx serving stage
# ==============================================================================
FROM nginx:1.25-alpine

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
