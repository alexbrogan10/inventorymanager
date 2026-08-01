# --- dev: used by docker-compose for local development (hot reload via a
# bind-mounted source volume, see docker/docker-compose.yml) ---
FROM node:22-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# --- build: compiles the production static bundle ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Vite bakes VITE_* env vars into the bundle at build time, not runtime - the
# production compose passes this as a relative path (e.g. `/api/v1`) so the
# built app calls same-origin and nginx's /api/ proxy (below) forwards to
# the backend, matching how the dev server's absolute localhost URL works
# differently in that environment.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- prod: serves the static bundle with nginx, reverse-proxying /api and
# /static to the backend service (see nginx.conf). nginx-unprivileged runs
# as a non-root user out of the box (listening on 8080), rather than
# patching the stock image's permissions by hand. ---
FROM nginxinc/nginx-unprivileged:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:8080/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
