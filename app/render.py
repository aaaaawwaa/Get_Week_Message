from datetime import datetime
import json
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import TEMPLATE_DIR, REPORTS_DIR, SOURCE_LABELS, SOURCE_ORDER


def _parse_github_desc(raw_json: str) -> dict:
    """解析 raw_json 中的 GitHub 项目描述信息。"""
    try:
        return json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return {}


_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)
_env.filters["github_desc"] = _parse_github_desc


def _group_items(items: List[Dict]) -> List[Dict]:
    by_source: Dict[str, List[Dict]] = {}
    for item in items:
        source = item.get("source", "unknown")
        by_source.setdefault(source, []).append(item)

    groups: List[Dict] = []
    for source in SOURCE_ORDER:
        if source in by_source:
            groups.append(
                {
                    "source": source,
                    "label": SOURCE_LABELS.get(source, source),
                    "entries": by_source[source],
                }
            )
            by_source.pop(source, None)

    for source in sorted(by_source.keys()):
        groups.append(
            {
                "source": source,
                "label": SOURCE_LABELS.get(source, source),
                "entries": by_source[source],
            }
        )

    return groups


def render_weekly(
    week_start: str,
    items: List[Dict],
    ai_summary: str,
    ai_status: str,
) -> str:
    template = _env.get_template("report.html")
    groups = _group_items(items)
    summary = [
        {"label": group["label"], "count": len(group["entries"])}
        for group in groups
    ]

    # Build featured items: top 3 from each source, max 9 total
    featured_items: List[Dict] = []
    for group in groups:
        for item in group["entries"][:3]:
            featured_items.append(item)
        if len(featured_items) >= 9:
            break

    html = template.render(
        week_start=week_start,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        groups=groups,
        summary=summary,
        total_count=len(items),
        featured_items=featured_items,
        ai_summary=ai_summary,
        ai_summary_status=ai_status,
    )
    output_path = REPORTS_DIR / f"{week_start}.html"
    output_path.write_text(html, encoding="utf-8")
    latest_path = REPORTS_DIR / "latest.html"
    latest_path.write_text(html, encoding="utf-8")
    return str(output_path)


def render_index(week_summaries: List[Dict]) -> str:
    template = _env.get_template("index.html")
    weeks = [
        {
            "week_start": row["week_start"],
            "total": row["total"],
            "link": f"/reports/{row['week_start']}.html",
        }
        for row in week_summaries
    ]
    html = template.render(
        weeks=weeks,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    output_path = REPORTS_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
