# Prompt: WebSocket Manager — Notificación de Progreso

## Metadata
* **ID:** PR-WS-01
* **Componente:** `backend/app/ws/websocket_manager.py`
* **Objetivo:** Enviar notificaciones de actualización de procesamiento en tiempo real.

## Prompt Cuerpo
```
Role: Eres un desarrollador backend especializado en sistemas de tiempo real con FastAPI WebSockets y Redis Pub/Sub.

Task: Implementa el WebSocketManager que:
1. Mantiene conexiones WebSocket activas por sample_id
2. Escucha el canal de Redis y hace push al cliente correcto
3. Payload: {sample_id, status, chromosome_count}

Context:
- NFR: latencia entre publicación Redis y recepción cliente < 500ms

Reasoning:
1. Usar asyncio para escuchar Redis Pub/Sub sin bloquear
2. Mantener dict de conexiones

Stop Condition: Detente cuando el cliente reciba la notificación en <500ms tras la publicación en Redis.

Output:
- `backend/app/ws/websocket_manager.py`
```
