# Instrucciones de pruebas de seguridad

## Requisitos cubiertos

- **FR4**: secreto interno obligatorio. 403 si la cabecera falta o es incorrecta; 503 si backend-ml no tiene el secreto configurado.
- **NFR2**: comparación de tiempo constante, y el valor del secreto nunca aparece en una respuesta.

## Pruebas automatizadas

En `backend-ml/tests/test_estado_inferencias.py`:

- 403 sin cabecera `X-Internal-Secret`;
- 403 con un secreto incorrecto;
- 503 sin `INTERNAL_SERVICE_SECRET` configurado, mientras `/health/` sigue en 200.

Para ejecutarlas, desde `backend-ml/`:

```bash
py -3.12 -m pytest -q tests/test_estado_inferencias.py
```

Las pruebas usan un secreto inventado (`secreto-de-prueba-no-real`), nunca uno real.

## Revisión manual (NFR2)

- `backend-ml/app/main.py` compara con `hmac.compare_digest`, no con `==`.
- Los textos de error («Estado de inferencias no configurado», «Secreto de servicio inválido») no incluyen ni el valor recibido ni el esperado.
- El endpoint no escribe nada en el log.
