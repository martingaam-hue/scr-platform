"""PDF report generator using Jinja2 HTML rendering.

Generates styled HTML (stored as .html). Actual PDF conversion uses
headless Chrome / wkhtmltopdf via pdf_utils in production.

Supported section types:
  kv            – key/value pairs table
  table         – data table (list of dicts)
  text          – free-form narrative text
  metrics_grid  – 2–4 column KPI card grid
  checklist     – status checklist table with colour-coded badges
"""

from jinja2 import Template

from app.modules.reporting.generators.base import BaseReportGenerator

HTML_TEMPLATE = Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
      color: #1a1d23;
      padding: 48px;
      background: #fff;
      font-size: 13px;
      line-height: 1.5;
    }

    /* ── Cover header ─────────────────────────────────── */
    .header {
      background: {{ brand_color }};
      color: #fff;
      padding: 40px 48px;
      margin: -48px -48px 40px;
    }
    .header h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.3px; }
    .header .meta { font-size: 13px; opacity: 0.8; }
    .header .org-name { font-size: 15px; font-weight: 600; margin-bottom: 4px; }

    /* ── Section container ────────────────────────────── */
    .section { margin-bottom: 36px; page-break-inside: avoid; }
    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: {{ brand_color }};
      border-bottom: 2px solid {{ brand_color }};
      padding-bottom: 8px;
      margin-bottom: 16px;
      letter-spacing: -0.2px;
    }

    /* ── Metrics grid (KPI cards) ─────────────────────── */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 4px;
    }
    .metric-card {
      background: #f7f8fa;
      border: 1px solid #e2e5ea;
      border-radius: 6px;
      padding: 14px 16px;
    }
    .metric-card .metric-label {
      font-size: 11px;
      color: #8a8f9a;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .metric-card .metric-value {
      font-size: 20px;
      font-weight: 700;
      color: #1a1d23;
    }

    /* ── Data tables ──────────────────────────────────── */
    table { width: 100%; border-collapse: collapse; margin-bottom: 4px; }
    thead th {
      background: {{ brand_color }};
      color: #fff;
      padding: 9px 12px;
      text-align: left;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.2px;
    }
    tbody td {
      padding: 7px 12px;
      border-bottom: 1px solid #e8eaed;
      font-size: 12px;
      color: #374151;
      vertical-align: top;
    }
    tbody tr:last-child td { border-bottom: none; }
    tbody tr:nth-child(even) td { background: #f9fafb; }

    /* ── Key/value table ──────────────────────────────── */
    .kv-table td:first-child {
      font-weight: 600;
      width: 38%;
      color: #6b7280;
      font-size: 12px;
    }
    .kv-table td:last-child { color: #1a1d23; font-size: 12px; }

    /* ── Checklist ────────────────────────────────────── */
    .checklist-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
    }
    .badge-complete { background: #dcfce7; color: #166534; }
    .badge-pending  { background: #fef9c3; color: #854d0e; }
    .badge-breach   { background: #fee2e2; color: #991b1b; }
    .badge-warning  { background: #ffedd5; color: #9a3412; }
    .badge-waived   { background: #f3e8ff; color: #6b21a8; }
    .badge-default  { background: #f3f4f6; color: #374151; }

    /* ── Narrative text ───────────────────────────────── */
    .text-content {
      line-height: 1.7;
      font-size: 13px;
      color: #374151;
      max-width: 720px;
    }

    /* ── Footer ───────────────────────────────────────── */
    .footer {
      margin-top: 56px;
      padding-top: 14px;
      border-top: 1px solid #e2e5ea;
      font-size: 11px;
      color: #9ca3af;
      display: flex;
      justify-content: space-between;
    }
    .confidential {
      background: #fef3c7;
      border: 1px solid #f59e0b;
      color: #92400e;
      font-size: 11px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 4px;
      margin: -20px -48px 32px;
      text-align: center;
      letter-spacing: 0.5px;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="org-name">{{ org_name }}</div>
    <h1>{{ title }}</h1>
    <div class="meta">Generated {{ generated_at }}</div>
  </div>

  {% if confidential %}
  <div class="confidential">CONFIDENTIAL &mdash; FOR AUTHORISED RECIPIENTS ONLY</div>
  {% endif %}

  {% for section in sections %}
  <div class="section">
    <div class="section-title">{{ section.display_name }}</div>

    {% if section.type == 'metrics_grid' %}
    <div class="metrics-grid">
      {% for item in section.items %}
      <div class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </div>
      {% endfor %}
    </div>

    {% elif section.type == 'table' %}
    {% if section.rows %}
    <table>
      <thead><tr>{% for h in section.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for row in section.rows %}
        <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p style="color:#9ca3af;font-size:12px;">No data available.</p>
    {% endif %}

    {% elif section.type == 'kv' %}
    <table class="kv-table">
      {% for key, val in section.items %}
      <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
      {% endfor %}
    </table>

    {% elif section.type == 'checklist' %}
    <table>
      <thead><tr>{% for h in section.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for row in section.rows %}
        <tr>
          {% for i, cell in enumerate(row) %}
          {% if i == section.status_col %}
          <td>
            {% set s = cell | lower %}
            {% if s in ('complete', 'completed', 'compliant', 'yes', 'done') %}
              <span class="checklist-badge badge-complete">{{ cell }}</span>
            {% elif s in ('pending', 'in progress', 'queued', 'not started') %}
              <span class="checklist-badge badge-pending">{{ cell }}</span>
            {% elif s in ('breach', 'failed', 'overdue', 'error') %}
              <span class="checklist-badge badge-breach">{{ cell }}</span>
            {% elif s in ('warning', 'at risk', 'review') %}
              <span class="checklist-badge badge-warning">{{ cell }}</span>
            {% elif s in ('waived', 'n/a', 'not applicable') %}
              <span class="checklist-badge badge-waived">{{ cell }}</span>
            {% else %}
              <span class="checklist-badge badge-default">{{ cell }}</span>
            {% endif %}
          </td>
          {% else %}
          <td>{{ cell }}</td>
          {% endif %}
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>

    {% else %}
    <div class="text-content">{{ section.content }}</div>
    {% endif %}

  </div>
  {% endfor %}

  <div class="footer">
    <span>{{ org_name }} &mdash; {{ title }}</span>
    <span>{{ generated_at }}</span>
  </div>
</body>
</html>
""")

# Column names that are typically status/badge columns
_STATUS_COLUMN_KEYWORDS = frozenset(
    {
        "status",
        "state",
        "compliance",
        "result",
        "outcome",
        "completion",
        "complete",
        "received",
        "aligned",
    }
)


def _guess_status_col(headers: list[str]) -> int:
    """Return the index of the most likely status column, or -1."""
    for i, h in enumerate(headers):
        if h.lower() in _STATUS_COLUMN_KEYWORDS:
            return i
    return -1


class PDFGenerator(BaseReportGenerator):
    """Generate styled HTML report (PDF conversion via pdf_utils in production)."""

    CONTENT_TYPE = "text/html"

    def generate(self, data: dict, sections: list[dict]) -> tuple[bytes, str]:
        rendered_sections = []
        confidential = (data.get("parameters") or {}).get("confidential", False)

        for section in sections:
            name = section.get("name", "section")
            label = section.get("label", name.replace("_", " ").title())
            section_type_hint = section.get("type", "")
            section_data = data.get(name)

            rendered = self._render_section(name, label, section_type_hint, section_data)
            rendered_sections.append(rendered)

        html = HTML_TEMPLATE.render(
            title=data.get("title", "Report"),
            org_name=self.org_name,
            brand_color=self.brand_color,
            generated_at=self.generated_at,
            confidential=confidential,
            sections=rendered_sections,
            enumerate=enumerate,
        )
        return html.encode("utf-8"), self.CONTENT_TYPE

    # ── Section rendering ──────────────────────────────────────────────────────

    def _render_section(
        self,
        name: str,
        label: str,
        type_hint: str,
        section_data,
    ) -> dict:
        """Convert raw section data into a typed render dict."""

        # ── Explicit metrics_grid ──────────────────────────────────────────────
        if (
            (
                type_hint == "metrics_grid"
                or (
                    isinstance(section_data, dict)
                    and type_hint in ("metrics_grid", "")
                    and not isinstance(section_data, list)
                    and all(not isinstance(v, dict | list) for v in section_data.values())
                    and len(section_data) <= 10
                )
            )
            and isinstance(section_data, dict)
            and section_data
        ):
            return {
                "display_name": label,
                "type": "metrics_grid",
                "items": [
                    {
                        "label": k.replace("_", " ").title(),
                        "value": str(v) if v is not None else "—",
                    }
                    for k, v in section_data.items()
                ],
            }

        # ── List of dicts → table ──────────────────────────────────────────────
        if isinstance(section_data, list) and section_data:
            if isinstance(section_data[0], dict):
                headers = [h.replace("_", " ").title() for h in section_data[0]]
                raw_headers_lower = [h.lower() for h in section_data[0]]
                rows = [
                    [str(v) if v is not None else "" for v in row.values()] for row in section_data
                ]
                if type_hint == "checklist":
                    status_col = _guess_status_col(raw_headers_lower)
                    return {
                        "display_name": label,
                        "type": "checklist",
                        "headers": headers,
                        "rows": rows,
                        "status_col": status_col,
                    }
                return {
                    "display_name": label,
                    "type": "table",
                    "headers": headers,
                    "rows": rows,
                }
            # List of scalars → single-column table
            return {
                "display_name": label,
                "type": "table",
                "headers": [label],
                "rows": [[str(v)] for v in section_data],
            }

        # ── Dict → kv or metrics_grid ──────────────────────────────────────────
        if isinstance(section_data, dict) and section_data:
            # Deep dicts (nested) → kv with string representation
            items = [
                (k.replace("_", " ").title(), str(v) if v is not None else "—")
                for k, v in section_data.items()
            ]
            if type_hint == "metrics_grid":
                return {
                    "display_name": label,
                    "type": "metrics_grid",
                    "items": [{"label": k, "value": v} for k, v in items],
                }
            return {
                "display_name": label,
                "type": "kv",
                "items": items,
            }

        # ── String → text ──────────────────────────────────────────────────────
        if isinstance(section_data, str) and section_data:
            return {
                "display_name": label,
                "type": "text",
                "content": section_data,
            }

        # ── Fallback ───────────────────────────────────────────────────────────
        return {
            "display_name": label,
            "type": "text",
            "content": f"No data available for {label}.",
        }
