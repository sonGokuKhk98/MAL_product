# Migration & Architecture Strategy

## Visual Overview

Architecture diagram: [docs/assets/pipeline-flow.svg](/Users/hiteshkaushik/MAL_product/docs/assets/pipeline-flow.svg)

Migration diagram: [docs/assets/rollout-flow.svg](/Users/hiteshkaushik/MAL_product/docs/assets/rollout-flow.svg)

## 1. Architecture Strategy

My starting point was simple: Cards, Transfers, and Bill Payments are all payment events, but each squad produces them in its own format. If the business wants shared reporting, stronger controls, and faster downstream analytics, consumers should not need to understand three different schemas. The platform should absorb that complexity once and publish one canonical contract.

That is why I chose a flat canonical payment model instead of a heavily normalized design. In a larger production platform, I might separate payment facts, parties, merchants, and lifecycle history into multiple related tables. For this rollout, though, that would slow adoption. A single reusable row per payment event is much easier for Finance, Risk, CRM, and Analytics teams to query immediately.

I also kept product-specific details such as `merchant_name`, `counterparty_id`, and `biller_code` as optional fields inside the same contract. The trade-off is that the model is less academically pure, but it is much more practical for a first shared platform release. The goal here is fast standardization with low adoption friction.

## 2. Pipeline Design Logic

Each squad keeps ownership of its raw extract, but the platform owns mapping, validation, contract migration, and published outputs. I made that choice because the platform is the right place to manage standardization consistently.

The mapping layer is the main control point. This is where squad-specific fields are translated into the shared contract, where status semantics are normalized, and where timestamps and amounts are made consistent. Once that common layer exists, version migration becomes much easier because the platform can move records from `v1` to `v2` centrally instead of asking every squad to upgrade at the same pace.

Validation sits after migration because I want the final published dataset to match the latest governed contract. Squads can continue producing backward-compatible versions for a period of time, but the platform is responsible for publishing only well-formed records in the final shape. Rejected rows should go to an error log rather than disappearing silently.

## 3. Migration Strategy

I approached the rollout as a risk-management problem, not just a delivery plan. The right sequence is the one that proves the model early while avoiding the most operationally sensitive flows at the start.

Bill Payments should come first because it is usually lower volume, structurally simpler, and less sensitive than cards or outbound transfers. If the shared model or validation process needs adjustment, Bill Payments is the safest place to learn. The first 30 days should focus on publishing canonical `v1`, documenting source mappings, and running the shared pipeline in parallel with current squad outputs.

Cards should come second because they create visible business value quickly. This phase can introduce `v2` of the contract with fields such as `channel` and `country_code`, while still keeping backward compatibility so squads can emit `v1` and let the platform handle migration during ingestion.

Transfers should come last because they usually carry the highest controls burden. Beneficiary semantics, sanctions context, and cross-border reporting make transfers the least forgiving domain for an early rollout mistake. By the time Transfers move over, the platform should already have proved that the contract, validation rules, and operating model work.

## 4. Governance and Success Measures

Governance has to be explicit from the start. The platform team should own the canonical contract, migration logic, validation library, and release process. Product squads should own extraction quality and mapping correctness for their own sources.

Breaking changes should require a major version bump. Non-breaking additions should stay within the same major version. Every contract release should include a changelog, sample payload, validation rules, and a named owner. I would also place validation in three layers: source mapping tests, ingestion-time checks, and post-load monitoring.

I would measure success through canonical coverage rate, reuse rate across downstream jobs, schema compliance rate, time to onboard a new source, and incident rate tied to data mismatches or delayed loads. Those metrics show whether the platform is actually being adopted, not just whether it was delivered.

## 5. Production Direction

If this moved beyond an assessment-scale implementation, I would shift ingestion to object storage landing zones, orchestrate runs with Airflow or Dagster, and publish to a warehouse-friendly format such as Delta or Iceberg. I would also add idempotency keys, partitioning by event date, structured logging, and dead-letter handling for rejected rows.

Monitoring would cover freshness, row counts, rejection rates, null-rate spikes, and reconciliation against source totals. For this submission, I intentionally left out full cloud deployment, secrets handling, and a complete semantic warehouse layer so the focus stays on the core platform thinking: standardize the model, roll it out safely, and govern it well.
