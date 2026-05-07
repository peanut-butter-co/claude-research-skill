from __future__ import annotations

import csv
import io
import re

UNCERTAIN_MARKER = "[uncertain]"
BROKEN_URL_MARKER = "[source unavailable - URL broken]"
TIER_ORDER = ["A", "B", "C", "D"]
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC_RE = re.compile(r"\*([^*]+)\*|_([^_]+)_")


def build_report(
    outline: dict,
    item_jsons: list[dict],
    fields_yaml: dict | None = None,
    url_validation: dict[str, dict] | None = None,
) -> dict:
    mode = outline.get("mode", "comparative")
    url_validation = url_validation or {}
    if mode == "narrative":
        report_md, gap_count, broken = _build_narrative(outline, item_jsons, url_validation)
        report_csv = ""
    else:
        report_md, gap_count, broken, report_csv = _build_comparative(
            outline, item_jsons, fields_yaml or {}, url_validation
        )
    return {
        "report_md": report_md,
        "report_csv": report_csv,
        "gap_count": gap_count,
        "broken_url_count": broken,
    }


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _flatten_fields(fields_yaml: dict) -> list[str]:
    out: list[str] = []
    categories = fields_yaml.get("categories", {}) if isinstance(fields_yaml, dict) else {}
    for _name, fields in categories.items():
        for f in fields or []:
            out.append(f)
    return out


def _strip_markdown(text: str) -> str:
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _MD_BOLD_RE.sub(r"\1", text)
    text = _MD_ITALIC_RE.sub(lambda m: m.group(1) or m.group(2), text)
    return text.strip()


def _is_broken(url: str, url_validation: dict[str, dict]) -> bool:
    if not url_validation:
        return False
    entry = url_validation.get(url)
    if entry is None:
        return False
    return entry.get("ok") is False


def _inline_citation(source: dict) -> str:
    title = source.get("title") or source.get("url", "source")
    tier = source.get("tier", "Unknown")
    url = source.get("url", "")
    return f"[{title} • Tier {tier}]({url})"


def _toc(sections: list[str]) -> str:
    lines = ["## Table of contents", ""]
    for s in sections:
        lines.append(f"- [{s}](#{_slugify(s)})")
    lines.append("")
    return "\n".join(lines)


def _format_field_value(field: dict, url_validation: dict[str, dict]) -> tuple[str, bool, bool]:
    raw = field.get("value")
    sources = field.get("sources") or []
    if raw is None or raw == "" or raw == UNCERTAIN_MARKER:
        return UNCERTAIN_MARKER, True, False
    has_broken = False
    citations: list[str] = []
    for src in sources:
        url = src.get("url", "")
        if _is_broken(url, url_validation):
            has_broken = True
            continue
        citations.append(_inline_citation(src))
    text = str(raw)
    if has_broken and not citations:
        return BROKEN_URL_MARKER, False, True
    if citations:
        text = f"{text} {' '.join(citations)}"
    if has_broken:
        text = f"{text} {BROKEN_URL_MARKER}"
    return text, False, has_broken


