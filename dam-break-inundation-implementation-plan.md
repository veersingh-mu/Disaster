# Implementation Plan
## FloodPath — Rapid Dam & Glacial Lake Breach Inundation Scenario Tool
### SIH 2026 — Problem Statement 26161

Each phase is scoped to be independently buildable and testable before the next begins. MVP functionality (per the PRD) is prioritized throughout; Should/Could-Have items are explicitly deferred to their own sub-steps within relevant phases rather than blocking MVP delivery. Phase order follows the requested sequence, with one adjustment noted in Phase 6.

---

## Phase 1: Project Setup

**Objective:** Establish the repository, tooling, and skeleton services so every subsequent phase has a working foundation to build on.

**Tasks:**
- Initialize monorepo structure: `/frontend` (React + Vite + TypeScript), `/backend` (FastAPI + Python), `/worker` (simulation pipeline, shares backend's Python environment/package).
- Set up linting/formatting (ESLint/Prettier for frontend, `ruff`/`black` for backend).
- Configure Docker Compose for local development: backend, worker, PostgreSQL+PostGIS, frontend dev server.
- Set up `.env.example` files per the Technical Requirements Document's environment variable list.
- Initialize Git repository with a basic CI workflow stub (lint + build only at this stage).

**Files/components affected:** Repo root config, `/frontend` scaffold, `/backend` scaffold, `/worker` scaffold, `docker-compose.yml`, `.env.example`.

**Dependencies:** None — this is the starting point.

**Expected result:** `docker-compose up` brings up an empty but running frontend, backend, and database, all able to talk to each other on a health-check level.

**Testing requirements:** A trivial `GET /health` endpoint returns 200; frontend dev server loads a placeholder page without console errors.

**Acceptance criteria:**
- [ ] All services start via a single command with no manual steps.
- [ ] Lint and format checks pass on empty scaffolds.
- [ ] `.env.example` covers every variable named in the Technical Requirements Document.

---

## Phase 2: Database

**Objective:** Implement the full schema from the Database Schema document, migration-managed, with seed data.

**Tasks:**
- Set up a migration tool (`alembic`) in `/backend`.
- Write migrations for all 8 tables (`users`, `scenarios`, `simulation_runs`, `flood_results`, `settlements`, `affected_settlements`, `case_studies`, `exports`), including all enums, constraints, and indexes defined in the schema document.
- Write seed scripts for: the system account, `settlements` reference data, and at minimum one fully pre-computed `case_studies` entry (Rishi Ganga 2021) with its backing scenario/run/flood_results rows.
- Verify PostGIS extension is enabled in the migration.

**Files/components affected:** `/backend/migrations/`, `/backend/seed/`.

**Dependencies:** Phase 1 (running Postgres instance).

**Expected result:** A fresh database, after running migrations and seed scripts, contains a valid schema and at least one browsable historical case study.

**Testing requirements:** Migration up/down tested for reversibility; a seed-data integrity test confirms the seeded case study has non-empty `flood_results` and `affected_settlements` rows.

**Acceptance criteria:**
- [ ] Schema matches the Database Schema document exactly (tables, types, constraints, indexes).
- [ ] Migrations run cleanly from empty on a fresh database.
- [ ] Seed data includes a complete, queryable case study.

---

## Phase 3: Authentication

**Objective:** Implement JWT-based login and the two-role (`analyst`/`guest`) model per the Technical Requirements Document.

**Tasks:**
- Implement `POST /auth/login` with password hashing (`bcrypt`) verification against `users`.
- Implement JWT issuance (signed, short expiry) and a FastAPI dependency to decode/validate it on protected routes.
- Implement guest/demo-role handling as a session-only client-side flag, with no `users` row created.
- Build the frontend Auth screen (role-selection UI per the Design Brief) wired to `/auth/login`.

**Files/components affected:** `/backend/app/auth/`, `/backend/app/dependencies.py`, `/frontend/src/pages/Auth/`.

**Dependencies:** Phase 2 (`users` table must exist).

**Expected result:** A seeded analyst account can log in and receive a valid JWT; a guest session proceeds without a database row.

**Testing requirements:** Unit tests for password hashing/verification and JWT encode/decode; integration test for `/auth/login` success and invalid-credentials failure paths (matching the App Flow's inline error behavior).

**Acceptance criteria:**
- [ ] Valid credentials return a usable JWT; invalid ones return a clear 401 with no navigation.
- [ ] Guest mode requires no backend account creation.
- [ ] Protected endpoints reject requests with missing/invalid tokens.

---

## Phase 4: Backend Foundation

**Objective:** Establish the API's structural building blocks — request validation, error handling, logging, and role-based authorization — before any feature logic is built on top.

**Tasks:**
- Define Pydantic request/response models for every endpoint in the API Endpoints table (Technical Requirements Document), including coordinate range and enum validation.
- Implement the structured error-response format (`error_code`, `message`) and a global exception handler.
- Implement structured JSON logging with request IDs.
- Implement the row-level ownership authorization pattern (`user_id = current_user.id` filtering) as a reusable dependency.
- Set up the async job-queue mechanism (e.g., a lightweight queue such as `RQ` or `Celery` with Redis, or FastAPI `BackgroundTasks` if queue infrastructure is judged unnecessary at hackathon scale — decision recorded in code comments) connecting the API to the `/worker` service.

**Files/components affected:** `/backend/app/schemas/`, `/backend/app/errors.py`, `/backend/app/logging.py`, `/backend/app/dependencies.py`, `/backend/app/queue.py`.

**Dependencies:** Phase 3 (auth dependency reused here).

**Expected result:** A backend skeleton where any new endpoint automatically gets validation, structured errors, logging, and ownership checks by following the established pattern.

**Testing requirements:** Unit tests for the validation schemas' boundary cases (e.g., negative dam height rejected); a smoke test confirming a job can be enqueued and picked up by the worker.

**Acceptance criteria:**
- [ ] Invalid input to any schema returns a structured 422 error, never an unhandled exception.
- [ ] Every log line includes a request ID traceable across the API and worker.
- [ ] A test job placed on the queue is consumed by the worker process.

---

## Phase 5: Core Backend Functionality

**Objective:** Implement the actual simulation pipeline logic — DEM fetch, breach-parameter estimation, flood routing, and impact summary generation — as a standalone, testable module before wiring it to the API.

**Tasks:**
- Implement DEM fetch/caching from the open data source (OpenTopography/USGS), storing tiles in object storage.
- Implement empirical breach-parameter formulas (published dam-safety regressions) as pure functions.
- Implement the simplified flood-routing algorithm (diffusive-wave or cellular-automaton raster spread) producing time-stepped flood polygons.
- Implement the settlement-impact query (spatial join of flood polygons against `settlements`) producing `affected_settlements` rows with arrival times.
- Wire the full pipeline into the worker, updating `simulation_runs.current_stage` at each step and writing results to `flood_results`/`affected_settlements` on completion, or `error_stage`/`error_message` on failure.

**Files/components affected:** `/worker/pipeline/dem.py`, `/worker/pipeline/breach.py`, `/worker/pipeline/routing.py`, `/worker/pipeline/impact.py`, `/worker/run.py`.

**Dependencies:** Phase 2 (schema), Phase 4 (queue mechanism).

**Expected result:** Given a scenario's coordinates and configuration, the pipeline produces a complete, stored set of flood-extent time steps and an affected-settlements list, end to end, without any API/frontend involvement yet.

**Testing requirements:** Unit tests for breach-parameter formulas against known published values; a full pipeline test run against the seeded Rishi Ganga case study's known input, checked for a plausible (not necessarily pixel-exact) flood extent.

**Acceptance criteria:**
- [ ] Pipeline runs end to end on the seeded case study without manual intervention.
- [ ] Each stage's timing is logged (supports the PRD's success metric).
- [ ] A failure at any stage correctly sets `error_stage` and halts further processing.

---

## Phase 6: Core Backend API Endpoints

*(Reordered ahead of the originally-numbered "Stitch frontend integration" step — the API surface must exist before frontend integration can meaningfully begin. This is the one sequencing adjustment to the requested order.)*

**Objective:** Expose the Phase 5 pipeline and Phase 2 data through the full REST API defined in the Technical Requirements Document.

**Tasks:**
- Implement `POST /scenarios`, `GET /scenarios`, `GET /scenarios/{id}`, `DELETE /scenarios/{id}`.
- Implement `POST /scenarios/{id}/run` (enqueues a `simulation_runs` row and worker job) and `GET /scenarios/{id}/status`.
- Implement `GET /scenarios/{id}/results` (assembles flood-extent time steps + impact summary into the Results view's expected payload shape).
- Implement `GET /case-studies` and `GET /case-studies/{id}/results`.
- Implement `GET /dem/preview` (auto-fill estimates for the Configuration Form).
- Implement `POST /scenarios/{id}/export`.

**Files/components affected:** `/backend/app/routers/scenarios.py`, `/backend/app/routers/case_studies.py`, `/backend/app/routers/dem.py`, `/backend/app/routers/exports.py`.

**Dependencies:** Phases 3, 4, 5.

**Expected result:** Every endpoint in the Technical Requirements Document's API table is live, authenticated, and returns correctly-shaped data against the seeded database.

**Testing requirements:** Integration tests per endpoint covering success, not-found, and unauthorized-access (wrong user) cases; a test verifying `/case-studies/{id}/results` returns the seeded Rishi Ganga data correctly.

**Acceptance criteria:**
- [ ] All endpoints match the documented request/response contracts.
- [ ] Ownership checks prevent a user from accessing another user's scenario.
- [ ] `/scenarios/{id}/status` correctly reflects live pipeline progress during a run.

---

## Phase 7: Frontend Integration ("Stitch")

**Objective:** Connect the React frontend to the now-complete backend API, implementing the App Flow's screens end to end for the core happy path.

**Tasks:**
- Build the API client layer (typed fetch wrappers matching backend Pydantic response shapes).
- Implement Dashboard, Site Selection (map), Configuration Form, Simulation Loading (polling), and Results View screens per the App Flow and Design Brief.
- Implement navigation between these screens per the App Flow diagrams.
- Wire the Historical Case Studies list and detail view.

**Files/components affected:** `/frontend/src/api/`, `/frontend/src/pages/Dashboard/`, `/frontend/src/pages/SiteSelection/`, `/frontend/src/pages/Configuration/`, `/frontend/src/pages/Results/`, `/frontend/src/pages/CaseStudies/`.

**Dependencies:** Phase 6 (full API surface), Phase 3 (auth).

**Expected result:** A logged-in user can select a site, configure a scenario, run it, watch progress, and view results — and separately, browse and open the seeded historical case study — entirely through the UI.

**Testing requirements:** Component tests for the Configuration Form's validation states; one Playwright end-to-end test covering the full happy path (per the Technical Requirements Document's testing strategy).

**Acceptance criteria:**
- [ ] The full happy-path flow (site selection → configuration → run → results) works without manual API calls.
- [ ] The historical case study is viewable via the same Results component used for live runs.
- [ ] Loading states (staged progress indicator) render correctly during a real run.

---

## Phase 8: Core User Feature Depth

**Objective:** Complete the remaining MVP-critical UI/UX detail beyond the bare happy path — empty states, the impact table, layer toggles, and the time-slider interaction.

**Tasks:**
- Implement the Results view's map layer toggles (extent, depth, arrival time) and time-slider scrubbing against `flood_results` time steps.
- Implement the village-level impact table (sorted by arrival time) from `affected_settlements`.
- Implement all documented empty states (no scenarios yet, no point selected, no settlements affected).
- Implement Export/Share actions against `POST /scenarios/{id}/export`.

**Files/components affected:** `/frontend/src/pages/Results/TimeSlider.tsx`, `/frontend/src/pages/Results/ImpactTable.tsx`, `/frontend/src/components/EmptyState.tsx`, `/frontend/src/pages/Results/Actions.tsx`.

**Dependencies:** Phase 7.

**Expected result:** The Results screen matches the Design Brief and App Flow specification in full, including the product's signature time-slider interaction.

**Testing requirements:** Component tests for time-slider scrubbing updating the displayed flood layer; manual UX review against the Design Brief's Section 24 (micro-interactions).

**Acceptance criteria:**
- [ ] Time-slider scrubbing feels immediate (pre-computed steps, no re-fetch per scrub).
- [ ] Every empty state defined in the App Flow renders correctly and is reachable in testing.
- [ ] Export produces a downloadable file matching the `exports` schema.

---

## Phase 9: AI Integration (Stretch, Should-Have)

**Objective:** Add the ML surrogate model for near-instant repeat scenario results, as scoped as a stretch goal in the PRD and Technical Requirements Document — built only after MVP (Phases 1–8) is functioning.

**Tasks:**
- Generate a training dataset by running the Phase 5 pipeline across a range of synthetic breach parameters.
- Train a surrogate regression model (e.g., gradient-boosted trees) to predict flood-extent characteristics from breach parameters.
- Add a `POST /scenarios/{id}/run?mode=fast` (or equivalent) path that uses the surrogate instead of the full pipeline, clearly labeled in the UI as an estimate.
- Add a comparison view/metric demonstrating surrogate speed vs. full pipeline speed (a strong demo point per the Problem Analysis).

**Files/components affected:** `/worker/ml/train.py`, `/worker/ml/predict.py`, `/backend/app/routers/scenarios.py` (extended), `/frontend/src/pages/Results/` (mode indicator).

**Dependencies:** Phase 5 (needs the full pipeline to generate training data), Phase 6/7 (API and UI to expose it).

**Expected result:** A working demonstration of "full solve: N minutes vs. surrogate: seconds" without misrepresenting the surrogate's accuracy to the user.

**Testing requirements:** Model validation against held-out full-pipeline runs (basic accuracy/error reporting, not a rigorous ML test suite at this scope); UI test confirming the surrogate result is visibly labeled as an estimate.

**Acceptance criteria:**
- [ ] Surrogate results are never presented as equivalent in confidence to a full pipeline run.
- [ ] Speed improvement is measurable and demonstrable.
- [ ] MVP functionality (Phases 1–8) is unaffected if this phase is cut for time.

---

## Phase 10: External APIs

**Objective:** Finalize and harden integration with all third-party/open data sources, moving from development stubs to production-configured calls.

**Tasks:**
- Confirm production API keys/config for the DEM source, map tiles (MapLibre), and geocoding (Nominatim).
- Implement caching for DEM tiles and geocoding results to avoid redundant external calls (per the Technical Requirements Document's scalability notes).
- Add graceful fallback messaging when an external source is unavailable or returns no data for a selected region (feeding the App Flow's "unsupported region" error state).

**Files/components affected:** `/backend/app/integrations/dem.py`, `/backend/app/integrations/geocoding.py`, `/frontend/src/components/Map/`.

**Dependencies:** Phase 5 (DEM already integrated at pipeline level — this phase hardens and extends to geocoding/tiles), Phase 7 (map UI).

**Expected result:** All external dependencies are configured, cached, and fail gracefully rather than crashing the pipeline or UI.

**Testing requirements:** Integration tests using recorded/mocked external responses (to avoid flaky tests depending on live third-party uptime); a manual test selecting a location outside DEM coverage to confirm the correct error message appears.

**Acceptance criteria:**
- [ ] No external API call lacks a timeout and fallback error path.
- [ ] Repeated requests for the same region are served from cache, not re-fetched.
- [ ] Out-of-coverage selections produce the documented error message, not a generic failure.

---

## Phase 11: Error/Edge Cases

**Objective:** Systematically implement every edge case named in the App Flow document.

**Tasks:**
- Implement handling for: DEM voids at selected location, degenerate/unrealistic dam geometry input, oversized watershed selection exceeding demo time limits, historical case study terrain drift disclosure.
- Implement the Failure/Retry screen fully, including "Edit configuration" pre-fill behavior.
- Review and implement every Empty State and Error State listed in the App Flow and Design Brief not already covered in Phase 8.

**Files/components affected:** `/backend/app/routers/scenarios.py` (validation extensions), `/worker/pipeline/` (defensive checks), `/frontend/src/pages/Failure/`.

**Dependencies:** Phases 6–8.

**Expected result:** No known edge case from the design documents produces an unhandled crash or a confusing/blank UI state.

**Testing requirements:** A dedicated edge-case test suite, one test per documented case; manual QA pass against the App Flow's Section 11–14 checklist.

**Acceptance criteria:**
- [x] Every edge case listed in the App Flow has a corresponding automated test.
- [x] Retry after failure re-uses prior input without requiring full re-entry.
- [x] No edge case results in a stuck loading state (all paths terminate in success, error, or empty).

---

## Phase 12: Testing

**Objective:** Consolidate and fill gaps in the test suite per the Technical Requirements Document's testing strategy, ensuring coverage across all layers before the security/performance/deployment phases.

**Tasks:**
- Audit unit test coverage for breach-parameter formulas and flood-routing logic.
- Audit API integration test coverage against the full endpoint table.
- Audit frontend component test coverage for Configuration Form and Results states.
- Finalize the end-to-end Playwright happy-path test and add one covering the failure/retry path.

**Files/components affected:** `/backend/tests/`, `/frontend/tests/`, `/e2e/`.

**Dependencies:** All prior phases.

**Expected result:** A test suite that can be run in CI and gives confidence the demo path (and its most likely failure modes) will behave correctly live.

**Testing requirements:** This phase *is* the testing requirement — target: all critical-path tests passing in CI, coverage gaps documented for anything intentionally deferred.

**Acceptance criteria:**
- [x] CI runs the full test suite on every push.
- [x] Happy-path and failure/retry E2E tests both pass reliably (no flakiness) in CI.
- [x] Any known, deliberately deferred test gap is documented, not silently missing.

---

## Phase 13: Security

**Objective:** Apply the security requirements from the Technical Requirements Document as a final hardening pass.

**Tasks:**
- Confirm HTTPS enforcement at the deployment layer.
- Verify JWT expiry, signing secret strength, and secure storage on the frontend.
- Verify CORS is restricted to known origins only.
- Review input validation coverage (Phase 4/11) specifically for injection/abuse vectors (e.g., malformed geometry payloads).
- Confirm rate limiting is active on `/scenarios/{id}/run`.
- Run a dependency vulnerability scan on both frontend and backend packages.

**Files/components affected:** `/backend/app/middleware.py`, deployment config, `package.json`/`requirements.txt` audit.

**Dependencies:** Phases 4, 6, 7.

**Expected result:** The application meets the security baseline defined in the Technical Requirements Document with no outstanding high-severity findings.

**Testing requirements:** Automated dependency scan (`npm audit`, `pip-audit`) with no unresolved high/critical findings; manual verification of CORS and rate-limit behavior.

**Acceptance criteria:**
- [x] No secrets present in source control history.
- [x] Rate limiting demonstrably blocks rapid repeated `/run` calls.
- [x] Dependency scans show no unaddressed high/critical vulnerabilities.

---

## Phase 14: Performance

**Objective:** Validate the application meets the performance expectations set in the Technical Requirements Document, and optimize the specific paths most visible in a live demo.

**Tasks:**
- Measure and log pipeline stage timings against the seeded case study; optimize any stage exceeding the target window.
- Verify interactive endpoints (dashboard, forms) respond within the ~300ms target under normal load.
- Verify DEM/geocoding caching (Phase 10) is measurably reducing repeat-request latency.
- Load-test the `/scenarios/{id}/run` → worker path for a small number of concurrent runs (demo-realistic scale only, per the Technical Requirements Document's explicit deferral of full load testing).

**Files/components affected:** Worker pipeline (targeted optimization), caching layer.

**Dependencies:** Phases 5, 9, 10.

**Expected result:** The demo path performs predictably and within the documented expectations, with no surprises during a live run.

**Testing requirements:** Benchmark script producing timing reports for the pipeline and key API endpoints, checked in for repeatability.

**Acceptance criteria:**
- [x] Full pipeline run on the demo case study completes within the documented multi-minute target.
- [x] Interactive endpoints meet the ~300ms target in benchmark runs.
- [x] Caching produces a measurable improvement on repeat requests.

---

## Phase 15: Deployment

**Objective:** Deploy the complete application per the Technical Requirements Document's platform recommendations, ready for live demo access.

**Tasks:**
- Deploy frontend to Vercel/Netlify from the main branch.
- Deploy backend and worker (Dockerized) to Render/Railway, with the background worker configured as a separate service/process type.
- Provision managed PostgreSQL+PostGIS on the same platform.
- Configure all production environment variables/secrets.
- Run migrations and seed scripts against the production database.
- Perform a full smoke test of the live deployment (login → scenario → run → results, and case-study replay).

**Files/components affected:** Deployment platform configuration, CI/CD pipeline (extend Phase 1's stub to deploy on merge to `main`).

**Dependencies:** All prior phases.

**Expected result:** A publicly reachable URL running the complete application, demo-ready.

**Testing requirements:** Manual smoke test of the live deployment covering the same happy path as the Phase 7/12 E2E test, executed against production infrastructure.

**Acceptance criteria:**
- [x] Live URL is reachable and the full happy path works end to end in production.
- [x] The seeded historical case study is viewable live.
- [x] Environment variables are correctly scoped (no local/dev values leaking into production).
