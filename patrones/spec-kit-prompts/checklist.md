# checklist — generador de "Unit Tests for English"

> Adaptado de `templates/commands/checklist.md` de [github/spec-kit](https://github.com/github/spec-kit).

## Concepto crítico

**Los checklists testean los REQUIREMENTS, NO la implementación.**

Si SPECS.md es código en inglés, el checklist es su test suite. Validamos que los requirements estén bien escritos — completos, claros, sin ambigüedad, listos para implementar — NO si la implementación funciona.

❌ NO hacer:
- "Verificar que el botón de delete funciona"
- "Test que la API devuelve 200"
- "Confirmar que el scoring filtra Tier D"

✅ SÍ hacer:
- "¿Están definidos los requirements para todos los failure modes del scoring? `[Completeness]`"
- "¿Está cuantificado 'cross-citation bonus' con threshold específico? `[Clarity, Spec §Scoring]`"
- "¿Son consistentes las reglas de tier-A entre source-tiers.yaml y SPECS §Scoring? `[Consistency]`"

## Cuándo invocar

- Para validar áreas críticas del spec por dominio (ej: scoring, learning system, optional integrations, last30days integration).
- Antes de cerrar una sección importante del spec.
- Como gate previo a implementar un componente.

Múltiples checklists conviven (ej: `scoring.md`, `learning.md`, `integrations.md`); cada uno testea una dimensión.

## Procedimiento

### 1. Clarify intent (max 3 preguntas iniciales, dinámicas)

Generar hasta 3 preguntas a partir de los signals del prompt del usuario + spec. Solo si materialmente cambian el contenido del checklist. Skip individualmente si ya inequívoco en `$ARGUMENTS`.

Algoritmo:
1. Extraer signals: keywords del dominio (auth, latency, scoring), risk indicators ("crítico", "must", "compliance"), audience hints ("review", "QA"), entregables explícitos ("a11y", "rollback").
2. Cluster en focus areas (max 4) ranked por relevancia.
3. Detectar dimensiones missing: scope, depth/rigor, risk emphasis, exclusion boundaries, measurable acceptance criteria.
4. Formular preguntas de archetypes:
   - **Scope refinement** — "¿Incluir integration touchpoints con X y Y, o limitarnos a correctness local?"
   - **Risk prioritization** — "¿Cuáles de estas áreas de riesgo deben tener mandatory gates?"
   - **Depth calibration** — "¿Lightweight pre-commit sanity, o formal release gate?"
   - **Audience framing** — "¿Solo para el autor o para peers en PR review?"
   - **Boundary exclusion** — "¿Excluir performance tuning explícitamente esta ronda?"
   - **Scenario class gap** — "No detecté recovery flows; ¿están en scope rollback / partial failure?"

Format:
- Si presento opciones: tabla compacta con `Option | Candidate | Why It Matters`.
- Max A-E. Free-form si es más claro.
- Etiquetar Q1/Q2/Q3.

Tras respuestas, si quedan ≥2 scenario classes (Alternate / Exception / Recovery / NF) sin clarificar, puedo añadir hasta 2 follow-ups (Q4/Q5) con justificación de una línea. Nunca exceder 5 totales. Skip escalation si el usuario declina más.

Defaults si interacción imposible:
- Depth: Standard
- Audience: Reviewer (PR) si código; Author si no
- Focus: top 2 relevance clusters

### 2. Cargar contexto

- SPECS.md (sección relevante al dominio).
- patrones/*.md si aplica.
- TASKS.md si existe.

Strategy:
- Cargar solo porciones relevantes al focus area; no full-file dumps.
- Resumir secciones largas en bullets concisos de scenario/requirement.
- Progressive disclosure — fetch adicional solo si gaps detectados.

### 3. Generar checklist

**Path**: `checklists/<domain>.md` (ej: `scoring.md`, `learning.md`).
- Si NO existe: crear, items desde CHK001.
- Si existe: append, continuar IDs desde el último (e.g. último CHK015 → empezar en CHK016).
- Nunca borrar contenido existente; siempre preservar y append.

**Estructura**:
```markdown
# <Domain> Requirements Quality Checklist

**Purpose**: Validate <domain> requirements for completeness, clarity, consistency, measurability.
**Created**: YYYY-MM-DD
**Spec**: SPECS.md §<section>

## Requirement Completeness
- [ ] CHK001 ¿...? [Completeness, Spec §X]
- [ ] CHK002 ¿...? [Gap]

## Requirement Clarity
- [ ] CHK003 ¿...? [Clarity, Ambiguity, Spec §Y]

## Requirement Consistency
...

## Acceptance Criteria Quality
...

## Scenario Coverage
...

## Edge Case Coverage
...

## Non-Functional Requirements
...

## Dependencies & Assumptions
...

## Ambiguities & Conflicts
...

## Notes
- Chequear: `[x]`
- Comentarios inline si encuentras issues
- Referencias a spec section / patrones cuando aplique
```

Solo incluir las categorías que aplican al dominio.

### 4. Cómo escribir cada item

**CORE PRINCIPLE — Test the requirements, not the implementation.**

Cada item debe evaluar los REQUIREMENTS por:
- **Completeness** — ¿están todos los requirements necesarios?
- **Clarity** — ¿son inequívocos y específicos?
- **Consistency** — ¿alinean entre sí?
- **Measurability** — ¿se pueden verificar objetivamente?
- **Coverage** — ¿abordan todos los scenarios / edge cases?

**Patrón de item**:
- Pregunta sobre la calidad del requirement.
- Foco en lo escrito (o no escrito) en el spec.
- Bracket de quality dimension: `[Completeness]`, `[Clarity]`, `[Consistency]`, `[Measurability]`, `[Coverage]`.
- Reference de spec: `[Spec §X.Y]` cuando aplica.
- Marker de tipo: `[Gap]` (falta), `[Ambiguity]` (vago), `[Conflict]` (contradice), `[Assumption]` (no validada).

**Mínimo 80% de items con traceability reference.**

### 5. Ejemplos por quality dimension

**Completeness**
- "¿Están definidos error handling requirements para todos los API failure modes? `[Gap]`"
- "¿Están especificados accessibility requirements para todos los interactive elements? `[Completeness]`"
- "¿Están definidos requirements de mobile breakpoints para responsive layouts? `[Gap]`"

**Clarity**
- "¿Está cuantificado 'fast loading' con timing thresholds específicos? `[Clarity, Spec §NFR-2]`"
- "¿Están definidos los criterios de selección de 'related episodes' explícitamente? `[Clarity, Spec §FR-5]`"
- "¿Está definido 'prominent' con propiedades visuales medibles? `[Ambiguity, Spec §FR-4]`"

**Consistency**
- "¿Alinean los navigation requirements en todas las páginas? `[Consistency, Spec §FR-10]`"
- "¿Son consistentes los requirements del componente Card entre landing y detail page? `[Consistency]`"

**Coverage**
- "¿Están definidos requirements para zero-state scenarios (sin episodes)? `[Coverage, Edge Case]`"
- "¿Están abordados scenarios de interacción concurrent? `[Coverage, Gap]`"
- "¿Están especificados requirements para partial data loading failures? `[Coverage, Exception Flow]`"

**Measurability**
- "¿Son measurable/testable los requirements de visual hierarchy? `[Acceptance Criteria, Spec §FR-1]`"
- "¿Se puede verificar objetivamente 'balanced visual weight'? `[Measurability, Spec §FR-2]`"

**Scenario Classification & Coverage**
- Por cada clase (Primary, Alternate, Exception/Error, Recovery, Non-Functional): "¿Son completos, claros y consistentes los <scenario type> requirements?"
- Si una clase falta: "¿Son los <scenario type> requirements intencionadamente excluidos o missing? `[Gap]`"
- Si hay state mutation: "¿Están definidos rollback requirements para fallos de migración? `[Gap]`"

### 6. Reglas

🚫 **PROHIBIDO** (eso lo convierte en implementation test, no requirements test):
- Items que empiezan por "Verificar", "Confirmar", "Test", "Check" + comportamiento del sistema.
- Referencias a ejecución de código, acciones de usuario, system behavior.
- "Funciona correctamente", "renderiza", "navega".
- Test cases, test plans, QA procedures.
- Detalles de implementación (frameworks, APIs, algorithms).

✅ **REQUERIDO**:
- "¿Están definidos / especificados / documentados los <requirement type> para <scenario>?"
- "¿Está cuantificado / clarificado <término vago> con criterio específico?"
- "¿Son consistentes los requirements entre <sección A> y <sección B>?"
- "¿Se puede medir objetivamente <requirement>?"
- "¿Están abordados <edge cases / scenarios> en los requirements?"
- "¿Define el spec <aspecto missing>?"

### 7. Content consolidation

- Soft cap: si los candidate items > 40, priorizar por risk/impact.
- Merge near-duplicates que chequean el mismo aspecto.
- Si hay >5 edge cases low-impact: merge en uno: "¿Están abordados los edge cases X, Y, Z en los requirements? `[Coverage]`"

### 8. Reporte

- Path completo al checklist generado.
- Item count.
- Si era new file o append.
- Focus areas seleccionados.
- Depth level.
- Actor/timing.
- User-specified must-haves incorporados.

## Anti-examples (qué NO hacer)

❌ **WRONG** — testea implementación:
```markdown
- [ ] CHK001 - Verificar que las fuentes Tier D se filtran del reporte [Spec §Scoring]
- [ ] CHK002 - Test que el cross-citation bonus se aplica correctamente
- [ ] CHK003 - Confirmar que el validador URL marca las rotas
```

✅ **CORRECT** — testea requirements:
```markdown
- [ ] CHK001 - ¿Están especificadas las condiciones bajo las cuales Tier D entra al reporte? [Completeness, Spec §Scoring]
- [ ] CHK002 - ¿Está cuantificado el cross-citation bonus con threshold y peso explícitos? [Clarity, Spec §Scoring]
- [ ] CHK003 - ¿Está definido qué hace el reporte cuando una URL falla validación (skip, mark, fail)? [Edge Case, Gap]
- [ ] CHK004 - ¿Son consistentes los criterios de Tier entre source-tiers.yaml y SPECS §Scoring? [Consistency, Spec §Scoring]
```

**Diferencias clave**:
- Wrong: tests si el sistema funciona correctamente.
- Correct: tests si los requirements están bien escritos.
- Wrong: "¿Hace X?"
- Correct: "¿Está X claramente especificado?"
