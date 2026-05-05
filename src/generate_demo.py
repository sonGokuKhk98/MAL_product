from __future__ import annotations

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs"
DOCS_DIR = BASE_DIR / "docs"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def query_rows(sql: str) -> list[tuple]:
    conn = sqlite3.connect(OUT_DIR / "payments.db")
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def table(headers: list[str], rows: list[tuple]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def main() -> None:
    summary = load_json(OUT_DIR / "run_summary.json")
    quality = load_json(OUT_DIR / "data_quality_report.json")
    by_type = query_rows(
        "select payment_type, count(*), round(sum(amount), 2) from canonical_payments group by 1 order by 1"
    )
    by_source = query_rows(
        "select source_system, count(*), round(sum(amount), 2) from canonical_payments group by 1 order by 1"
    )
    recent = query_rows(
        "select payment_id, payment_type, customer_id, amount, currency, status, country_code from canonical_payments order by event_ts desc limit 8"
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mal Unified Payments Demo</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --card: #fffdf8;
      --ink: #1b2430;
      --muted: #5b6574;
      --accent: #0f766e;
      --line: #d7d2c8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(15,118,110,.10), transparent 28%),
        linear-gradient(180deg, #f9f5ef 0%, var(--bg) 100%);
      color: var(--ink);
      font: 16px/1.5 Georgia, "Times New Roman", serif;
    }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 48px 20px 64px; }}
    h1, h2 {{ font-family: Helvetica, Arial, sans-serif; letter-spacing: -.02em; }}
    h1 {{ font-size: 40px; line-height: 1.05; margin: 0 0 8px; }}
    p {{ color: var(--muted); max-width: 760px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin: 28px 0 36px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(27,36,48,.05);
    }}
    .metric {{
      font: 600 34px/1 Helvetica, Arial, sans-serif;
      margin: 4px 0;
    }}
    .label {{
      color: var(--muted);
      font: 600 12px/1.2 Helvetica, Arial, sans-serif;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    section {{ margin-top: 28px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid #ebe5da;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      font-family: Helvetica, Arial, sans-serif;
      font-size: 12px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
      background: #faf7f1;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    @media (max-width: 800px) {{
      .two-col {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 32px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Unified Payment Data Pipeline</h1>
    <p>Static demo for the Mal assessment. This page is generated from the pipeline outputs and is suitable for GitHub Pages as the optional deployed demo.</p>

    <div class="grid">
      <div class="card">
        <div class="label">Valid Records</div>
        <div class="metric">{summary.get("valid_records", 0)}</div>
      </div>
      <div class="card">
        <div class="label">Invalid Records</div>
        <div class="metric">{summary.get("invalid_records", 0)}</div>
      </div>
      <div class="card">
        <div class="label">Compliance Rate</div>
        <div class="metric">{round(quality.get("schema_compliance_rate", 0) * 100, 1)}%</div>
      </div>
      <div class="card">
        <div class="label">Freshness Lag</div>
        <div class="metric">{quality.get("freshness_hours_since_latest_event", 0)}h</div>
      </div>
    </div>

    <section class="two-col">
      <div>
        <h2>Volume by Payment Type</h2>
        {table(["Payment Type", "Txn Count", "Total Amount"], by_type)}
      </div>
      <div>
        <h2>Volume by Source System</h2>
        {table(["Source", "Txn Count", "Total Amount"], by_source)}
      </div>
    </section>

    <section>
      <h2>Recent Canonical Records</h2>
      {table(["Payment ID", "Type", "Customer", "Amount", "Currency", "Status", "Country"], recent)}
    </section>
  </main>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html)
    print("generated docs/index.html")


if __name__ == "__main__":
    main()
