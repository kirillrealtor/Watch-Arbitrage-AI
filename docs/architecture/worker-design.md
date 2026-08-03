# ChronoArb — Worker Design

**Document type:** Async worker and pipeline architecture
**Source:** ChronoArb_MVP_SRS_v1.0 §10, AI-Agent Engineering Playbook §12
**Date:** 2026-08-03

---

## 1. Worker Architecture

ChronoArb uses separate worker processes for long-running ingestion, normalization, valuation, alert matching, and notification work. Workers are deployed as ECS Fargate tasks and scale independently by queue depth.

```
apps/worker/
├── workers/
│   ├── discovery/         # Source discovery worker
│   ├── fetch/             # Listing fetch worker
│   ├── normalize/         # Normalization worker
│   ├── valuate/           # Valuation worker
│   ├── alert_match/       # Alert matcher worker
│   ├── notify/            # Notification channel worker
│   ├── outbox/            # Outbox event publisher
│   └── analytics/         # Analytics event sink
├── shared/
│   ├── sqs_client.py      # SQS wrapper with DLQ handling
│   ├── tracing.py         # OpenTelemetry correlation
│   └── idempotency.py     # Idempotency helpers
└── main.py                # Worker entry point (configurable by WORKER_TYPE env var)
```

## 2. Worker Lifecycle

```
┌──────────────────────────────────────────────────┐
│ Worker Process (ECS Fargate Task)                 │
│                                                   │
│  while running:                                   │
│    messages = sqs.receive_message(                │
│      QueueUrl=queue_url,                          │
│      MaxNumberOfMessages=10,                      │
│      WaitTimeSeconds=20,                          │
│      VisibilityTimeout=300                        │
│    )                                              │
│    for msg in messages:                           │
│      try:                                         │
│        trace_id = extract_trace_id(msg)            │
│        with tracer.start_span(trace_id):           │
│          process(msg)                              │
│        sqs.delete_message(msg)                     │
│      except TransientError:                       │
│        # Visibility timeout will retry            │
│        raise                                      │
│      except PermanentError:                       │
│        sqs.send_message(DLQ, msg)                 │
│        sqs.delete_message(msg)                    │
│        record_failure_metric()                     │
│                                                   │
│  on SIGTERM:                                      │
│    drain current batch                            │
│    flush telemetry                                │
│    exit 0                                         │
└──────────────────────────────────────────────────┘
```

## 3. Pipeline Stages

### 3.1 Discovery Worker

- **Queue:** `source-discovery`
- **Input:** Scheduled trigger (EventBridge) or admin replay command
- **Output:** `SourceItemRef` messages to `source-fetch` queue

```
discover(source, scope, schedule_window) → [SourceItemRef]
- Determine time window to scan
- Call adapter.discover() for each enabled source
- Emit SourceItemRef to source-fetch queue
- Track last_discovered_at per source
```

Idempotency: `source + scope + schedule_window`

### 3.2 Fetch Worker

- **Queue:** `source-fetch`
- **Input:** `SourceItemRef` messages
- **Output:** `RawSnapshot` records; `ParsedListing` messages to `normalize-listing`

```
fetch_and_parse(item: SourceItemRef) → RawSnapshot + ParsedListing
- Call adapter.fetch(item)
- Compute checksum of raw response
- Check if RawSnapshot already exists for source + external_id + version + checksum
  → If yes: reuse existing snapshot (idempotent)
  → If no: store raw payload (S3 for large, JSONB for small) with lineage
- Call adapter.parse(raw)
- Emit ParsedListing to normalize-listing queue
```

Idempotency: `source + stable_external_id + observed_version/checksum`

### 3.3 Normalization Worker

- **Queue:** `normalize-listing`
- **Input:** `ParsedListing` messages
- **Output:** `NormalizedListing` records; may trigger `value-listing` message

```
normalize(parsed: ParsedListing) → NormalizedListing
- Normalize Unicode, punctuation, spacing, brand/reference separators
- Extract exact reference candidates with brand-specific regex
- Resolve exact canonical and alias matches
- Apply variant constraints (material, dial, bracelet, generation)
- Use supervised classifier only for unresolved cases after labeled examples exist
- Quarantine conflicting high-value matches for operations review
- Set match confidence and status (active/quarantined/suppressed)
- Persist NormalizedListing with normalizer version, method, features
```

Idempotency: `snapshot_id + parser_version + normalizer_version`

### 3.4 Valuation Worker

- **Queue:** `value-listing`
- **Input:** Triggered by normalization completion or price change event
- **Output:** `Valuation` record; may trigger `Opportunity` creation

```
valuate(listing: NormalizedListing) → Valuation
- Select comparable listings for the reference (recency decay, source quality weights)
- Apply condition, set, year, seller, geography adjustments (versioned tables)
- Compute all_in_acquisition, expected_net_resale, expected_net_profit, ROI
  - All using Decimal/fixed-point arithmetic
- Use median and MAD or winsorized ranges to resist extreme asks
- Compute confidence from sample_size, dispersion, match_quality, freshness
- Return low/high bands
- Persist immutable Valuation with model_version, config_version, lineage
```

