# Mal Unified Payment Data Pipeline

Compact assessment implementation for Mal's multi-product payment platform. It unifies card, transfer, and bill-payment events into a shared canonical model, validates the contract, demonstrates a `v1 -> v2` migration path, and writes queryable outputs for downstream teams.

Live demo: `https://songokukhk98.github.io/MAL_product/`

Data quality dashboard: `https://songokukhk98.github.io/MAL_product/data_quality_dashboard.html`

Architecture visuals:
- [Pipeline Flowchart](/Users/hiteshkaushik/MAL_product/docs/assets/pipeline-flow.svg)
- [30/60/90 Rollout Flowchart](/Users/hiteshkaushik/MAL_product/docs/assets/rollout-flow.svg)
- Excalidraw sources: [pipeline-flow.excalidraw](/Users/hiteshkaushik/MAL_product/docs/assets/pipeline-flow.excalidraw) and [rollout-flow.excalidraw](/Users/hiteshkaushik/MAL_product/docs/assets/rollout-flow.excalidraw)

## What is included

- `data/`: mock CSV extracts from Cards, Transfers, and Bill Payments squads
- `src/pipeline.py`: end-to-end ingestion, transformation, validation, migration, and output writer
- `src/data_quality.py`: bonus data quality monitoring report
- `src/generate_demo.py`: static HTML demo generator for GitHub Pages
- `sql/downstream_queries.sql`: example SQL for analytics, finance, risk, and CRM teams
- `docs/architecture_strategy.md`: rollout and governance document
- `docs/architecture_strategy.pdf`: PDF version of the strategy document

## Canonical model

Canonical contract `v2` fields:

`contract_version, payment_id, payment_type, source_system, customer_id, amount, currency, event_ts, status, payment_method, reference_id, merchant_name, counterparty_id, biller_code, is_recurring, channel, country_code, ingested_at`

Design notes:

- Shared payment fields come first so downstream consumers can query all products with one table.
- Product-specific fields are nullable rather than split into three siloed tables.
- `channel` and `country_code` were added in `v2` to support operational analytics and cross-border controls.

## Local run

Python 3.9+ is sufficient. No third-party packages are required.

```bash
python3 src/pipeline.py
python3 src/data_quality.py
python3 src/generate_demo.py
```

## Outputs

After running the pipeline:

- `outputs/canonical_payments_v2.jsonl`: validated canonical records
- `outputs/canonical_payments_v1_preview.jsonl`: sample pre-migration records
- `outputs/validation_errors.jsonl`: rejected rows with explicit validation reasons
- `outputs/payments.db`: SQLite database with `canonical_payments` table
- `outputs/run_summary.json`: pipeline run summary
- `outputs/data_quality_report.json`: bonus quality report
- `docs/index.html`: deployed pipeline demo page for GitHub Pages
- `docs/data_quality_dashboard.html`: deployed bonus data quality dashboard

## Validation rules

- Required field checks for all canonical identifiers and operational metadata
- Positive numeric amount
- ISO-8601 timestamp parsing
- Enumerated checks for `payment_type`, `status`, `payment_method`, and `channel`
- ISO-style length checks for `currency` and `country_code`

## Data contract versioning

`v1` represents the first common contract shared by squads. `v2` adds `channel` and `country_code`.

Migration pattern used here:

1. Ingest squad-specific rows and map them to canonical `v1`.
2. Apply deterministic migration to `v2`.
3. Validate only the latest contract before publishing.

This keeps source teams stable during rollout while the platform team evolves the shared model.

## Query the unified model

```bash
sqlite3 outputs/payments.db < sql/downstream_queries.sql
```

If `sqlite3` is not installed, open the `.sql` file and run the queries in any SQLite-compatible client.

## Assessment framing

This implementation intentionally stays small:

- stdlib-only Python to keep local setup trivial
- JSONL plus SQLite instead of heavier warehouse tooling
- row-level rejection logging instead of a full dead-letter queue

In production, this would move behind orchestration, object storage, CI contract tests, and warehouse-managed tables. Those trade-offs are covered in the strategy document.

## Optional deployed demo

The static demo is live on GitHub Pages:

`https://songokukhk98.github.io/MAL_product/`

To refresh the published demo after changing data or code:

```bash
python3 src/pipeline.py
python3 src/data_quality.py
python3 src/generate_demo.py
```

Then commit and push the updated `docs/index.html` to GitHub. Pages will redeploy automatically from the `docs/` folder on the `master` branch.
