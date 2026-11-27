# CyberSentinel-AI development roadmap

Steps 9B and 9C provide PostgreSQL storage, trained XGBoost inference, atomic
prediction and alert creation, and an audited alert status workflow. See the
[Step 9C API guide](step-9c-api.md) for the current contract. All six features
below are planned unless explicitly marked implemented.

Each feature goes into its own sequential pull request with implementation,
automated tests, API or operator documentation, and a security review that
covers data access and retention. Verify CI before merging. Establish a
reproducible CI check before the first advanced-feature PR can merge. CI fixtures
should use synthetic data and trusted model artifacts without committing private
datasets or generated production artifacts.

## 1. Explainable Threat Detection

- **Architecture.** Compute XGBoost TreeSHAP contributions using the same
  ordered, imputed feature vector used for inference. Return the baseline,
  output scale, model version, and top signed contributions through an
  explanation API. Show positive and negative contributions in a dashboard.
- **Dependencies.** Existing predictor, a compatible SHAP version, trusted
  model fixtures, and an authenticated dashboard/API path for sensitive values.
- **Implementation.** Share preprocessing, expose an explanation endpoint,
  define contribution ordering and tie-breaking, and build the visualization.
  Compute explanations within the authorized request flow so raw features can
  remain transient. Document availability for historical predictions.
- **Tests.** Check additivity on the documented output scale, stability for
  repeated inputs, consistent model feature order, null input handling, and
  API validation.
- **Done when.** API and dashboard agree on the top contributors, fixture
  contributions reconstruct the model output within a documented tolerance,
  and the UI describes contributions as model behavior.

## 2. Evidence-Based Investigation Timeline

- **Architecture.** Link incident events and evidence in PostgreSQL. Record
  observed and ingested timestamps, source identifiers, and provenance.
  Serve a chronologically ordered, paginated investigation timeline.
- **Dependencies.** Incident identity, migrations, authorized evidence sources,
  and a retention policy for evidence references and excerpts.
- **Implementation.** Create event and evidence tables, define deterministic
  ordering, build the timeline API, and use distinct record types and UI labels
  for observed facts and AI conclusions. Require conclusions to cite evidence.
- **Tests.** Cover time zones, tied timestamps, missing provenance, pagination,
  access boundaries, and conclusion-to-evidence linkage.
- **Done when.** An analyst can reconstruct a fixture incident chronologically
  and trace each conclusion back to its evidence.

## 3. Network Behavior Drift Monitor

- **Architecture.** Version training reference distributions alongside the
  model. Compare aggregated observation windows using PSI or KS statistics.
  Store monitoring history and significant-change alerts in PostgreSQL.
- **Dependencies.** Training summaries, an approved feature collection path,
  sufficient samples per window, scheduled evaluation, and severity policy.
- **Implementation.** Define bins, windows, minimum sample sizes, and
  thresholds. Record sample counts and missingness. Expose drift history via
  an API and dashboard. Deduplicate alerts by feature, model and window.
- **Tests.** Compare stable, shifted, sparse and missing-data samples. Verify
  deterministic replay and alert deduplication.
- **Done when.** The monitor reproducibly surfaces controlled shifts, charts
  history, and explicitly reports insufficient samples.

## 4. Human-Approved Response Simulator

- **Architecture.** Generate defensive recommendations and pause execution at
  a LangGraph human-in-the-loop checkpoint. An authorized reviewer approves or
  rejects a plan. Approved plans run against simulation state and produce
  an audit record.
- **Dependencies.** Persistent checkpoints, reviewer identity and roles,
  evidence-backed inputs, and an isolated simulator.
- **Implementation.** Define simulated action types, implement approval and
  rejection, and record recommendation, decision, actor, timestamps, and
  outcome. Simulator adapters operate exclusively on mock state. Real firewall
  or host changes require a separately authorized future feature.
- **Tests.** Cover paused and rejected runs, unauthorized approval, retries,
  checkpoint recovery, and isolation from real systems.
- **Done when.** A reviewer can inspect and approve or reject a recommendation,
  reproduce an approved simulation, and trace the complete decision history.

## 5. Intelligent Alert Grouping (implemented)

See the [incident correlation guide](incident-correlation.md) for the API,
metadata requirements, and evaluation methodology.

- **Architecture.** Assign related alerts to incidents using bounded time
  windows and available host identifiers and network metadata. Persist
  membership and the basis for each correlation.
- **Dependencies.** Incident records, approved normalized metadata,
  deterministic identifiers, and evaluation fixtures with labeled groups.
- **Implementation.** Define correlation rules and handling for missing
  metadata. Design uniqueness and transactions for retries and concurrent
  alerts. Measure incorrect groupings and missed correlations on fixtures.
- **Tests.** Check replay, concurrent creation, late alerts, missing fields,
  unrelated alerts, and expected grouping metrics.
- **Done when.** Replay and concurrency produce one incident for each
  matching fixture group, and incorrect and missed grouping rates meet
  documented acceptance targets.

## 6. Detection Coverage and Blind Spot Map

- **Architecture.** Maintain a versioned catalog of available telemetry,
  tested detection categories, and evidence-backed MITRE ATT&CK mappings.
  Show tested, partial, and uncovered capabilities in a coverage view.
- **Dependencies.** Telemetry inventory, labeled test fixtures, test results,
  and reviewed ATT&CK references where the evidence supports a mapping.
- **Implementation.** Record telemetry prerequisites, dataset and model
  versions, test links, and review dates. Track category-level evidence and
  require explicit support for any technique-level claim.
- **Tests.** Validate coverage records, evidence links, status rendering, and
  rejection of unsupported technique claims.
- **Done when.** Every tested or partial claim traces to reproducible evidence
  and uncovered areas are visible alongside the telemetry needed to assess them.
