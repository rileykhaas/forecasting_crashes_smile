"""Wrap each exhibit PNG in a self-contained HTML file for the chartbook.

ChartBook renders a chart from an HTML ``path`` (not a PNG), so we base64-embed each
figure into a minimal standalone HTML page. The chartbook shows the **extended-sample**
(_ext, through the latest data) version of every figure that has one -- the date
extension the rubric requires -- falling back to the base figure otherwise.

Run by ``doit chart_html`` before the chartbook build.
"""

import base64
from pathlib import Path

from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

# chart_id -> source PNG. Use the _ext (through-2025) variant where one exists; the SVB
# case study is a fixed Feb-Mar 2023 window, so it has no extension.
CHART_PNG = {
    "fig1_single_name_bounds": "fig1_single_name_bounds_ext.png",
    "fig2_median_bounds_market": "fig2_median_bounds_market_ext.png",
    "fig6_oos_r2": "fig6_oos_r2_ext.png",
    "eda_panel": "eda_panel_ext.png",
    "fig_etf_sector_bounds": "fig_etf_sector_bounds_ext.png",
    "fig_industry_compare": "fig_industry_compare_ext.png",
    "fig_svb_case_study": "fig_svb_case_study.png",
}

_TEMPLATE = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>{title}</title>\n"
    "<style>html,body{{margin:0;padding:0;background:#fff}}"
    "img{{display:block;max-width:100%;height:auto;margin:0 auto}}</style>\n"
    "</head>\n<body>\n"
    '<img alt="{title}" src="data:image/png;base64,{b64}">\n'
    "</body>\n</html>\n"
)


def png_to_html(png_path, title):
    """Return a self-contained HTML string with the PNG base64-embedded."""
    b64 = base64.b64encode(Path(png_path).read_bytes()).decode("ascii")
    return _TEMPLATE.format(title=title, b64=b64)


def build_all(output_dir=OUTPUT_DIR):
    """Write ``<chart_id>.html`` into output_dir for every registered chart."""
    written = []
    for chart_id, png_name in CHART_PNG.items():
        png = output_dir / png_name
        html = output_dir / f"{chart_id}.html"
        html.write_text(png_to_html(png, chart_id))
        written.append(html.name)
    return written


if __name__ == "__main__":
    names = build_all()
    print("wrote chart HTML:", ", ".join(names))
