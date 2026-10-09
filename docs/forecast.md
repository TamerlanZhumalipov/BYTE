# BYTE AI Forecast v1

## Deploy

Update code and run `python manage.py migrate`, then restart Django. No new
packages, API keys or LLM calls. `/app/analytics/` replaces the old extrapolated
percentage with a bilingual exam-score estimate, bounds, evidence summary,
13-topic breakdown, recommendations and a retrospective 30-day history.

In admin:

1. Review ENT topic → root Section mappings. Set `forecast_weight` only with a
   documented rationale in the specification's RU/KZ weight-note fields. Default
   weight 1 means **equal model weights**, not an official exam allocation.
2. For contests, select the actual BYTE user on each ContestAccount and tag
   ContestTask with ENT topics (also available in the contest inline). Existing
   accounts are unlinked after migration. Nothing is inferred from names/logins.
3. For full mock results, create ENTPracticeResult with source, unique external
   reference, actual exam date, score/max, user and specification. Mark verified
   only after checking the result. This is the storage contract for the future
   variant module; there is no student self-report endpoint. The max must match
   the specification's full score (50 for informatics 2026).

Course-only forecasts work without steps 2–3 when enough topics have evidence.
No lesson unlock rules or existing quiz/AI endpoints are changed.

## Computation contract

`core.forecast.get_forecast(user, language='ru', year=None, now=None)` uses the
latest informatics specification at or before the as-of year, or an explicit
year. Authenticated GET `/api/ent/forecast/?language=ru|kk|kz` returns only
`request.user`'s data. It ignores user-ID parameters, prohibits writes, and sets
private/no-store cache headers. Reads never create history or change progress.
Missing/invalid specification gives `unavailable`, not a server error.

This is a heuristic baseline, **not a statistically calibrated predictor**.
Do not use its bounds as a confidence interval or promise exam accuracy.
The UI exposes the assumptions. Version: `byte-forecast-v1`.

- Evidence window: 180 days for tests/contests; full mocks 90 days. Future and
  invalid records are excluded. Time decay is `0.5 ** (age_days / 60)`.
- For each published mapped root quiz, average the latest 3 valid results by
  recency, with retry multipliers 1, 0.5, 0.25. Use correct_count/total_questions.
  Evidence mass is min(latest question count, 12) × time decay. Repeating a test
  does not grow independent sample size. A changed quiz has no stored question
  version today; this model therefore conservatively treats it as the same test.
- Shared roots split their evidence mass across ENT mappings, so they cannot
  multiply confidence. Each unique root is counted once in source statistics.
- Only explicitly linked contest accounts and tagged tasks contribute. Use the
  latest valid judged submission per task; exclude PENDING, invalid counts and
  zero totals. Each task contributes at most 2 × decay, split among linked ENT
  topics. Total contest mass is capped at 4 per topic. Passed judge cases are a
  weak proxy for exam mastery, not independent exam questions.
- Topic reliability = min(0.8, mass/(mass+4)) × mapped-root evidence coverage.
  When contests exist, the coverage factor has a minimum of 0.35. This caps
  confidence because broad root mappings may only partially cover a topic.
- Topic estimate = 0.5 + reliability × (observed score − 0.5). An unknown topic
  stays neutral internally (0.5), has a full [0,1] model interval, and displays
  no mastery or point estimate. Missing observations never imply mastered topics.
- Topic radius = 0.12 + 0.38 × (1 − reliability). Normalize configured weights,
  sum weighted estimates/radii, then scale by the specification max. Summing
  radii conservatively avoids assuming shared topic evidence is independent.
- Show course/contest score only with ≥3 distinct evidence sources, total mass
  ≥10, and weighted reliability ≥20%. Otherwise show insufficient data.
- With verified full mocks: average latest 3, using decay and multipliers
  1, 0.7, 0.49. Blend 75% mock / 25% topic model when topic reliability ≥20%;
  otherwise use the mock estimate alone. One mock allows an initial score.
  Mock radius is max(0.12, maximum deviation+0.08, 0.22−0.03×mock count).
  Overall bounds are clamped to [0,max_score]. No per-topic mastery is inferred
  from a full mock total. Topic contributions thus describe the topic component,
  not an additive decomposition of the mock-blended headline.
- Reliability label is at most medium, and only with ≥2 verified full mocks
  within 30 days; otherwise low. No high-accuracy claim is made.
- “Data coverage” is weighted topic reliability, not just mapped-topic count.
  It can remain below 100% with evidence on every topic. Mock totals cannot
  provide topic coverage. Course completion is shown by existing analytics;
  reading materials alone is not evidence of mastery and adds no score.

Historical points at −30/−21/−14/−7 days filter out later evidence and recompute
with the **current** mappings, ownership, verification flags and weights. This
is a retrospective calculation, not an immutable record of past predictions.
Trend is absent unless both endpoints have sufficient evidence. Decay can change
estimates even without a new attempt. GET performs 8 queries with quizzes alone,
9 with contest submissions when reading recommendations exist, independent of topic count. Evidence is loaded once
for all history points; very large histories may need database-side windowing.

## Validation and next calibration step

Run `python manage.py test core.tests`, `python manage.py check`, and
`python manage.py makemigrations --check --dry-run`.

Before presenting forecast accuracy as established, collect held-out exam scores
with consent, evaluate MAE and interval coverage, calibrate topic weights and
source reliability, and version the model. The default prior and thresholds are
explicit product assumptions. Do not fit and evaluate on the same mock results.
