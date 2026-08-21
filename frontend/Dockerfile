# ============================================================================
# MAHOUN Frontend - Production Multi-Stage Dockerfile
# ============================================================================
# Architecture: Multi-stage build with Vite + Nginx
# Target Size: ~50MB (Nginx + static assets)
# Security: Non-root user, minimal attack surface
# Performance: Static file serving with caching headers
# Build Output: /dist (matches vite.user.config.ts outDir)
# ============================================================================

# Build arguments
ARG NODE_VERSION=20-alpine
ARG NGINX_VERSION=alpine

# ============================================================================
# Stage 1: Builder - Compile frontend assets with Vite
# ============================================================================
FROM node:${NODE_VERSION} AS builder

WORKDIR /app

# Install dependencies with cache optimization
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline --no-audit --no-fund

# Copy source code and build
COPY . .
RUN npm run build

# ============================================================================
# Stage 2: Runtime - Nginx serving static files
# ============================================================================
FROM nginx:${NGINX_VERSION} AS runtime

# Security: Create non-root user
RUN addgroup -g 1000 nginxapp \
    && adduser -u 1000 -G nginxapp -s /bin/sh -D nginxapp \
    && mkdir -p /var/cache/nginx /var/run /var/log/nginx \
    && chown -R nginxapp:nginxapp /var/cache/nginx /var/run /var/log/nginx /etc/nginx/conf.d

# Copy built assets from builder (outputs to /dist per vite config)
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Security: Switch to non-root user
USER nginxapp:nginxapp

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Nginx entrypoint
CMD ["nginx", "-g", "daemon off;"]