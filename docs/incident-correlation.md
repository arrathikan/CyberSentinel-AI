# Incident correlation

The prediction API still accepts its original 78-feature XGBoost vector.
Clients may also supply an optional `metadata` object alongside `features`.
The model receives only `features`. The processed data has destination port
and statistical features. The local raw CSV header inspected also lacks source
and destination IPs and event timestamps. Existing database rows lack reliable
correlation metadata, so this migration adds empty incident tables without
rewriting or backfilling alerts.

## Rules and storage

- Group attack alerts only when source IP, destination IP, destination port,
  TCP/UDP protocol, and an observed timestamp with an explicit timezone are
  supplied. Optional source port is validated and excluded from the key.
  Destination port is taken from the metadata supplied by the collector.
- The source and destination identities and the destination service must match
  exactly. The complete incident's observed-time span must fit inside
  `INCIDENT_WINDOW_SECONDS` (default 300, inclusive).
- Only open and investigating incidents qualify. If multiple incidents qualify,
  prefer the most recent last-seen time, then the highest incident ID. Late
  arrivals may expand the interval inside the window. Existing incidents are
  never merged automatically. Incident severity is the highest member severity.
- Missing metadata, an unset secret, or a timestamp more than five minutes
  ahead leaves the alert ungrouped. Dissimilar complete flows start separate
  incidents regardless of model score. Correlated alerts are a review signal.
  Confirming an attack requires independent evidence.

Set a shared, private `INCIDENT_CORRELATION_SECRET` of at least 32 characters
across API replicas. The database stores a keyed HMAC of the matching tuple,
not the raw endpoint addresses or ports. Changing the secret starts new groups.
PostgreSQL transaction-scoped advisory locks serialize writers with the same
key. Membership is unique per alert. The prediction, alert, incident, and
membership share one transaction. A repeated prediction POST is a new inference,
while reprocessing the same alert with valid metadata returns its existing
membership.

Alembic revision `0005_incident_correlation` adds `incidents` and
`incident_alerts`. Membership rows store the observed event time and a generic
reason and reference both original alerts and incidents. The APIs expose
neither raw identifiers nor correlation keys. Timestamp and membership records
can still be sensitive. Deploy the endpoints behind the same trusted internal
gateway as prediction and alerts. The application currently has no built-in
authentication. Restrict database access and set incident retention according to
the deployment's policy. Deleting an expired incident cascades its membership
rows while preserving original alerts. Administrative re-correlation is omitted
because historical raw metadata and application-level administrator
authorization are unavailable.

The rule cannot disambiguate hosts behind shared addresses, correlate across
address changes, or prove common intent. Use metadata supplied by a trusted
collector. Shared database deployments need separate correlation namespaces
before accepting events from multiple independent tenants.

## API

| Endpoint | Response |
| --- | --- |
| `GET /api/v1/incidents?status=open&severity=critical&limit=50&offset=0` | Incident page ordered by last event time. Both filters are optional. |
| `GET /api/v1/incidents/{incident_id}` | Incident details. |
| `GET /api/v1/incidents/{incident_id}/alerts?limit=50&offset=0` | Original alerts with timestamps and correlation reasons, ordered by observed time. |
| `GET /api/v1/alerts/{alert_id}/incident` | Incident and the reason for this membership. Returns 404 when no membership exists. |

An example metadata object to place beside the complete `features` map:

```json
{
  "source_ip": "192.0.2.10",
  "destination_ip": "198.51.100.20",
  "destination_port": 443,
  "protocol": "tcp",
  "observed_at": "2026-11-27T12:00:00Z"
}
```

The alert lookup returns the incident object and, for a matching member, a
reason such as `Matched source IP, destination IP, destination port and protocol
within the 300-second event window.`

## macOS, Docker, and evaluation

Follow the [base setup](step-9c-api.md) for Python and the existing model.
Start Docker Desktop and, from the checkout root, run:

```bash
docker compose up -d --wait postgres
export INCIDENT_CORRELATION_SECRET="$(openssl rand -hex 32)"
python -m alembic upgrade head
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

To exercise concurrency, point `STEP9C_TEST_DATABASE_URL` at a separate,
disposable migrated PostgreSQL database. Tests write to that database.

```bash
DATABASE_URL="$STEP9C_TEST_DATABASE_URL" python -m alembic upgrade head
python -m pytest -q
```

The labeled fixture compares all 28 alert pairs across eight alerts, including
a window boundary, a late arrival, distinct sources, different destinations,
and different services. A false grouping is a pair assigned the same incident
despite different expected labels. A missed grouping is a pair assigned
different incidents despite a shared expected label. The fixture expects zero
of both. These counts measure those constructed scenarios. Performance on real
telemetry requires independently labeled incidents.
