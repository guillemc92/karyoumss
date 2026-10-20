# Instrucciones de pruebas de rendimiento

## Alcance

No hay requisito de rendimiento cuantificado. NFR1 pide que la consulta no espere a que termine una inferencia en curso: es un requisito de comportamiento, no un umbral de latencia. La estrategia Minimal no genera pruebas de carga.

## Verificación de NFR1

La cubre la prueba del endpoint con el límite ocupado: responde 200 con `en_curso = 1` y `libres = 0` mientras un hilo retiene la única plaza. Para ejecutarla, desde `backend-ml/`:

```bash
py -3.12 -m pytest -q tests/test_estado_inferencias.py
```
