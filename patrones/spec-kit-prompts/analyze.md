# analyze — auditor retrospectivo cross-artifact

> Adaptado de `templates/commands/analyze.md` de [github/spec-kit](https://github.com/github/spec-kit).

## Propósito

Identificar inconsistencias, duplicaciones, ambigüedades e items underspecified entre los artefactos disponibles **antes de implementar**. Read-only: produce un report estructurado, no modifica nada. Opcionalmente sugiere remediation que el usuario debe aprobar.

## Cuándo invocar

- Tras refactorizar SPECS.md.
- Cuando ya existe TASKS.md y queremos cross-checking spec ↔ tasks.
- Antes de empezar a implementar como verificación final.
- Después de aplicar clarify para confirmar que las inconsistencias se resolvieron.

## Operating constraints

**STRICTLY READ-ONLY**. NO modificar ningún archivo. Output es un report. Si hay sugerencias de fix, pedir aprobación explícita antes de aplicarlas en una operación separada.

**Project rules authority**: tratar `CLAUDE.md` y `patrones/*.md` como "constitution lite". Si un MUST de CLAUDE.md choca con el spec, es automáticamente CRITICAL — el spec se ajusta, no se diluye el principio.

## Procedimiento

### 1. Cargar artefactos disponibles (progressive disclosure)

Cargar solo el contexto mínimo necesario:

**De SPECS.md (requerido):**
- Overview / context
- Functional Requirements (FR-###)
- Success Criteria / Measurable Outcomes (SC-###)
- User Stories
- Edge Cases (si presentes)
- Assumptions (si presentes)

**De TASKS.md (si existe):**
- Task IDs (T###)
- Descripciones
- Phase grouping (Setup / Foundational / User Story N / Polish)
- Parallel markers `[P]`
- Story tags `[USx]`
- File paths referenciados

**De CLAUDE.md (si existe):**
- Reglas de proyecto, principios MUST/SHOULD.

**De patrones/*.md (si relevante):**
- Patterns que el spec debería estar respetando.

Si SPECS.md no existe: abort con instrucción clara.

### 2. Build semantic models (no incluir raw artefactos en output)

- **Requirements inventory**: para cada FR-### y SC-###, registrar key estable. Usar el ID explícito como primary key. Incluir solo SC items que requieren buildable work (e.g. infraestructura de load testing, security audit tooling); excluir post-launch outcome metrics y business KPIs (e.g. "Reduce support tickets by 50%") — estos no son auditables aquí.
- **User story / action inventory**: acciones discretas con acceptance criteria.
- **Task coverage mapping**: mapear cada task a uno o más requirements/stories (inferencia por keyword o referencia explícita).
- **Project rule set**: extraer de CLAUDE.md los principios MUST/SHOULD.

### 3. Detection passes (high-signal, max 50 findings)

Limitar a 50 findings totales; si hay más, agregar overflow summary.

#### A. Duplication
- Requirements casi-duplicados, posiblemente reescritos en otra parte.
- Marcar el de phrasing inferior para consolidación.

#### B. Ambiguity
- Adjetivos vagos sin métrica: "fast", "scalable", "secure", "intuitive", "robust", "rápido", "ligero".
- Placeholders sin resolver: TODO, TKTK, ???, `<placeholder>`, `[NEEDS CLARIFICATION]`.

#### C. Underspecification
- Requirements con verbo pero sin objeto medible.
- User stories sin acceptance criteria.
- Tasks que referencian archivos/componentes no definidos en spec.

#### D. Project rule alignment
- Cualquier requirement o task element que choque con un MUST de CLAUDE.md o patrones.
- Secciones obligatorias o quality gates ausentes.

#### E. Coverage gaps (solo si hay TASKS.md)
- Requirements con cero tasks asociados.
- Tasks sin requirement / story mapeado.
- Success Criteria que requieren buildable work pero no aparecen en tasks (e.g. "Validar 500 req/s sostenidos" sin task de load testing).

#### F. Inconsistency
- Terminology drift (mismo concepto con nombres distintos en archivos distintos).
- Entities referenciadas en tasks pero ausentes en spec (o viceversa).
- Contradicciones entre orden de tasks (e.g. integration antes de foundational sin nota de dependencia).
- Conflicting requirements (e.g. uno dice Python, otro dice JS para la misma pieza).

### 4. Severity assignment

- **CRITICAL**: viola un MUST de CLAUDE.md, falta artefacto core del spec, o requirement con cero coverage que bloquea baseline functionality.
- **HIGH**: requirement duplicado/conflictivo, ambigüedad en security/performance attribute, acceptance criterion no testeable.
- **MEDIUM**: terminology drift, NF coverage missing, edge case underspecified.
- **LOW**: mejoras estilísticas/wording, redundancia menor sin afectar ejecución.

### 5. Output: Markdown report (no escribir archivos)

```markdown
## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | SPECS.md:L120-134 | Two similar requirements... | Merge phrasing; keep clearer version |
| B3 | Ambiguity | HIGH | SPECS.md §FR-007 | "Fast scoring" sin métrica | Quantify: e.g. "<200ms p95 per source" |
| ...
```

(IDs con prefijo de categoría: A=duplication, B=ambiguity, C=underspecification, D=project-rule, E=coverage, F=inconsistency.)

**Coverage Summary Table** (si hay TASKS.md):
```
| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | ✓ | T012, T015 | |
| FR-007 | ✗ | — | Sin task asociada |
| SC-003 | ✓ | T028 | Coverage indirecta |
```

**Project Rule Issues** (si CLAUDE.md tiene MUSTs):
Listar conflictos individuales.

**Unmapped Tasks** (si hay):
Tasks sin requirement claro.

**Metrics**:
- Total Requirements: N
- Total Tasks: M
- Coverage % (requirements con ≥1 task): X%
- Ambiguity Count: ...
- Duplication Count: ...
- Critical Issues Count: ...

### 6. Next Actions

- Si CRITICAL existe: recomendar resolverlas antes de implementar.
- Si solo LOW/MEDIUM: usuario puede proceder, pero con sugerencias de mejora.
- Sugerencias concretas: e.g. "Run clarify para FR-007", "Refactor SPECS §3 para resolver terminology drift", "Add task para SC-003 load testing".

### 7. Offer remediation

Preguntar al usuario: "¿Quieres que sugiera ediciones concretas para los top N issues?"

NO aplicarlas automáticamente. Solo si el usuario aprueba, generar diff preview en una operación separada.

## Operating principles

### Context efficiency
- Tokens minimos high-signal — findings actionables, no documentación exhaustiva.
- Progressive disclosure — cargar artefactos incrementalmente, no dump entero.
- Output token-efficient — limitar findings table a 50 rows; resumir overflow.
- Determinístico — mismas entradas → mismos IDs y counts.

### Analysis guidelines
- NUNCA modificar archivos.
- NUNCA hallucinar secciones inexistentes (si falta, reportarlo).
- Project rule violations son siempre CRITICAL.
- Citar instances específicas (línea, sección), no generic patterns.
- Si zero issues: emit success report con coverage stats, no inventar problemas.
