"""PDF report generator using Jinja2 HTML rendering.

Generates styled HTML (stored as .html). Actual PDF conversion would
require headless Chrome or wkhtmltopdf in production.
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
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a1a; padding: 40px; }
    .header { background: {{ brand_color }}; color: #fff; padding: 32px; margin: -40px -40px 32px; }
    .header h1 { font-size: 28px; margin-bottom: 8px; }
    .header .meta { font-size: 14px; opacity: 0.85; }
    .section { margin-bottom: 32px; page-break-inside: avoid; }
    .section h2 { font-size: 20px; color: {{ brand_color }}; border-bottom: 2px solid {{ brand_color }}; padding-bottom: 8px; margin-bottom: 16px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
    th { background: {{ brand_color }}; color: #fff; padding: 10px 12px; text-align: left; font-size: 13px; }
    td { padding: 8px 12px; border-bottom: 1px solid #e5e5e5; font-size: 13px; }
    tr:nth-child(even) { background: #f9f9f9; }
    .kv-table td:first-child { font-weight: 600; width: 40%; color: #555; }
    .text-content { line-height: 1.6; font-size: 14px; }
    .footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 12px; color: #888; text-align: center; }
  </style>
</head>
<body>
  <div class="header">
    <h1>{{ title }}</h1>
    <div class="meta">{{ org_name }} &bull; Generated {{ generated_at }}</div>
  </div>

  {% for section in sections %}
  <div class="section">
    <h2>{{ section.display_name }}</h2>
    {% if section.type == 'table' %}
    <table>
      <thead><tr>{% for h in section.headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for row in section.rows %}
        <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
        {% endfor %}
      </tbody>
    </table>
    {% elif section.type == 'kv' %}
    <table class="kv-table">
      {% for key, val in section['items'] %}
      <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="text-content">{{ section.content }}</div>
    {% endif %}
  </div>
  {% endfor %}

  <div class="footer">
    {{ org_name }} &mdash; Confidential &bull; {{ generated_at }}
  </div>
</body>
</html>
""")


class PDFGenerator(BaseReportGenerator):
    """Generate HTML report (PDF conversion deferred to production setup)."""

    CONTENT_TYPE = "text/html"

    def generate(self, data: dict, sections: list[dict]) -> tuple[bytes, str]:
        rendered_sections = []
        for section in sections:
            name = section.get("name", "section")
            display_name = name.replace("_", " ").title()
            section_data = data.get(name, {})

            if isinstance(section_data, list) and section_data:
                headers = [h.replace("_", " ").title() for h in section_data[0].keys()]
                rows = [
                    [str(v) if v is not None else "" for v in row.values()]
                    for row in section_data
                ]
                rendered_sections.append({
                    "display_name": display_name,
                    "type": "table",
                    "headers": headers,
                    "rows": rows,
                })
            elif isinstance(section_data, dict):
                items = [
                    (k.replace("_", " ").title(), str(v) if v is not None else "")
                    for k, v in section_data.items()
                ]
                rendered_sections.append({
                    "display_name": display_name,
                    "type": "kv",
                    "items": items,
                })
            else:
                rendered_sections.append({
                    "display_name": display_name,
                    "type": "text",
                    "content": str(section_data) if section_data else f"No data available for {display_name}.",
                })

        html = HTML_TEMPLATE.render(
            title=data.get("title", "Report"),
            org_name=self.org_name,
            brand_color=self.brand_color,
            generated_at=self.generated_at,
            sections=rendered_sections,
        )
        return html.encode("utf-8"), self.CONTENT_TYPE
