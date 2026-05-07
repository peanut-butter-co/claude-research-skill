# clarify — crítico proactivo de specs

> Adaptado de `templates/commands/clarify.md` de [github/spec-kit](https://github.com/github/spec-kit).

## Propósito

Detectar y reducir ambigüedad en el spec **antes** de implementar. Hace un escaneo taxonómico, identifica las áreas underspecified de mayor impacto, y resuelve hasta 5 con preguntas dirigidas. Cada respuesta se integra en el spec.

## Cuándo invocar

- Antes de cerrar una sección importante de SPECS.md.
- Antes de implementar una user story o un componente.
- Después de un cambio grande para detectar ambigüedades nuevas.

NO usar para preferencias estilísticas o detalles de implementación que mejor pertenecen al plan técnico.

## Procedimiento

### 1. Cargar artefacto objetivo

Leer el archivo (por defecto `SPECS.md`). Si no existe: parar y avisar.

### 2. Escaneo taxonómico de ambigüedad

Para cada categoría, marcar status: **Clear / Partial / Missing**. No mostrar el mapa raw a menos que no haya preguntas que hacer.

**Functional scope & behavior**
- Core user goals & success criteria
- Out-of-scope declarations explícitas
- Roles / personas diferenciados

**Domain & data model**
- Entities, atributos, relaciones
- Identidad y reglas de unicidad
- Lifecycle / state transitions
- Asunciones de volumen / escala

**Interaction & UX flow**
- User journeys críticos
- Error / empty / loading states
- Accesibilidad / localización

**Non-functional quality attributes**
- Performance (latency, throughput)
- Scalability (horizontal/vertical, límites)
- Reliability & availability
- Observability (logging, metrics, tracing)
- Security & privacy (authN/Z, threat model)
- Compliance / regulatorio

**Integration & external dependencies**
- Servicios/APIs externos y modos de fallo
- Formatos import/export
- Versionado de protocolos

**Edge cases & failure handling**
- Escenarios negativos
- Rate limiting / throttling
- Conflict resolution (ediciones concurrentes)

**Constraints & tradeoffs**
- Restricciones técnicas (lenguaje, storage, hosting)
- Tradeoffs explícitos / alternativas rechazadas

**Terminology & consistency**
- Términos canónicos del glosario
- Sinónimos a evitar / términos deprecados

**Completion signals**
- Acceptance criteria testeables
- Definition of Done medible

**Misc / placeholders**
- TODO / TKTK / `[NEEDS CLARIFICATION]` sin resolver
- Adjetivos vagos sin cuantificar ("robusto", "intuitivo", "rápido")

### 3. Generar cola priorizada de preguntas (máximo 5)

Reglas:
- Solo si la respuesta **materialmente cambia** arquitectura, modelo de datos, decomposición de tareas, diseño de tests, comportamiento UX, operatividad o compliance.
- Cobertura de categorías balanceada: priorizar las de mayor impacto (security/scope) sobre dos low-impact.
- Excluir preguntas ya respondidas, preferencias estilísticas, o detalles de implementación.
- Si quedan más de 5 categorías sin resolver: top 5 por heurística (Impact × Uncertainty).

### 4. Loop de preguntas (una a una)

**Para multiple-choice (2-5 opciones mutuamente excluyentes):**
1. Analizar todas las opciones y determinar la **recomendada** según best practices, reducción de riesgo, y alineamiento con el spec/CLAUDE.md.
2. Presentar la recomendación arriba: `**Recommended:** Option [X] - <razonamiento 1-2 frases>`
3. Tabla:
   ```
   | Option | Description |
   |--------|-------------|
   | A | ... |
   | B | ... |
   | Short | Provide a different short answer (<=5 words) |
   ```
4. Cierre: `Responde con la letra, "yes" para aceptar la recomendación, o tu propia respuesta corta.`

**Para short-answer (sin opciones discretas significativas):**
1. **Suggested:** `<respuesta propuesta>` con razonamiento breve.
2. `Format: Short answer (<=5 words). "yes" para aceptar la sugerencia, o tu respuesta.`

**Tras respuesta del usuario:**
- "yes" / "recommended" / "suggested" → usar la recomendación.
- Si ambigua → pedir disambiguación (no avanza el contador).
- Validar y guardar en memoria de trabajo. Avanzar.

### 5. Stop conditions

- Todas las ambigüedades críticas resueltas (los items pendientes de la cola dejan de ser necesarios).
- Usuario señala fin: "stop", "done", "proceed", "no more".
- Se llega a 5 preguntas asked.

Nunca revelar las preguntas futuras antes de tiempo.
Si no hay preguntas válidas al inicio: reportar "No critical ambiguities detected" y sugerir avanzar.

### 6. Integrar cada respuesta en el spec

Tras aceptar cada respuesta:

1. Asegurar sección `## Clarifications` en el spec (crear si no existe, justo después de la sección de contexto/overview).
2. Bajo ella, asegurar subheader `### Session YYYY-MM-DD`.
3. Append bullet: `- Q: <pregunta> → A: <respuesta final>`
4. Aplicar inmediatamente al área correspondiente del spec:
   - Ambigüedad funcional → update/add bullet en Functional Requirements.
   - Distinción de actor / interacción → update User Stories.
   - Shape de datos / entities → update Data Model con campos/types/relaciones.
   - Restricción non-functional → add/modify metric en Success Criteria > Measurable Outcomes.
   - Edge case / negative flow → add bullet en Edge Cases / Error Handling.
   - Conflicto de terminología → normalizar término a través del spec; conservar el original solo con `(formerly referred to as "X")` una vez si necesario.
5. Si la clarificación invalida una afirmación previa: reemplazarla, no duplicar.
6. Guardar el spec tras cada integración.
7. Preservar formato: no reordenar secciones no relacionadas, mantener jerarquía de headings.

### 7. Validación tras cada write y final

- Sección Clarifications: exactly one bullet por respuesta accepted, sin duplicados.
- Total preguntas asked ≤ 5.
- Las secciones updated no contienen los placeholders vagos que la respuesta debía resolver.
- Sin contradicciones residuales (escanear que las alternativas ahora-inválidas se eliminaron).
- Markdown estructura válida; nuevos headings permitidos: `## Clarifications`, `### Session YYYY-MM-DD`.
- Terminología consistente.

### 8. Reporte final

- Número de preguntas asked & answered.
- Path al spec actualizado.
- Secciones tocadas (lista).
- **Coverage summary table**:
  ```
  | Category | Status |
  |---|---|
  | Functional scope | Resolved / Deferred / Clear / Outstanding |
  | Domain model | ... |
  | ... | ... |
  ```
- Si quedan Outstanding o Deferred: recomendar si proceder o re-correr clarify post-cambios.
- Sugerir comando siguiente.

## Behavior rules

- Si no hay ambigüedades materiales: "No critical ambiguities detected worth formal clarification" + sugerir avanzar.
- Si SPECS.md no existe: instruir al usuario que primero exista el spec; no crearlo aquí.
- Nunca exceder 5 preguntas accepted (retries de la misma pregunta no cuentan).
- Evitar preguntas especulativas de tech stack a menos que su ausencia bloquee claridad funcional.
- Respetar terminación temprana ("stop", "done", "proceed").
