# ============================================================================
# MAHOUN Enterprise Edition - Production-Grade Frontend Dockerfile
# ============================================================================
# Multi-stage build: Build with Node.js, serve with Nginx
# Pinned versions for deterministic builds
# ============================================================================

# ============================================================================
# Stage 1: Dependencies - Install node_modules
# ============================================================================
FROM node:20.12.2-alpine3.19 AS deps

WORKDIR /build

# Copy ONLY package files first (for layer caching)
COPY package.json package-lock.json ./

# Install dependencies using npm ci (clean install from lockfile)
# Use --omit=dev after build stage to reduce size
RUN npm ci --prefer-offline --no-audit

# ============================================================================
# Stage 2: Builder - Build application
# ============================================================================
FROM node:20.12.2-alpine3.19 AS builder

WORKDIR /build

# Copy node_modules from deps stage
COPY --from=deps /build/node_modules ./node_modules

# Copy source code
COPY . .

# Build the application (outputs to /build/dist)
# Vite build includes minification and tree-shaking
RUN npm run build

# ============================================================================
# Stage 3: Runtime - Serve with Nginx
# ============================================================================
FROM nginx:1.27.3-alpine AS runtime

# Install curl for healthcheck
RUN apk add --no-cache curl

# Create non-root nginx user (nginx already exists in nginx image)
# Ensure nginx can write to necessary directories
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Copy built static files from builder
COPY --from=builder --chown=nginx:nginx /build/dist /usr/share/nginx/html

# Copy nginx configuration
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.bak

# Switch to non-root user (nginx user uid=101)
USER nginx

# Expose HTTP port
EXPOSE 80

# Health check (use curl instead of wget for consistency)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]

