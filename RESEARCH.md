# Research: skills de research existentes para Claude Code

Mapeo del ecosistema vía WebSearch + WebFetch. Hecho el 2026-05-06.

---

## Categorías

### A. Investigación estructurada por catálogo de items
Outline (items × fields) → un agente paralelo por item → reporte tabular.
- **Weizhena/Deep-Research-skills** — 634★. Referencia inicial de este proyecto. 5 fases con human-in-the-loop. YAML para `outline.yaml` + `fields.yaml`. Comandos `/research`, `/research-add-items`, `/research-add-fields`, `/research-deep`, `/research-report`.

### B. Pipeline largo con validación de fuentes y citas
Multi-fase con scoring de credibilidad y validadores anti-alucinación.
- **199-biotechnologies/claude-deep-research-skill** — 615★. 8 fases (Scope → Plan → Retrieve → Triangulate → Outline → Synthesize → Critique → Refine → Package). `source_evaluator.py` puntúa autoridad/recencia/citas; `validate_report.py` (9 chequeos) y `verify_citations.py` (DOI/URL). 4 modos (Quick/Standard/Deep/UltraDeep) con red-teaming multi-persona. Output Markdown / HTML estilo McKinsey / PDF (WeasyPrint). Búsqueda vía `search-cli` (Brave + Serper + Exa + Jina + Firecrawl).
- **Web Research Agent** (mcpmarket) — protocolo que obliga a documentar URL, fecha y nivel de incertidumbre por afirmación. Más enfocado en disciplina que en tooling.

### C. Pipeline académico de publicación
Cadena research → write → review → revise → finalize.
- **Imbad0202/academic-research-skills** — 4.7k★. 4 skills encadenados (deep-research v2.8 con 13 agentes, academic-paper v3.0 con 12 agentes, reviewer v1.8 con 7 agentes, pipeline v3.7 con 10 stages). Citas APA/Chicago/MLA/IEEE/Vancouver. Verificación vía Semantic Scholar API. Gates de bloqueo de integridad. Pandoc/tectonic para LaTeX/PDF.

### D. Investigación social en tiempo real
Reddit + X + YouTube + TikTok + HN + Polymarket sintetizados.
- **mvanhorn/last30days-skill** — ya instalado en el sistema. Multi-plataforma, ranking por engagement, transcripts de YouTube, citas con @handles y r/sub. Mejor para "qué dice la gente AHORA" sobre productos, personas, eventos.

### E. Plan-first con sub-agentes y memoria cross-thread
Decomposición conversacional, menos rígida que A/B.
- **openclaw/deep-research** — citado por skillsdirectory.com como skill plan-first con sub-agentes especializados y memoria persistente entre conversaciones (comando `/deepsearch`). **Verificación 2026-05-06**: tanto `github.com/openclaw/deep-research` como el path del monorepo `github.com/openclaw/skills/blob/main/skills/seyhunak/deep-research/SKILL.md` devuelven 404. No hay fuente pública verificable; categoría sin ejemplo público sólido confirmado.

### F. Engineering de research ML — descartado
- **Orchestra-Research/AI-Research-SKILLs** — 7.9k★ pero son 98 skills para entrenamiento/inferencia (Megatron, vLLM, Flash Attention, etc.). No es web research; aparece en búsquedas pero no aplica al caso.

---

## Top 2 (los que merece la pena estudiar a fondo)

1. **Weizhena/Deep-Research-skills** — la referencia inicial. Patrón outline + parallel-agents-per-item + report. Limpio, simple, bien escrito. Bueno para casos comparativos (comparar N opciones con M atributos).

2. **199-biotechnologies/claude-deep-research-skill** — la pieza con mejor ingeniería de calidad del ecosistema. Source scoring, citation validators, modos de profundidad, output multi-formato, persistencia en disco que sobrevive compactación. Es la referencia para "cómo se hace research con rigor".

A representa el patrón estructurado (outline rígido + parallel agents); B el de calidad-y-citas (rigor con source scoring + validators). Con `/last30days` ya cubierto para social, estas dos cubren los enfoques principales con fuente pública verificable. La categoría E (plan-first conversacional) se queda sin ejemplo público sólido — ver nota en categoría arriba.

---

## Patrón ortogonal: planificación pre-research

Independientemente de qué skill base se elija, un patrón aplicable encima es **planificación pre-research**: escribir un plan estructurado de 7 decisiones (perfil de la información, dimensiones, caminos indirectos, sesgos, criterio de parada, fuentes obligatorias, queries) y confirmarlo con el usuario antes de ejecutar la primera query. Detalle en [`patrones/pre-research-planning.md`](./patrones/pre-research-planning.md). Útil para evitar el sesgo de "ya lo tengo claro" en cualquier research con espacio de búsqueda amplio.

---

## Fuentes

- https://github.com/Weizhena/Deep-Research-skills
- https://github.com/199-biotechnologies/claude-deep-research-skill
- https://github.com/Imbad0202/academic-research-skills
- https://github.com/Orchestra-Research/AI-research-SKILLs
- https://github.com/mvanhorn/last30days-skill
- https://www.skillsdirectory.com/skills/openclaw-deep-research
- https://mcpmarket.com/tools/skills/web-research-agent-3
- https://claudefa.st/blog/tools/skills/best-claude-code-skills
- https://www.firecrawl.dev/blog/best-claude-code-skills
