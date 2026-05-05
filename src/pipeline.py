from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"
VALID_STATUSES = {"SETTLED", "DECLINED", "COMPLETED", "PENDING", "FAILED", "PAID", "SCHEDULED"}
VALID_TYPES = {"card", "transfer", "bill_payment"}
VALID_METHODS = {"DEBIT_CARD", "CREDIT_CARD", "ACCOUNT_BALANCE", "CARD", "BANK_TRANSFER"}
VALID_CHANNELS = {"MOBILE_APP", "WEB", "BRANCH", "POS"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_csv(name: str) -> List[Dict[str, str]]:
    with (DATA_DIR / name).open() as handle:
        return list(csv.DictReader(handle))


def card_to_v1(row: Dict[str, str]) -> Dict[str, object]:
    return {
        "contract_version": "v1",
        "payment_id": row["card_txn_id"],
        "payment_type": "card",
        "source_system": "cards",
        "customer_id": row["customer_no"],
        "amount": row["txn_amount"],
        "currency": row["currency_code"],
        "event_ts": row["auth_ts"],
        "status": row["txn_status"],
        "payment_method": row["payment_method"],
        "reference_id": row["rrn"],
        "merchant_name": row["merchant_name"],
        "counterparty_id": "",
        "biller_code": "",
        "is_recurring": False,
        "channel_hint": "POS" if row["pos_entry_mode"] != "ECOM" else "WEB",
        "country_hint": row["merchant_country"],
    }


def transfer_to_v1(row: Dict[str, str]) -> Dict[str, object]:
    return {
        "contract_version": "v1",
        "payment_id": row["transfer_id"],
        "payment_type": "transfer",
        "source_system": "payments_transfers",
        "customer_id": row["user_id"],
        "amount": row["amount"],
        "currency": row["currency"],
        "event_ts": row["initiated_at"],
        "status": row["state"],
        "payment_method": "BANK_TRANSFER",
        "reference_id": row["destination_iban"][-8:],
        "merchant_name": "",
        "counterparty_id": row["beneficiary_id"],
        "biller_code": "",
        "is_recurring": False,
        "channel_hint": row["channel_name"],
        "country_hint": row["country_code"],
    }


def bill_to_v1(row: Dict[str, str]) -> Dict[str, object]:
    return {
        "contract_version": "v1",
        "payment_id": row["payment_ref"],
        "payment_type": "bill_payment",
        "source_system": "bill_payments",
        "customer_id": row["cif"],
        "amount": row["bill_amount"],
        "currency": row["bill_currency"],
        "event_ts": row["paid_on"],
        "status": row["payment_state"],
        "payment_method": row["debit_method"],
        "reference_id": row["source_account"][-4:],
        "merchant_name": "",
        "counterparty_id": "",
        "biller_code": row["biller_code"],
        "is_recurring": row["recurring_flag"].lower() == "true",
        "channel_hint": row["channel"],
        "country_hint": "AE",
    }


def migrate_v1_to_v2(record: Dict[str, object]) -> Dict[str, object]:
    migrated = dict(record)
    migrated["contract_version"] = "v2"
    migrated["channel"] = migrated.pop("channel_hint", "WEB")
    migrated["country_code"] = migrated.pop("country_hint", "AE")
    migrated["ingested_at"] = now_iso()
    return migrated


def validate_v2(record: Dict[str, object]) -> List[str]:
    errors: List[str] = []
    required = [
        "payment_id",
        "payment_type",
        "source_system",
        "customer_id",
        "amount",
        "currency",
        "event_ts",
        "status",
        "payment_method",
        "channel",
        "country_code",
        "contract_version",
    ]
    for field in required:
        if record.get(field) in ("", None):
            errors.append(f"missing {field}")
    if record.get("payment_type") not in VALID_TYPES:
        errors.append("invalid payment_type")
    if record.get("status") not in VALID_STATUSES:
        errors.append("invalid status")
    if record.get("payment_method") not in VALID_METHODS:
        errors.append("invalid payment_method")
    if record.get("channel") not in VALID_CHANNELS:
        errors.append("invalid channel")
    try:
        if float(record.get("amount", 0)) <= 0:
            errors.append("amount must be > 0")
    except (TypeError, ValueError):
        errors.append("amount must be numeric")
    try:
        datetime.fromisoformat(str(record.get("event_ts")))
    except ValueError:
        errors.append("event_ts must be ISO-8601")
    if len(str(record.get("currency", ""))) != 3:
        errors.append("currency must be ISO-4217")
    if len(str(record.get("country_code", ""))) != 2:
        errors.append("country_code must be ISO-3166 alpha-2")
    return errors


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def write_sqlite(path: Path, rows: List[Dict[str, object]]) -> None:
    conn = sqlite3.connect(path)
    conn.execute("drop table if exists canonical_payments")
    conn.execute(
        """
        create table canonical_payments (
            contract_version text,
            payment_id text primary key,
            payment_type text,
            source_system text,
            customer_id text,
            amount real,
            currency text,
            event_ts text,
            status text,
            payment_method text,
            reference_id text,
            merchant_name text,
            counterparty_id text,
            biller_code text,
            is_recurring integer,
            channel text,
            country_code text,
            ingested_at text
        )
        """
    )
    conn.executemany(
        """
        insert into canonical_payments values (
            :contract_version, :payment_id, :payment_type, :source_system, :customer_id,
            :amount, :currency, :event_ts, :status, :payment_method, :reference_id,
            :merchant_name, :counterparty_id, :biller_code, :is_recurring, :channel,
            :country_code, :ingested_at
        )
        """,
        [{**row, "is_recurring": int(bool(row["is_recurring"]))} for row in rows],
    )
    conn.commit()
    conn.close()


def run() -> Tuple[int, int]:
    OUT_DIR.mkdir(exist_ok=True)
    transformers = {
        "cards.csv": card_to_v1,
        "transfers.csv": transfer_to_v1,
        "bill_payments.csv": bill_to_v1,
    }
    valid_rows: List[Dict[str, object]] = []
    invalid_rows: List[Dict[str, object]] = []
    v1_preview: List[Dict[str, object]] = []
    for file_name, transformer in transformers.items():
        for row in load_csv(file_name):
            v1 = transformer(row)
            v2 = migrate_v1_to_v2(v1)
            errors = validate_v2(v2)
            if len(v1_preview) < 3:
                v1_preview.append(v1)
            if errors:
                invalid_rows.append({"source_file": file_name, "payment_id": v2["payment_id"], "errors": errors, "raw": row})
            else:
                v2["amount"] = round(float(v2["amount"]), 2)
                valid_rows.append(v2)
    write_jsonl(OUT_DIR / "canonical_payments_v2.jsonl", valid_rows)
    write_jsonl(OUT_DIR / "validation_errors.jsonl", invalid_rows)
    write_jsonl(OUT_DIR / "canonical_payments_v1_preview.jsonl", v1_preview)
    write_sqlite(OUT_DIR / "payments.db", valid_rows)
    status_counts = Counter(row["status"] for row in valid_rows)
    summary = {
        "generated_at": now_iso(),
        "valid_records": len(valid_rows),
        "invalid_records": len(invalid_rows),
        "status_breakdown": dict(status_counts),
        "output_files": [
            "outputs/canonical_payments_v2.jsonl",
            "outputs/canonical_payments_v1_preview.jsonl",
            "outputs/validation_errors.jsonl",
            "outputs/payments.db",
        ],
    }
    (OUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2))
    return len(valid_rows), len(invalid_rows)


if __name__ == "__main__":
    valid, invalid = run()
    print(f"pipeline complete: {valid} valid, {invalid} invalid")
