# Step 9C prediction and alert API

| Method and path | Behavior |
| --- | --- |
| `POST /api/v1/predict` | Accepts `{"features": {...}}` with every model feature. Values must be finite numbers or null. Returns the existing model, prediction, label, score and threshold fields plus `prediction_id` and nullable `alert_id`. |
| `GET /api/v1/predictions` | Returns prediction history as `{items, total, limit, offset}`. |
| `GET /api/v1/alerts` | Returns the same page structure and accepts optional `severity` and `status` filters. |
| `GET /api/v1/alerts/{alert_id}` | Returns the alert, its associated prediction, and status changes in chronological order. |
| `PATCH /api/v1/alerts/{alert_id}/status` | Accepts a body such as `{"status":"investigating"}` and returns the updated detail. |

List endpoints default to 50 rows, accept limits from 1 to 100 and nonnegative
offsets, and sort newest first with ID as a tiebreaker. Alert totals reflect
the selected filters. The list of required model inputs is available from
`GET /api/v1/model-info`. Interactive API documentation is served at `/docs`.

An alert starts `open`. Allowed transitions are `open → investigating`,
`investigating → open or resolved`, and `resolved → investigating or closed`.
A same-status update succeeds without adding an audit record. A missing alert
returns 404, an invalid transition returns 409, invalid request data returns 422,
and a database operation failure returns 503.

## Storage and severity

The existing XGBoost artifact supplies the prediction and its decision threshold.
A single transaction stores the prediction and, for an attack classification,
its alert. The database allows one alert per prediction. Each prediction
submission is a new inference record, including repeated feature payloads.

Revision `0002_add_threshold` adds the prediction threshold and defaults
historical rows to 0.5. Revision `0003_alert_status_history` adds the unique
constraint on `security_alerts.prediction_id` and the `alert_status_changes`
table with alert ID, previous status, new status, and timestamp. Status updates
lock the alert row and commit the change and audit row together.

If an older database contains multiple alerts for a prediction, the uniqueness
migration fails and rolls back. Review those rows and reconcile them before
retrying. Find affected IDs with:

```sql
SELECT prediction_id, COUNT(*) FROM security_alerts
GROUP BY prediction_id HAVING COUNT(*) > 1;
```

Attack severity starts at `low`. The inclusive thresholds for `medium`,
`high`, and `critical` default to 0.70, 0.85, and 0.95. Override them with
`ALERT_SEVERITY_MEDIUM`, `ALERT_SEVERITY_HIGH`, and
`ALERT_SEVERITY_CRITICAL`. The values must be strictly increasing and within
[0, 1].

## macOS startup and verification

From the checkout root, use Python 3.11 or newer with compatible dependencies
and start Docker Desktop before running Compose.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
docker compose up -d --wait postgres
python -m alembic upgrade head
python -m pytest -q
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Keep the existing trusted `models/selected_model.json` and
`models/xgboost_model.joblib` in the checkout. These local artifacts are needed
for application startup and existing model tests.

In another terminal at the checkout root:

```bash
source .venv/bin/activate
curl --fail http://127.0.0.1:8000/health
python -m ml_training.scripts.test_prediction_api
curl --fail 'http://127.0.0.1:8000/api/v1/predictions?limit=5'
curl --fail 'http://127.0.0.1:8000/api/v1/alerts?status=open&limit=5'
```

The smoke script uses `data/processed/validation.csv`. The alert integration
tests default to SQLite for isolated runs. To run them against PostgreSQL, set
`STEP9C_TEST_DATABASE_URL` to a disposable, already migrated PostgreSQL
database using the `postgresql+psycopg://` scheme, then run
`python -m pytest -q backend/tests/test_prediction_alerts.py`. The tests write
persistent test records to that database.
