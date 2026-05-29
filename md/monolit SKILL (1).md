---

name: monolith-decomposition-architect description: \> Propone la descomposición en microservicios del producto a partir de bounded contexts y un heat map de cambios, aplicando Scale Cube, Decompose by Business Capability, Decompose by DDD Subdomain, regla "Database per service" y el árbol de decisión "¿migrar a microservicios ahora / después / nunca?". Detecta el anti-patrón Distributed Monolith. Produce la tabla de servicios del DTI y el esqueleto de ADR de descomposición. allowed-tools:

- read  
- edit model-tier: opus fsd-version-min: v0.1 status: stable owner: Módulo 4 – UMSS

---

# Skill: monolith-decomposition-architect (descomposición en microservicios \+ ADR)

Skill canónica del módulo 4\. Para activarla en Claude Code o Claude Desktop, copia esta carpeta a `~/.claude/skills/monolith-decomposition-architect/` (alcance: tu usuario, todos los proyectos) o a `.claude/skills/monolith-decomposition-architect/` en la raíz del repositorio del grupo (alcance: solo ese repo).

## 1\. Cuándo activarlo (triggers)

- DURANTE: redacción del DTI §6 (Arquitectura Distribuida), redacción del ADR de descomposición monolito vs microservicios, identificación de seams del monolito, revisión arquitectónica del producto grupal o del examen.  
- ARRANCA cuando: el usuario invoca `"@monolith-decomposition-architect"`, abre `docs/DTI.md` cerca de §6, abre `docs/adr/0003-monolito-vs-microservicios.md`, o pide "descompón mi producto en microservicios" / "identifica los seams".  
- NO ACTIVAR cuando: los bounded contexts aún no están definidos (DTI §4-5 ausente); el equipo es menor a 3 personas y el producto es nuevo (probablemente monolito modular es mejor — pedir al usuario que lo confirme antes).

## 2\. Entradas obligatorias

El usuario MUST proporcionar al menos:

- **Bounded contexts** del producto (mínimo 3\) con su responsabilidad de negocio.  
- **Heat map de cambios frecuentes**: qué partes del dominio cambian más (por commits, por tickets, por release notes históricos).  
- **Tamaño del equipo**: número de devs, distribución en sub-equipos si existe.  
- **Tráfico esperado por seam** (al menos cualitativo: bajo / medio / alto).  
- **Restricciones**: capacidad operativa (¿pueden operar un cluster de Kubernetes? ¿prefieren PaaS?), presupuesto, regulación.

Si falta cualquiera, responder: `"Necesito los bounded contexts, el heat map de cambios, el tamaño del equipo y el tráfico por seam antes de descomponer. Lista mínima: <items que faltan>."`

## 3\. Fuentes de verdad (orden de precedencia)

1. Bounded contexts y mapa estratégico de DDD (DTI §4-5).  
2. UCs del FSD por bounded context.  
3. NFRs del PRD (latencia, throughput, regulación, auditoría).  
4. `AGENTS.md` del repo del producto (si existe; restricciones operativas declaradas).  
5. ADRs vigentes (stack tecnológico, restricciones cloud).

## 4\. Procedimiento

1. **Verificar inputs**. Si faltan bounded contexts, STOP.  
2. **Modelar Scale Cube** del producto en sus 3 ejes:  
   - **X axis** (réplicas detrás de un load balancer): escalado horizontal del monolito; tope cuando la BD es bottleneck.  
   - **Y axis** (descomposición funcional por capacidad de negocio o subdominio DDD): cada microservicio cubre un bounded context.  
   - **Z axis** (sharding por dimensión de datos: usuario, tenant, región): partición horizontal de datos. Decidir cuál eje es el dominante para el producto.  
3. **Aplicar las 2 estrategias de descomposición** complementarias:  
   - **Decompose by Business Capability**: identificar capacidades core ("Order Taking", "Order Fulfillment", "Billing", "Notifications") y asignar 1 capacidad a 1 servicio.  
   - **Decompose by DDD Subdomain**: dividir core / supporting / generic subdomains. Core sub-domains merecen su propio servicio; generic puede ser un SaaS comprado.  
4. **Detectar God classes**: clases del monolito con \> 1000 líneas o con más de 5 responsabilidades; cada God class probablemente cruza varios bounded contexts y es candidata a romperse antes de microservicio-izar.  
5. **Aplicar "Database per service"** como regla no negociable: cada servicio dueño de sus tablas; cero `JOIN` cross-servicio en producción; queries cross-servicio se resuelven con API Composition o CQRS.  
6. **Aplicar el árbol de decisión "migrar a microservicios"**:  
   - ¿Tamaño del equipo ≥ 3 sub-equipos autónomos? Si no → monolito modular gana.  
   - ¿Velocidad de cambio diferente entre bounded contexts? Si todos cambian a la misma velocidad → poco beneficio.  
   - ¿Volúmenes de tráfico diferenciados? Si todo el tráfico es uniforme → no se necesita escala diferenciada.  
   - ¿Hay regulación específica por contexto (PCI en pagos, GDPR en perfiles)? Sí → microservicio aislado.  
   - ¿Capacidad operativa para múltiples servicios (CI/CD, observabilidad, on-call)? Si no → monolito modular o híbrido serverless. El resultado del árbol decide entre 3 opciones: A) microservicios completos / B) monolito modular \+ satélites / C) híbrido serverless \+ monolito modular.  
