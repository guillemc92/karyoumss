# Demo 1 de M8 — guion (lunes 19/10/2026, 19:00)

Tres features comprometidas en Classroom: issues **#2, #3 y #4**, entregadas en
`release/8.1.0`. Unos **3 minutos** en total.

## Antes de entrar (18:40)

1. **Cerrar Illustrator y los navegadores que no uses.** El 19/10 Illustrator tenía
   la CPU al 100 % y cada segmentación pasaba de ~19 s a más de 2 min.
2. Abrir **tres terminales en Git Bash** en la raíz del repositorio.
3. En la terminal 1, levantar backend-ml y dejarlo corriendo:
   ```bash
   cd backend-ml && py -3.12 -m uvicorn app.main:app --port 8000
   ```
4. En la terminal 2, calentar el modelo (tarda ~15 s la primera vez):
   ```bash
   curl http://localhost:8000/health/
   ```

## Apertura (20 s)

> «Mi compromiso para hoy fueron tres features, las tres salen de la auditoría que
> hicimos del repositorio: dos hallazgos de concurrencia de severidad alta y uno de
> secretos. Están en las issues 2, 3 y 4, y en `release/8.1.0`.»

## Feature 1 — La inferencia no congela backend-ml (issue #2) · 1 min

```bash
py -3.12 scripts/demo_m8_concurrencia.py --url http://localhost:8000
```

Mientras corre (~45 s):

> «Lanzo dos segmentaciones reales a la vez y consulto `/health/` cada medio segundo.
> Antes, la segmentación corría dentro de un `async def` y congelaba el único event
> loop: con la CPU libre medimos que `/health/` tardaba **44 segundos** en contestar.
> Ahora contesta siempre, en unos **3,5 segundos**, y la segunda segmentación no hace
> cola a ciegas: recibe un **503 con `Retry-After`**, que el cliente ya trata como
> degradación.»

Al terminar, la honestidad que se defiende:

> «No llega al objetivo de 1 segundo que puse en la issue. Las pruebas automáticas lo
> daban por bueno porque simulaban la inferencia con una espera que libera el GIL; la
> segmentación real no lo libera. La solución es un worker en otro proceso, que es el
> experimento E4 del módulo.»

| | `/health/` durante dos segmentaciones | Segunda segmentación |
|---|---|---|
| Antes (`release/8.0.0`) | 44 s y 34 s | termina a los 79 s, en cola |
| Ahora (`release/8.1.0`) | 11 de 11 respuestas, peor 3,9 s | 503 + `Retry-After: 25` a los 28 s |

## Feature 2 — LLM con reintentos explícitos y límite (issue #3) · 45 s

```bash
cd backend-clinic && .venv/Scripts/python.exe -m pytest apps/samples/tests/test_llm_limites.py -v --no-cov -p no:warnings; cd ..
```

> «El SDK de OpenAI reintentaba dos veces en secreto, también tras un timeout de 240
> segundos: una petición podía esperar 12 minutos. Ahora un solo punto crea los cinco
> clientes del LLM con `max_retries` en cero, y como máximo dos llamadas van a la vez.
> La tercera recibe "ocupado" en menos de 5 segundos y **no** abre el circuit breaker,
> porque estar ocupado no es una caída. Hay una prueba de arquitectura que falla si
> alguien vuelve a crear un cliente por su cuenta.»

## Feature 3 — Sin secretos por defecto (issue #4) · 40 s

```bash
backend-clinic/.venv/Scripts/python.exe scripts/demo_m8_secretos.py
git check-ignore -v backend-ml/.env frontend-clinic/.env
```

> «Antes, si un despliegue olvidaba la variable, el servicio arrancaba con un secreto
> escrito en el código, que conoce cualquiera con acceso al repositorio. Ahora no
> arranca y dice exactamente cuál falta. Y ningún `.env` real puede entrar al
> repositorio, en ninguna carpeta.»

## Cierre (15 s)

> «Cada feature tiene pruebas que comprobamos que fallan al reintroducir el defecto.
> El aporte está en `8.1.0-aportes.md`. Lo siguiente: el worker aparte para la
> inferencia, medido con k6.»

## Si algo falla en vivo

- **backend-ml no arranca:** muestra la tabla de la feature 1 de este guion; son las
  mediciones reales del 19/10.
- **La segmentación tarda mucho:** algo ocupa la CPU (Illustrator, navegador). La
  feature 2 y la 3 no dependen de la CPU: sigue con ellas.
