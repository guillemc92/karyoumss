#!/bin/sh
# Primer arranque de Postgres (DD-OPS-001 D2, ADR-0012): el rol de backend-admin
# y su schema. El rol no es superusuario: solo es dueño del schema 'admin'.
# La contraseña la genera el job secretos; nunca está en el repositorio.
set -eu
clave="$(cat /secretos/postgres/ADMIN_DB_PASSWORD)"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v clave="$clave" <<'SQL'
CREATE ROLE biomed_admin_service LOGIN PASSWORD :'clave';
CREATE SCHEMA admin AUTHORIZATION biomed_admin_service;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL
