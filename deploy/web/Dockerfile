# web: los dos frontends compilados detrás de un solo Caddy (DD-OPS-001 D4).
# El contexto es la raíz del repositorio; Dockerfile.dockerignore deja pasar
# solo los dos frontends y este Caddyfile.

# --- Etapa 1: compilar los frontends (Node solo existe aquí) ---
FROM node:22.21.1-slim@sha256:25b3eb23a00590b7499f2a2ce939322727fcce1b15fdd69754fcd09536a3ae2c AS frontends
ENV CI=true
WORKDIR /w/frontend-admin
COPY frontend-admin/package.json frontend-admin/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend-admin/ ./
# Las rutas de la API son relativas: el mismo origen (ADR-0020).
RUN VITE_CLINIC_APP_URL=/clinic/ npm run build \
 && rm -f dist/mockServiceWorker.js
WORKDIR /w/frontend-clinic
COPY frontend-clinic/package.json frontend-clinic/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend-clinic/ ./
RUN VITE_BASE_PATH=/clinic/ npm run build \
 && rm -f dist/mockServiceWorker.js

# --- Etapa 2: Caddy compilado con un Go y unas dependencias sin CVE altos ---
# La imagen oficial de Caddy 2.11.7 trae Go 1.26.8, x/net 0.59 y go-jose 4.1.5,
# con HIGH que ya tienen parche (ADR-0039 D1). Misma versión de Caddy, recompilada.
FROM golang:1.26.10-alpine@sha256:a2012b4a1d1f9f7e9f44e0d39b805a901e856b1dd80b4e6ee4338db547050308 AS caddy
WORKDIR /w
ENV CGO_ENABLED=0
RUN go install github.com/caddyserver/xcaddy/cmd/xcaddy@v0.4.7 \
 && xcaddy build v2.11.7 --output /w/caddy \
      --replace golang.org/x/net=golang.org/x/net@v0.60.0 \
      --replace github.com/go-jose/go-jose/v4=github.com/go-jose/go-jose/v4@v4.1.6

# --- Etapa 3: solo los dist/ y Caddy ---
FROM caddy:2.11.7-alpine@sha256:e70b164da81ef698b3ad19af799ea6086ce6d9e48ed4079eb9fe26f6fbf14ee5
# apk upgrade: los parches de Alpine que la imagen base todavía no trae (ADR-0039 D1).
# curl no lo usa nada aquí: el healthcheck es el wget de busybox.
RUN apk upgrade --no-cache \
 && apk del --no-cache curl \
 && adduser -D -H -u 10001 web \
 && mkdir -p /data /config \
 && chown -R web:web /data /config
COPY --from=caddy /w/caddy /usr/bin/caddy
COPY deploy/web/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontends /w/frontend-admin/dist /srv/admin
COPY --from=frontends /w/frontend-clinic/dist /srv/clinic
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
  CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
