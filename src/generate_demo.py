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
    <p><a href="data_quality_dashboard.html">Open the dedicated Data Quality Dashboard</a></p>

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
    dashboard = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Data Quality Dashboard</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --card: #fffdf8;
      --ink: #1b2430;
      --muted: #5b6574;
      --accent: #0f766e;
      --warn: #b45309;
      --danger: #b91c1c;
      --line: #d7d2c8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(15,118,110,.08), transparent 24%),
        linear-gradient(180deg, #f9f5ef 0%, var(--bg) 100%);
      color: var(--ink);
      font: 16px/1.5 Georgia, "Times New Roman", serif;
    }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 48px 20px 64px; }}
    h1, h2, h3 {{ font-family: Helvetica, Arial, sans-serif; letter-spacing: -.02em; }}
    h1 {{ font-size: 42px; line-height: 1.05; margin: 0 0 8px; }}
    p {{ color: var(--muted); max-width: 820px; }}
    .back {{ margin-top: 12px; display: inline-block; color: var(--accent); font-family: Helvetica, Arial, sans-serif; font-weight: 600; }}
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
      margin: 4px 0 8px;
    }}
    .label {{
      color: var(--muted);
      font: 600 12px/1.2 Helvetica, Arial, sans-serif;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .note {{
      color: var(--muted);
      font-size: 14px;
    }}
    section {{ margin-top: 28px; }}
    .two-col {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18px;
    }}
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
    .pill {{
      display: inline-block;
      border-radius: 999px;
      padding: 4px 10px;
      font: 600 12px/1 Helvetica, Arial, sans-serif;
      letter-spacing: .03em;
    }}
    .ok {{ background: #d1fae5; color: #065f46; }}
    .warn {{ background: #fef3c7; color: #92400e; }}
    .bad {{ background: #fee2e2; color: #991b1b; }}
    ul {{ margin: 8px 0 0 20px; color: var(--muted); }}
    @media (max-width: 860px) {{
      .two-col {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 34px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Data Quality Dashboard</h1>
    <p>This bonus dashboard operationalizes shared-platform data quality across Mal's three payment source systems. It focuses on the three checks the prompt asked for: schema compliance, freshness, and anomaly monitoring.</p>
    <a class="back" href="index.html">Back to pipeline demo</a>

    <div class="grid">
      <div class="card">
        <div class="label">Schema Compliance</div>
        <div class="metric">{round(quality.get("schema_compliance_rate", 0) * 100, 1)}%</div>
        <div class="note">Valid records divided by valid + invalid ingested rows.</div>
      </div>
      <div class="card">
        <div class="label">Freshness Lag</div>
        <div class="metric">{quality.get("freshness_hours_since_latest_event", 0)}h</div>
        <div class="note">Hours since the latest successfully published payment event.</div>
      </div>
      <div class="card">
        <div class="label">Volume Anomalies</div>
        <div class="metric">{len(quality.get("volume_anomaly_days", []))}</div>
        <div class="note">Days where volume dropped below 50% of the median day.</div>
      </div>
      <div class="card">
        <div class="label">Invalid Records</div>
        <div class="metric">{summary.get("invalid_records", 0)}</div>
        <div class="note">Rejected records captured for follow-up instead of silently dropped.</div>
      </div>
    </div>

    <section class="two-col">
      <div>
        <h2>Schema Compliance by Source</h2>
        {table(["Source System", "Valid", "Invalid"], [(source, stats.get("valid", 0), stats.get("invalid", 0)) for source, stats in quality.get("source_compliance", {}).items()])}
      </div>
      <div>
        <h2>Health Summary</h2>
        <div class="card">
          <p><span class="pill {'ok' if quality.get('schema_compliance_rate', 0) >= 0.95 else 'warn' if quality.get('schema_compliance_rate', 0) >= 0.8 else 'bad'}">Schema {'Healthy' if quality.get('schema_compliance_rate', 0) >= 0.95 else 'Watch' if quality.get('schema_compliance_rate', 0) >= 0.8 else 'Action Needed'}</span></p>
          <p><span class="pill {'ok' if quality.get('freshness_hours_since_latest_event', 0) <= 24 else 'warn' if quality.get('freshness_hours_since_latest_event', 0) <= 48 else 'bad'}">Freshness {'Healthy' if quality.get('freshness_hours_since_latest_event', 0) <= 24 else 'Lagging' if quality.get('freshness_hours_since_latest_event', 0) <= 48 else 'Stale'}</span></p>
          <p><span class="pill {'ok' if not quality.get('volume_anomaly_days', []) else 'warn'}">Volume {'Stable' if not quality.get('volume_anomaly_days', []) else 'Investigate'}</span></p>
          <ul>
            <li>Schema compliance tracks contract enforcement across Cards, Transfers, and Bill Payments.</li>
            <li>Freshness helps detect ingestion delays before downstream consumers notice stale data.</li>
            <li>Volume anomaly checks catch sharp drops that may point to failed extracts or upstream outages.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="two-col">
      <div>
        <h2>Optional Field Null Rates</h2>
        {table(["Field", "Null Rate"], [(field, f"{round(rate * 100, 2)}%") for field, rate in quality.get("null_rate_optional_fields", {}).items()])}
      </div>
      <div>
        <h2>Anomaly Details</h2>
        <div class="card">
          <p class="note">Detected anomaly days:</p>
          <ul>
            {"".join(f"<li>{day}</li>" for day in quality.get("volume_anomaly_days", [])) or "<li>No anomalous volume days detected in the current sample.</li>"}
          </ul>
        </div>
      </div>
    </section>
  </main>
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html)
    (DOCS_DIR / "data_quality_dashboard.html").write_text(dashboard)
    print("generated docs/index.html and docs/data_quality_dashboard.html")


if __name__ == "__main__":
    main()
