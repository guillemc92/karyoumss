# Stack tecnológico — karyoumss-main

Nota: `CLAUDE.md` menciona U-Net, Celery, Redis, PostgreSQL y Docker Compose. En el código escaneado no hay U-Net (la segmentación es OpenCV clásica), ni Celery/Redis, ni Docker Compose. backend-admin declara el driver de PostgreSQL, pero en local se usan archivos `*.sqlite3`. Esta tabla refleja lo que hay en el código.

## backend-ml

| Tecnología | Versión declarada | Versión observada | Uso |
|---|---|---|---|
| Python | — | 3.12 (`py -3.12`) | Lenguaje |
| FastAPI | `>=0.110` | 0.140.0 | API |
| uvicorn[standard] | `>=0.29` | — | Servidor ASGI |
| python-multipart | `>=0.0.9` | — | Formularios multipart |
| opencv-python-headless | `>=4.9` | 5.0.0 | Segmentación |
| NumPy | `>=1.26` | — | Arrays |
| torch / torchvision | `>=2.2` / `>=0.17` | 2.13.0+cpu | EfficientNet-B3, Grad-CAM |
| Pillow | (transitiva) | — | Letterbox |
| Pydantic | (vía FastAPI) | — | Esquemas |
| pytest / httpx | `>=8.0` / `>=0.27` | 8.3.2 | Pruebas |

Modelo: EfficientNet-B3, 24 clases, entrada de 300 px con letterbox, versión v3 (`models/model_meta.json`).

## backend-clinic
Django 5.0.6, DRF 3.15.2, simplejwt 5.3.1, django-cors-headers 4.4.0, httpx 0.27.0, cryptography 43.0.0, openai `>=1.0` (contra Ollama local), langgraph `>=1.0`, langgraph-checkpoint-sqlite `>=3.0`, langchain-openai `>=1.0`. Pruebas con pytest + pytest-cov (`--cov-fail-under=90`).

## backend-admin
Django 5.0.6, DRF 3.15.2, django-guardian 2.4.0, simplejwt 5.3.1, PyJWT 2.9.0, pyotp 2.10.0, qrcode 8.2, Pillow 12.3.0, cryptography 49.0.0, django-auditlog 3.0.0, psycopg[binary] 3.2.1, django-ratelimit 4.1.0, gunicorn 22.0.0, pytest 8.3.2, pytest-django 4.9.0, pytest-cov 5.0.0, factory-boy 3.3.0, ruff 0.5.5.

## Frontends
React ^18.3.1, react-router-dom ^6, Vite ^5.3.4, TypeScript ^5.5.3, Vitest ^1.6.0, MSW ^2.3.5. Solo en frontend-clinic: Konva ^9.3.22, react-konva ^18.2.16 y @playwright/test ^1.63.0. En la raíz: vitest, @vitest/coverage-v8 y jsdom como devDependencies.

## Infraestructura de desarrollo
Caddy (`Caddyfile.dev`, :3000) como proxy inverso; Ollama local para el LLM. Sin contenedores ni CI en el repositorio.