7. **Detectar Distributed Monolith**: anti-pattern donde se rompió en servicios pero conservaron BD compartida, despliegues acoplados o llamadas REST sync en cascada. Si el diseño actual tiende ahí, marcar como riesgo crítico en el ADR.  
8. **Producir tabla de servicios** y matriz de opciones del ADR.

## 5\. Salida esperada

Tres artefactos:

- Tabla de microservicios para `docs/DTI.md` §6:

| Servicio | Bounded context / capacidad | Responsabilidad | Datos propios (tablas) | API (REST/gRPC) | Eventos publicados | Equipo dueño |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| OrderService | Order Taking | Captura y validación de pedidos | orders, order\_items | POST /orders, GET /orders/{id} | OrderCreated, OrderCancelled | Equipo Pedidos |
| KitchenService | Order Fulfillment | Preparación en cocina | tickets, ticket\_items | gRPC AcceptTicket | TicketAccepted | Equipo Cocina |

- Matriz de opciones evaluadas (al menos 3\) para el ADR:

| Opción | Pros | Contras | Cuándo elegirla |
| :---- | :---- | :---- | :---- |
| A. Microservicios completos | Escalado independiente, equipos autónomos, lenguajes mixtos | Complejidad operativa alta, latencia agregada, debugging difícil | Equipo ≥ 3 sub-equipos, regulación diferenciada |
| B. Monolito modular \+ satélites | Simplicidad operativa, transacciones ACID locales, refactor incremental | Acoplamiento dentro del monolito, escalado uniforme | Equipo pequeño, dominio aún en exploración |
| C. Híbrido serverless | Costo por uso, escalado automático para picos, sin operación de cluster | Vendor lock-in, cold start, debugging distribuido | Tráfico espurio, equipo pequeño en cloud |

- Esqueleto de ADR de descomposición (formato estándar ADR: Context, Decision, Options evaluadas contra dimensiones explícitas, Consequences positivas y negativas).

## 6\. Verificación (criterios de "bien hecho")

- Cada microservicio mapea a exactamente 1 bounded context (o documenta explícitamente por qué 1 contexto se divide).  
- Cada microservicio tiene **datos propios** declarados (cero `JOIN` cross-servicio en producción).  
- Cada microservicio tiene equipo dueño asignado (no "todos somos dueños").  
- El ADR evalúa **≥ 3 opciones** contra **≥ 3 dimensiones** (equipo, velocidad de cambio, tráfico, regulación, ops).  
- El ADR lista **consecuencias positivas Y negativas** (no es panfleto).  
- El diseño no exhibe síntomas de Distributed Monolith (BD compartida, despliegues acoplados, cadenas REST sync de \> 3 saltos).  
- El árbol de decisión está documentado: se vio explícitamente cada pregunta y su respuesta para llegar a la opción elegida.

## 7\. Anti-patrones específicos

- **Distributed Monolith**: BD compartida entre "microservicios" \+ despliegues acoplados \+ cascada REST sync. Mitigación: asignar BD propia a cada servicio \+ IPC async donde sea posible \+ versionado contractual de APIs.  
- **Microservicios prematuros**: descomponer antes de entender el dominio (típico cuando el equipo nunca operó monolitos). Mitigación: empezar con monolito modular bien fronterizado; romper cuando duela.  
- **Microservicios por capa técnica** ("OrderController-Service", "OrderRepository-Service"): viola la regla de bounded context. Mitigación: descomponer por capacidad de negocio o subdominio.  
- **Demasiados microservicios para un equipo pequeño**: tax operativo \> beneficio. Mitigación: regla heurística "≥ 1 sub-equipo autónomo por microservicio crítico".  
- **God microservice**: un servicio absorbe 3+ bounded contexts. Mitigación: aplicar el árbol de decisión a ese servicio de nuevo y romperlo.  
- **Servicios que comparten tablas**: rompe Database per service. Mitigación: una sola tabla pertenece a un solo servicio; los demás consumen via API o eventos.

## 8\. Mini ejemplo de invocación

"Tengo el producto FTGO con bounded contexts: Order Taking, Order Fulfillment (cocina), Delivery, Billing, Notifications, Restaurant Catalog. Heat map: Order Taking cambia 60 % de los meses, Delivery 30 %, los demás \< 10 %. Equipo: 8 devs en 3 sub-equipos. Tráfico: Order Taking 200 req/s pico, los demás \< 50 req/s. AWS-only. Usa el skill `monolith-decomposition-architect` y propón la descomposición \+ esqueleto de ADR de descomposición."

## 9\. Modos de fallo conocidos

- El usuario pide microservicios pero el equipo es de 2 devs y el producto está en exploración → STOP, recomendar monolito modular y documentar la decisión como ADR.  
- Bounded contexts no están definidos en el FSD → STOP, derivar al skill de FSD o pedir al usuario que los defina antes.  
- Heat map de cambios no existe (producto nuevo, sin historia) → STOP, ofrecer modo "best guess basado en NFRs y volúmenes" pero marcarlo como riesgo en el ADR.  
- El usuario quiere romper un God class antes de descomponer → recomendar refactor monolítico primero (extraer módulos), luego microservicio-izar.

## 10\. Registro de cambios

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| 0.1.0 | 21/05/2026 | M.Sc. Edson Terceros | versión inicial; descomposición en microservicios \+ ADR de descomposición |

