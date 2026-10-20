# Reverse Engineering Timestamp

## Run Record

- Date: 2026-10-19
- Commit: 4fc0de6050477ff84226f880dc465f60c10f61c7

Primera ejecución (sin store previo) para el intent `estado-inferencias`. Profundidad Minimal. El análisis profundo se limitó al código de producción y a las pruebas de `backend-ml`, más el cliente que lo consume en backend-clinic. El resto del monorepo se recorrió a nivel de directorio, por eso el bloque es `kind: partial`. El árbol de trabajo tenía cambios sin commitear fuera de las rutas analizadas. La huella cubre los archivos tal como estaban en disco.

## Scope of Analysis

```yaml
scope_version: 1
kind: partial
intent: estado-inferencias
fingerprint: 7625b93d796d2a341eddaa7beee6a672619ac61b
analyzed:
  paths:
    - backend-ml/app/
    - backend-ml/tests/
    - backend-ml/requirements.txt
    - backend-ml/.env.example
    - backend-ml/README.md
    - backend-clinic/apps/samples/pipeline_client.py
  components:
    - API FastAPI de backend-ml
    - LimiteInferencias
    - Pipeline de inferencia
    - OpenCVSegmenter
    - EfficientNetClassifier
    - PlaceholderClassifier
    - Preprocesado letterbox
    - Reparto global
    - Grad-CAM
    - Esquemas Pydantic
    - PipelineClient
shallow:
  paths:
    - backend-ml/training/
    - backend-ml/models/
    - backend-clinic/
    - backend-admin/
    - frontend-clinic/
    - frontend-admin/
    - docs/
    - scripts/
    - pocs/
    - Caddyfile.dev
```
