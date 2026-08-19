# Revisión uno a uno — guion y hoja de notas

> Su requisito: *«el documento debe reflejar los puntos conversados en las
> revisiones uno a uno, incorporando lo que se puede mejorar o lo que faltaba
> en versiones previas»*.
>
> Es decir: **esta reunión es la materia prima de §9 del informe**. El objetivo
> no es que te diga «está bien» — eso no se puede incorporar. El objetivo es
> salir con frases concretas.

---

## 1 · Lo primero que enseñas (3 min)

No abras por el código. Abre por lo que te distingue:

> «Implementé los seis niveles, pero lo que quiero enseñarte es **cómo los
> medí**. Tengo cinco instrumentos de evaluación, cada uno con su comando.»

Y enseña **una** cosa corriendo:

```bash
cd backend-clinic
.venv/Scripts/python manage.py demo_sugerencias    # código + salida en una pantalla
```

Si hay tiempo y quiere ver el producto:

```bash
CLINIC_LLM_ENABLED=true .venv/Scripts/python manage.py demo_flujo_clinico
```

---

## 2 · Las tres cosas que debe oír de ti, no descubrir él

**1. El resultado incómodo, dicho por ti primero.**

> «Medí el coste de corrección: 64 acciones por caso frente a 46 de hacerlo a
> mano. Hoy mi pipeline añade trabajo en vez de ahorrarlo. Sé por qué y sé qué
> sigue.»

**2. La desviación del laboratorio, con su motivo.**

> «Mi herramienta de escritura **nunca ejecuta**, ni con `confirmado=true`, a
> diferencia del `cancelar_pedido` del Lab5. Cancelar una compra es reversible;
> validar un cariotipo lo firma un profesional con su identidad.»

**3. Un error propio que corregiste midiendo.**

> «Un análisis mío a ojo dijo que había cuatro regresiones. Reproduje el estado
> anterior en un worktree de git y resultó que la regresión real eran dos.»

Enseñar un error propio corregido con evidencia vale más que enseñar tres
aciertos.

---

## 3 · Las preguntas que SÍ producen material

Evita «¿qué te parece?». Produce «está bien», que no se puede incorporar.

Pregunta esto, con papel delante:

1. **«¿Qué le falta a este documento para ser un 10?»**
   Directa, y la única que apunta al objetivo.

2. **«¿La explicación del código es del nivel que pides, o esperas más detalle
   en alguna parte concreta?»**
   Su requisito literal fue «no basta con pegar el código». Que te señale dónde.

3. **«¿Qué esperas ver en la presentación formal que no esté ya aquí?»**
   La presentación se agenda la próxima semana: esto te adelanta el trabajo.

4. **«De los seis niveles, ¿cuál crees que está más flojo?»**
   Te da una prioridad que no tienes que adivinar.

5. **«¿El nivel 5 suma o distrae, siendo que no lo pediste?»**
   Zanja la duda de si mencionarlo en la defensa.

---

## 4 · Notas de la revisión

> Apunta **frases suyas**, no resúmenes tuyos. Las frases se citan en §9; los
> resúmenes se diluyen.

**Fecha:** ___/08/2026

**Lo que señaló como mejorable:**

-
-
-

**Lo que valoró:**

-
-

**Lo que espera para la presentación formal:**

-
-

**Frase textual que conviene citar en §9:**

> «...»

---

## 5 · Después de la revisión

1. Pásame las notas → incorporo §9.8 «Lo señalado en la revisión uno a uno»
2. Regenero el `.docx`
3. **Subes el jueves**, no el viernes

El retraso ya te costó 10 puntos una vez. Es la única variable que sabemos con
certeza que pesa en la nota.
