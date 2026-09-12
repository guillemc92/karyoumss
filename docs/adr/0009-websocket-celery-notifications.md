---
id: ADR-0009
title: Detalles Operativos del Push WebSocket (Implementación de ADR-0002)
date: 2026-06-23
status: accepted
related: [ADR-0002]
---

# ADR 0009: Detalles Operativos del Push WebSocket (Implementación de ADR-0002)

> ⚠️ **Nota de revisión (2026-06-23):** Este documento **no introduce una decisión arquitectónica nueva**. Detalla **cómo se implementa** el paso 4 de ADR-0002 ("a WebSocket event is pushed to the client via a dedicated Manager"). Si la decisión de fondo (push vs. polling) cambia, este ADR se vuelve obsoleto junto con ADR-0002.

## Contexto

ADR-0002 §Decisión punto 4 ya establece:

> *"Upon completion, a WebSocket event is pushed to the client via a dedicated Manager."*

Esta ADR aterriza los detalles operativos que ADR-0002 deja abiertos: **cómo** el worker Celery entrega el evento al manager WebSocket sin acoplamiento directo.

## Decisión Operativa

Cadena de notificación cuando un worker Celery termina una tarea de inferencia:

```
[Celery Worker]
    ↓ on_task_success() hook
    ↓ publica JSON en canal Redis
    ↓ channel: "biomed:sample:{sample_id}:events"
[Redis Pub/Sub broker]
    ↓ broker entrega mensaje a suscriptores activos
[FastAPI WebSocket Manager]
    ↓ ConnectionManager.broadcast(sample_id, payload)
    ↓ filtra conexiones autenticadas con scope sobre ese sample_id
[Cliente Frontend (React)]
    ↓ useWebSocketSample(sampleId) hook
    ↓ actualiza store Zustand (chromosomeStore)
    ↓ Konva re-renderiza con color de semáforo correspondiente
```

### Componentes

| Componente | Responsabilidad | Ubicación |
|---|---|---|
| `TaskNotifier` | Hook `on_task_success` que publica en Redis | `backend/app/tasks/notifier.py` |
| `RedisPubSub` | Adapter de broker (puerto hexagonal) | `backend/app/infrastructure/redis_pubsub.py` |
| `WSConnectionManager` | Mantiene `Dict[sample_id, Set[WebSocket]]`, broadcast selectivo | `backend/app/ws/manager.py` |
| `SampleEventPublisher` | Caso de uso que arma el payload `SampleEvent` | `backend/app/services/notifications.py` |
| `useWebSocketSample` | Hook React que abre WS y despacha al store | `frontend/src/services/websocket.ts` |

### Contrato del payload (evento `chromosome.ready`)

```typescript
// frontend/src/types/events.ts
type SampleEvent =
  | { type: "sample.processing"; sample_id: string; progress: number }
  | { type: "chromosome.ready";   sample_id: string; chromosome_id: string;
                                   pair_number: number; confidence_score: number }
  | { type: "sample.draft_ready"; sample_id: string; chn_code: string;
                                   draft_id: string; total_chromosomes: number }
  | { type: "sample.error";       sample_id: string; error_code: string;
                                   error_message: string };
```

### Eventos que disparan actualización visual

| Evento backend | Acción frontend | Anclaje RN |
|---|---|---|
| `chromosome.ready` | Calcular `status` (green/orange/red) y actualizar `Chromosome` en Zustand | RN-02 |
| `sample.draft_ready` | Habilitar transición a pantalla de validación | FSD-UC-002 |
| `sample.error` | Mostrar banner degradado (FSD-UC-007) | RN-07 |
| `sample.processing` | Barra de progreso (UX) | NFR-001 |

### Resiliencia

- **Reconexión cliente:** exponential backoff (1s → 2s → 4s, máx 30s) + replay del último `event_id` recibido.
- **Idempotencia servidor:** Cada evento lleva `event_id = ULID()`. El cliente descarta duplicados.
- **Backpressure:** Si el cliente no lee en 10s, el manager cierra la conexión (ping cada 5s).
- **Auth WS:** Token JWT en query string `?token=...` validado en handshake `accept`.

## Trade-offs

**A favor (vs. HTTP polling):**
- Latencia de notificación: <100ms p95 (vs. polling cada 5s = 2.5s promedio).
- Reducción de carga: 1 evento × N conexiones vs. N requests cada 5s.
- UX fluida (cambio instantáneo de color en Konva).

**Costo:**
- Mayor uso de memoria Redis (canales pub/sub activos por muestra en proceso).
- Lógica de reconexión en cliente (no trivial, requiere pruebas dedicadas — ver TASK-006 de SPEC-006).

## Consecuencias

- AGENTS.md §9 (Flujo Pipeline IA) se mantiene válido: el último paso sigue siendo `Redis PubSub → WebSocket push "Borrador listo"`.
- El **frontend debe implementar reconnection** desde el inicio (ver CA-5 de SPEC-006).
- El **backend debe implementar idempotencia** para evitar eventos duplicados tras reconexión.

## Referencias

- ADR-0002 (Async Pipeline using Redis and Celery) — decisión arquitectónica de fondo
- AGENTS.md §9 (Flujo de Pipeline IA)
- SPEC-006 §2.3 (Integración con Backend — WebSocket)
- FSD §4.2 FSD-UC-002 paso 10 ("Sistema cambia estado del caso")