Idempotency: `listing_id + listing_material_version + valuation_model_version + config_version + market_window`

### 3.5 Alert Matcher Worker

- **Queue:** `match-alerts`
- **Input:** New/modified opportunity
- **Output:** `AlertDelivery` messages to `send-notification` queue

```
match_alerts(opportunity: Opportunity) → [AlertMatch]
- Query enabled alert rules for the opportunity's organization
- Filter by reference, price range, condition, etc.
- Apply cooldown (last delivery for same rule + user + reference within cooldown period)
- For each match: create AlertDelivery with idempotency key
  - idempotency_key = SHA256(org_id + user_id + rule_id + opp_id + material_version + channel)
- Emit to send-notification queue per channel
```

Idempotency: `organization_id + user_id + rule_id + opportunity_id + material_version + channel`

### 3.6 Notification Worker

- **Queue:** `send-notification`
- **Input:** `AlertDelivery` messages
- **Output:** Delivery to Telegram or FCM

```
send_notification(delivery: AlertDelivery) → DeliveryResult
- Check idempotency: if already sent, skip
- Route by channel:
  → Telegram: call Bot API with safe title, summary, deep link URL
  → FCM: send minimal push payload (notification_id, opp_id, title, summary, route)
- Record provider_message_id on success
- Set delivery_status to sent/failed/suppressed
- On permanent failure: suppress future deliveries for this rule+user combo? flag for ops
```

Idempotency: `organization_id + user_id + rule_id + opportunity_id + material_version + channel`

### 3.7 Outbox Worker

- **Purpose:** Guarantee at-least-once event publishing
- **Pattern:** Application service writes event to `outbox_events` table in same transaction as state change
- **Worker:** Polls `outbox_events WHERE status = 'pending'`, publishes to SQS/EventBridge, marks `published`

```
publish_outbox() → void
- SELECT * FROM outbox_events WHERE status = 'pending' ORDER BY created_at LIMIT 100
- For each event:
    sqs.send_message(event_queue, event.payload)
    UPDATE outbox_events SET status = 'published', published_at = NOW()
- On failure: retry with exponential backoff; never lose events between DB commit and queue send
```

### 3.8 Analytics Sink Worker

- **Queue:** `analytics-events`
- **Purpose:** Non-blocking analytics ingestion
- **Input:** Product events from API and workers
- **Processing:** Batch write to analytics store with trace context

---

## 4. Idempotency Rules

| Stage | Idempotency Identity | Duplicate Behavior |
|-------|---------------------|-------------------|
| Discover | source + scope + schedule_window | Skip window already processed |
| Fetch | source + external_id + adapter_version + checksum | Reuse existing raw snapshot |
| Parse | snapshot_id + parser_version | Reuse existing parsed listing |
| Normalize | parsed_listing_id + normalizer_version | Reuse existing normalized listing |
| Valuate | listing_id + material_version + valuation_version | Return existing valuation (idempotent) |
| Match alerts | org + user + rule + opp + material_version | Skip already matched |
| Notify | org + user + rule + opp + material_version + channel | Skip already sent; return original delivery status |

---

## 5. Failure Classification

| Error Type | Examples | Behavior |
|-----------|----------|----------|
| Transient | Network timeout, DB connection, throttle | Retry with exponential backoff; visibility timeout handles retry |
| Source-specific | Rate limit, auth expiry, schema change | Source-specific backoff; pause source after threshold; alert ops |
| Permanent | Invalid data, missing required field | Quarantine record; DLQ with metadata; alert ops |
| Fatal | Corrupt message, unhandled exception | DLQ; alert ops; never infinite loop |

---

## 6. DLQ Management

Each queue has a corresponding DLQ:

```
{queue_name}-dlq
```

DLQ messages contain:
- Original message body
- Error message and type
- Trace ID
- Attempt count
- Timestamp

Operations tools provide:
- DLQ browser (filter by source, error type, age)
- Replay capability (individual or batch)
- Discard capability (with audit trail)
- Source pause threshold (too many DLQ messages from one source → auto-pause)

---

## 7. Concurrency and Scaling

| Worker | Scaling Signal | Min | Max |
|--------|---------------|-----|-----|
| Discovery | Scheduled; near-constant | 1 | 1 |
| Fetch | Queue depth | 1 | Per-source concurrency limit × sources |
| Normalize | Queue depth | 1 | Source_count × avg_listings_per_discovery |
| Valuate | Queue depth | 1 | Based on listing throughput |
| Alert Match | Opportunity creation rate | 1 | Proportional to opportunity volume |
| Notify | Delivery queue depth | 1 | Per-provider rate limits |
| Outbox | Pending events count | 1 | 1-2 |
| Analytics | Batch size | 1 | 1-2 |

---

## 8. Tracing

Every job carries:
- `trace_id` — Single UUID connecting source discovery through customer action
- `source_job_id` — Discovery run identifier
- `idempotency_key` — Stage-specific deduplication key

Trace context is propagated through:
1. SQS message attributes (trace_id, source_job_id)
2. Database records (trace_id column on all pipeline tables)
3. OpenTelemetry spans (linked by trace_id)
