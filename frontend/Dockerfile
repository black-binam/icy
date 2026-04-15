# syntax=docker/dockerfile:1.7

# ---------- Étape 1 : build ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Cache des deps
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# Code source
COPY . .

# Variable d'API injectée au build (Vite remplace au build).
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ---------- Étape 2 : runtime nginx ----------
FROM nginx:1.27-alpine AS runtime

# Sécurité : utilisateur non-root pour Nginx (le port doit être > 1024).
RUN addgroup -S icy && adduser -S icy -G icy

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# Permissions
RUN chown -R icy:icy /usr/share/nginx/html /var/cache/nginx /var/log/nginx /var/run \
    && chmod -R g+rwX /var/cache/nginx /var/log/nginx /var/run

USER icy

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
