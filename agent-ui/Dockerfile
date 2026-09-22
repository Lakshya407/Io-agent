# Multi-stage production build for the AI Agent Platform frontend.
#
# Stage 1 — Node: install dependencies and compile the Vite app to `dist/`.
# Stage 2 — Nginx: serve the static bundle with an SPA fallback and a
#           reverse proxy to the backend so the browser and API share an
#           origin (no CORS in production).

# ---------- Stage 1: build ----------
FROM node:22-alpine AS build

WORKDIR /app

# Copy lockfile + manifest first so the dependency layer is cached unless
# they change.
COPY package.json package-lock.json* ./

# `npm ci` needs a lockfile; fall back to `npm install` if it is missing.
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi

# Copy the rest of the sources and build.
COPY . .

# `.env.production` sets VITE_API_BASE_URL=/api/v1 (served by Nginx).
RUN npm run build

# ---------- Stage 2: runtime ----------
FROM nginx:1.27-alpine AS runtime

# Replace the default site config with the SPA + proxy configuration.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health probe: Nginx serves its own index, so a 200 from "/" means ready.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
