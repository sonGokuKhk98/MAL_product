from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "outputs"
SOURCE_MAP = {
    "cards": "cards",
    "transfers": "payments_transfers",
    "bill_payments": "bill_payments",
}


def load_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def hours_since(timestamp: str) -> float:
    return round((datetime.now(timezone.utc) - datetime.fromisoformat(timestamp)).total_seconds() / 3600, 2)


def main() -> None:
    valid = load_jsonl(OUT_DIR / "canonical_payments_v2.jsonl")
    invalid = load_jsonl(OUT_DIR / "validation_errors.jsonl")
    by_source = Counter(row["source_system"] for row in valid)
    invalid_by_source = Counter(SOURCE_MAP[row["source_file"].replace(".csv", "")] for row in invalid)
    freshness = max((row["event_ts"] for row in valid), default=datetime.now(timezone.utc).isoformat())
    null_rates = defaultdict(int)
    for row in valid:
        for field in ("merchant_name", "counterparty_id", "biller_code"):
            null_rates[field] += int(not row[field])
    volume_by_day = Counter(row["event_ts"][:10] for row in valid)
    median_volume = sorted(volume_by_day.values())[len(volume_by_day) // 2] if volume_by_day else 0
    anomalies = [day for day, count in volume_by_day.items() if median_volume and count < median_volume * 0.5]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_compliance_rate": round(len(valid) / max(len(valid) + len(invalid), 1), 4),
        "source_compliance": {
            source: {
                "valid": by_source.get(source, 0),
                "invalid": invalid_by_source.get(source, 0),
            }
            for source in sorted(set(by_source) | set(invalid_by_source))
        },
        "freshness_hours_since_latest_event": hours_since(freshness),
        "null_rate_optional_fields": {field: round(count / max(len(valid), 1), 4) for field, count in null_rates.items()},
        "volume_anomaly_days": anomalies,
    }
    (OUT_DIR / "data_quality_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