def _comparison_table(
    items: list[str],
    fields: list[str],
    item_jsons: list[dict],
    url_validation: dict[str, dict],
) -> str:
    by_item = {j.get("item"): j for j in item_jsons if "item" in j}
    header = "| Item | " + " | ".join(fields) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(fields)) + " |"
    rows = [header, sep]
    for item in items:
        j = by_item.get(item)
        if j is None or j.get("pruned"):
            cells = [UNCERTAIN_MARKER] * len(fields)
        else:
            jfields = j.get("fields", {}) or {}
            cells = []
            for f in fields:
                fdata = jfields.get(f)
                if not fdata:
                    cells.append(UNCERTAIN_MARKER)
                    continue
                text, _, _ = _format_field_value(fdata, url_validation)
                cells.append(text.replace("|", "\\|").replace("\n", " "))
        rows.append(f"| {item} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _per_item_section(item: str, j: dict | None, fields: list[str], url_validation: dict[str, dict]) -> str:
    lines = [f"## {item}", ""]
    if j is None:
        lines.append("No evidence found.")
        lines.append("")
        return "\n".join(lines)
    if j.get("pruned"):
        reason = j.get("prune_reason") or "agent pruned this item after triple reformulation"
        lines.append(f"No evidence found ({reason}).")
        lines.append("")
        return "\n".join(lines)
    jfields = j.get("fields", {}) or {}
    for f in fields:
        fdata = jfields.get(f)
        lines.append(f"### {f}")
        if not fdata:
            lines.append(UNCERTAIN_MARKER)
        else:
            text, _, _ = _format_field_value(fdata, url_validation)
            lines.append(text)
        lines.append("")
    if j.get("budget_exhausted"):
        lines.append("_Note: agent stopped due to budget exhaustion; remaining fields are uncertain._")
        lines.append("")
    return "\n".join(lines)


def _collect_all_sources(item_jsons: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for j in item_jsons:
        fields = j.get("fields", {}) or {}
        for fdata in fields.values():
            for src in (fdata.get("sources") or []) if isinstance(fdata, dict) else []:
                url = src.get("url", "")
                key = url or id(src)
                if key in seen:
                    continue
                seen.add(key)
                out.append(src)
    return out


def _sources_note(all_sources: list[dict], url_validation: dict[str, dict]) -> str:
    by_tier: dict[str, list[dict]] = {t: [] for t in TIER_ORDER}
    unclassified: list[dict] = []
    extraction_failures: list[dict] = []
    broken: list[dict] = []
    for src in all_sources:
        if src.get("extraction_failed"):
            extraction_failures.append(src)
            continue
        url = src.get("url", "")
        if _is_broken(url, url_validation):
            broken.append(src)
        tier = src.get("tier", "Unknown")
        if tier in by_tier:
            by_tier[tier].append(src)
        else:
            unclassified.append(src)

    lines = ["## Sources note", ""]
    for t in TIER_ORDER:
        bucket = by_tier[t]
        if not bucket:
            continue
        lines.append(f"### Tier {t}")
        for src in bucket:
            cite = _inline_citation(src)
            suffix = ""
            if _is_broken(src.get("url", ""), url_validation):
                suffix = f" {BROKEN_URL_MARKER}"
            lines.append(f"- {cite}{suffix}")
        lines.append("")
    if unclassified:
        lines.append("### Unclassified domains")
        for src in unclassified:
            lines.append(f"- {_inline_citation(src)}")
        lines.append("")
    if extraction_failures:
        lines.append("### Extraction failures")
        for src in extraction_failures:
            url = src.get("url", "")
            methods = src.get("methods_attempted") or []
            failure = src.get("failure_mode") or "all paths failed"
            mtxt = f" methods: {', '.join(methods)};" if methods else ""
            lines.append(f"- {url} —{mtxt} {failure}")
        lines.append("")
    if broken:
        lines.append("### Broken URLs")
        for src in broken:
            lines.append(f"- {src.get('url', '')} {BROKEN_URL_MARKER}")
        lines.append("")
    return "\n".join(lines)


def _disagreements_from_jsons(item_jsons: list[dict]) -> list[dict]:
    disagreements: list[dict] = []
    for j in item_jsons:
        item = j.get("item") or j.get("subquery") or ""
        fields = j.get("fields", {}) or {}
        for fname, fdata in fields.items():
            if not isinstance(fdata, dict):
                continue
            sources = fdata.get("sources") or []
            tier_a = [s for s in sources if s.get("tier") == "A"]
            claims_to_sources: dict[str, list[dict]] = {}
            for s in tier_a:
                claim = s.get("claim")
                if claim is None:
                    continue
                claims_to_sources.setdefault(claim, []).append(s)
            if len(claims_to_sources) >= 2:
                disagreements.append({
                    "scope": item,
                    "field": fname,
                    "claims": claims_to_sources,
                    "resolution": fdata.get("disagreement_resolution"),
                })
                continue
            conflicting = [s for s in sources if s.get("conflict")]
            if conflicting:
                grouped: dict[str, list[dict]] = {}
                for s in conflicting:
                    claim = s.get("claim", "(unspecified)")
                    grouped.setdefault(claim, []).append(s)
                if len(grouped) >= 2:
                    disagreements.append({
                        "scope": item,
                        "field": fname,
                        "claims": grouped,
                        "resolution": fdata.get("disagreement_resolution"),
                    })
    return disagreements


def _disagreements_section(disagreements: list[dict]) -> str:
    if not disagreements:
        return ""
    lines = ["## Disagreements", ""]
    for d in disagreements:
        lines.append(f"### {d['scope']} — {d['field']}")
        for claim, srcs in d["claims"].items():
            cites = ", ".join(_inline_citation(s) for s in srcs)
            lines.append(f"- Claim: {claim} — {cites}")
        if d.get("resolution"):
            lines.append(f"- Resolution: {d['resolution']}")
        lines.append("")
    return "\n".join(lines)


def _gaps_list(item_jsons: list[dict], expected_fields: list[str] | None = None) -> tuple[str, int]:
    gaps: list[str] = []
    for j in item_jsons:
        scope = j.get("item") or j.get("subquery") or "(unknown)"
        if j.get("pruned"):
            gaps.append(f"- {scope}: entire scope pruned (no evidence found)")
            continue
        budget_note = " [budget exhausted]" if j.get("budget_exhausted") else ""
        declared = j.get("uncertain") or []
        for u in declared:
            gaps.append(f"- {scope}: {u}{budget_note}")
        fields = j.get("fields", {}) or {}
        if expected_fields is not None:
            for f in expected_fields:
                fdata = fields.get(f)
                if fdata is None:
                    if f not in declared:
                        gaps.append(f"- {scope}: {f}{budget_note}")
                    continue
                if isinstance(fdata, dict):
                    val = fdata.get("value")
                    if val is None or val == "" or val == UNCERTAIN_MARKER:
                        if f not in declared:
                            gaps.append(f"- {scope}: {f}{budget_note}")
        else:
            for fname, fdata in fields.items():
                if isinstance(fdata, dict):
                    val = fdata.get("value")
                    if val is None or val == "" or val == UNCERTAIN_MARKER:
                        if fname not in declared:
                            gaps.append(f"- {scope}: {fname}{budget_note}")
    if not gaps:
        return "## Gaps\n\nNone.\n", 0
    return "## Gaps\n\n" + "\n".join(gaps) + "\n", len(gaps)


def _count_broken(item_jsons: list[dict], url_validation: dict[str, dict]) -> int:
    if not url_validation:
        return 0
    seen: set[str] = set()
    for j in item_jsons:
        fields = j.get("fields", {}) or {}
        for fdata in fields.values():
            if not isinstance(fdata, dict):
                continue
            for src in fdata.get("sources") or []:
                url = src.get("url", "")
                if url and _is_broken(url, url_validation):
                    seen.add(url)
    return len(seen)


def _build_csv(items: list[str], fields: list[str], item_jsons: list[dict]) -> str:
    by_item = {j.get("item"): j for j in item_jsons if "item" in j}
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["item", *fields])
    for item in items:
        j = by_item.get(item)
        row = [item]
        if j is None or j.get("pruned"):
            row.extend([UNCERTAIN_MARKER] * len(fields))
        else:
            jfields = j.get("fields", {}) or {}
            for f in fields:
                fdata = jfields.get(f)
                if not fdata or not isinstance(fdata, dict):
                    row.append(UNCERTAIN_MARKER)
                    continue
                val = fdata.get("value")
                if val is None or val == "" or val == UNCERTAIN_MARKER:
                    row.append(UNCERTAIN_MARKER)
                else:
                    row.append(_strip_markdown(str(val)))
        writer.writerow(row)
    return buf.getvalue()


def _build_comparative(
    outline: dict,
    item_jsons: list[dict],
    fields_yaml: dict,
    url_validation: dict[str, dict],
) -> tuple[str, int, int, str]:
    items = list(outline.get("items") or [])
    fields = _flatten_fields(fields_yaml)
    topic = outline.get("topic", "Research report")

    if not item_jsons:
        md = f"# {topic}\n\nNo evidence found.\n"
        return md, 0, 0, _build_csv(items, fields, [])

    by_item = {j.get("item"): j for j in item_jsons if "item" in j}
    sections = [*items, "Disagreements", "Gaps", "Sources note"]
    parts = [f"# {topic}", "", _toc(sections), "## Comparison", "",
             _comparison_table(items, fields, item_jsons, url_validation), ""]
    for item in items:
        parts.append(_per_item_section(item, by_item.get(item), fields, url_validation))
    disagreements = _disagreements_from_jsons(item_jsons)
    dis_section = _disagreements_section(disagreements)
    if dis_section:
        parts.append(dis_section)
    else:
        parts.append("## Disagreements\n\nNone detected.\n")
    gaps_md, gap_count = _gaps_list(item_jsons, expected_fields=fields)
    parts.append(gaps_md)
    parts.append(_sources_note(_collect_all_sources(item_jsons), url_validation))
    md = "\n".join(parts)
    broken = _count_broken(item_jsons, url_validation)
    return md, gap_count, broken, _build_csv(items, fields, item_jsons)


def _build_narrative(
    outline: dict,
    item_jsons: list[dict],
    url_validation: dict[str, dict],
) -> tuple[str, int, int]:
    subqueries = list(outline.get("subqueries") or [])
    topic = outline.get("topic", "Research report")
    if not item_jsons:
        return f"# {topic}\n\nNo evidence found.\n", 0, 0

    by_sub = {j.get("subquery"): j for j in item_jsons if "subquery" in j}
    sections = [*subqueries, "Cross-cutting findings", "Disagreements", "Gaps", "Sources note"]
    parts = [f"# {topic}", "", _toc(sections)]
    for sub in subqueries:
        parts.append(_narrative_section(sub, by_sub.get(sub), url_validation))
    parts.append(_cross_cutting(item_jsons))
    disagreements = _disagreements_from_jsons(item_jsons)
    dis_section = _disagreements_section(disagreements)
    if dis_section:
        parts.append(dis_section)
    else:
        parts.append("## Disagreements\n\nNone detected.\n")
    gaps_md, gap_count = _gaps_list(item_jsons)
    parts.append(gaps_md)
    parts.append(_sources_note(_collect_all_sources(item_jsons), url_validation))
    md = "\n".join(parts)
    broken = _count_broken(item_jsons, url_validation)
    return md, gap_count, broken


def _narrative_section(sub: str, j: dict | None, url_validation: dict[str, dict]) -> str:
    lines = [f"## {sub}", ""]
    if j is None:
        lines.append("No evidence found.")
        lines.append("")
        return "\n".join(lines)
    if j.get("pruned"):
        reason = j.get("prune_reason") or "agent pruned this subquery after triple reformulation"
        lines.append(f"No evidence found ({reason}).")
        lines.append("")
        return "\n".join(lines)
    fields = j.get("fields", {}) or {}
    evidence = j.get("evidence")
    if evidence and not fields:
        text = str(evidence)
        sources = j.get("sources") or []
        cites = " ".join(_inline_citation(s) for s in sources if not _is_broken(s.get("url", ""), url_validation))
        lines.append(f"{text} {cites}".strip())
    else:
        for fname, fdata in fields.items():
            lines.append(f"### {fname}")
            if isinstance(fdata, dict):
                text, _, _ = _format_field_value(fdata, url_validation)
                lines.append(text)
            else:
                lines.append(UNCERTAIN_MARKER)
            lines.append("")
    if j.get("budget_exhausted"):
        lines.append("_Note: agent stopped due to budget exhaustion._")
    lines.append("")
    return "\n".join(lines)


def _cross_cutting(item_jsons: list[dict]) -> str:
    lines = ["## Cross-cutting findings", ""]
    cross = []
    for j in item_jsons:
        for ext in j.get("proposed_extensions") or []:
            cross.append((j.get("subquery") or j.get("item") or "", ext))
    if not cross:
        lines.append("No cross-cutting findings surfaced across subqueries.")
        lines.append("")
        return "\n".join(lines)
    for scope, ext in cross:
        desc = ext.get("description", "") if isinstance(ext, dict) else str(ext)
        lines.append(f"- ({scope}) {desc}")
    lines.append("")
    return "\n".join(lines)
