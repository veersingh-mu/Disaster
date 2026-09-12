# Product Requirements Document
## Rapid Dam/Lake Breach Inundation Scenario Tool
### SIH 2026 — Problem Statement 26161

---

## 1. Product Name

**FloodPath** — Rapid Dam & Glacial Lake Breach Inundation Scenario Tool

---

## 2. Product Vision

To give disaster management authorities and HADR responders a fast, automated way to generate credible flood inundation scenarios for any dam or newly-formed glacial/landslide lake in India — turning a satellite-detected hazard into an actionable, village-level evacuation picture in minutes, not days.

---

## 3. Problem Statement

When a dam or landslide/glacial lake dam breaches, there is currently no fast, automated way to estimate how far the resulting flood will travel, how quickly, and which downstream settlements will be affected. Existing hydrodynamic modelling tools (HEC-RAS, MIKE) are accurate but require expert setup, licensed software, and hours-to-days of manual calibration per site — incompatible with the short timelines of sudden landslide-dam or GLOF events in the Himalayas. Open-source DEM data is coarse (30m), and no standardized pipeline currently connects hazard detection to a usable, decision-ready output.

---

## 4. Target Users

- District disaster management authorities (SDMA/DDMA) and district collectors
- NDMA and CWC (Central Water Commission) analysts
- NTRO and other remote-sensing/intelligence analysts monitoring high-risk terrain
- HADR (Humanitarian Assistance & Disaster Relief) response teams

---

## 5. User Personas

**Persona 1 — Anjali, District Disaster Management Officer**
Non-technical background, responsible for evacuation decisions. Needs a clear map and a plain-language summary ("these 4 villages, ~40 minutes"), not raw model output. Operates under extreme time pressure during an active event.

**Persona 2 — Rakesh, Remote Sensing Analyst (NTRO/CWC)**
Technical background, monitors satellite imagery for newly forming glacial/landslide lakes. Needs to quickly run "what if this breaches" scenarios for multiple candidate hazard sites and compare severity.

**Persona 3 — HADR Field Coordinator**
Needs a shareable, low-bandwidth-friendly output (map + summary) to coordinate relief resource positioning during or immediately after a breach event.

---

## 6. User Pain Points

- No fast way to model a *newly discovered*, unsurveyed lake or dam
- Existing tools require specialist hydraulic engineering skills the field/administrative users don't have
- Model outputs (hydrographs, raw rasters) are not directly actionable for evacuation decisions
- No standardized way to communicate uncertainty in breach behavior
- Coarse DEM data limits achievable accuracy, but this limitation is rarely communicated to end users

---

## 7. Proposed Solution

An automated, map-based web tool where a user selects a dam or lake location, the system fetches and conditions open DEM data, estimates breach parameters using established empirical formulas, runs a simplified but defensible flood-routing simulation, and returns a flood extent map with arrival-time estimates and a plain-language, village-level impact summary — validated against at least one real historical event (e.g., Rishi Ganga 2021).

---

## 8. Product Goals

- Reduce scenario-generation time from days (manual HEC-RAS setup) to minutes
- Make flood-scenario generation usable by non-hydraulic-engineering personnel
- Produce output that is directly actionable for evacuation decisions
- Demonstrate credible validation against a real historical breach event
- Communicate model uncertainty honestly rather than presenting false precision

---

## 9. Core Features

| Feature | Priority |
|---|---|
| Map-based site selection (dam/lake point) | Must Have |
| Automated DEM fetch (SRTM/ASTER) + conditioning | Must Have |
| Empirical breach parameter estimation (width, time, peak outflow) | Must Have |
| Simplified 2D flood-routing engine | Must Have |
| Flood extent + arrival-time visualization on map | Must Have |
| Plain-language village-level impact summary | Must Have |
| Historical case-study validation mode (e.g., Rishi Ganga replay) | Must Have |
| Uncertainty range on flood extent (not a single deterministic line) | Should Have |
| ML surrogate model for near-instant re-runs | Should Have |
| Multi-scenario comparison (different breach sizes) | Should Have |
| Population/settlement data overlay | Should Have |
| Satellite change-detection for new lake alerts | Could Have |
| Mobile/SMS alert integration | Could Have |
| Multi-language output | Could Have |
| Full 2D shallow-water equation solver (research-grade accuracy) | Won't Have (MVP) |
| Real-time continuous satellite monitoring pipeline | Won't Have (MVP) |
| Multi-country/global coverage | Won't Have (MVP) |

---

## 10. MVP Features

1. Map interface to select any dam/lake point in India (constrained demo region: Himalayan case-study rivers)
2. Automated open DEM fetch + basic hydrological conditioning
3. Empirical breach parameter estimation from dam/lake geometry (published formulas — no custom hydraulics research needed)
4. Simplified flood-routing engine (diffusive-wave or raster cellular-automaton spread model)
5. Visual flood extent map with time-based arrival estimates
6. Plain-language impact summary (villages affected, estimated arrival time)
7. At least one validated historical replay (Rishi Ganga 2021 or Kosi 2008) as proof of credibility

---

## 11. Non-MVP Features (Future)

- ML surrogate model trained on many simulation runs for near-instant results
- Uncertainty-band visualization
- Real-time Sentinel-1/2 satellite change-detection for automatic new-lake alerts
- Population and infrastructure overlay from census/OSM data
- Multi-scenario side-by-side comparison
- Mobile push/SMS alerting for last-mile warning
- Multi-language interface and reports
- Full research-grade 2D shallow-water solver integration

---

## 12. User Stories

- As a district disaster officer, I want to select a dam on a map and get an evacuation-relevant flood summary, so that I can make fast evacuation decisions.
- As a remote-sensing analyst, I want to input a newly detected lake's geometry and get a breach scenario, so that I can assess whether it poses an urgent hazard.
- As a HADR coordinator, I want a shareable summary of affected areas and arrival times, so that I can position relief resources ahead of the flood.
- As a judge/domain expert, I want to see the tool's output validated against a real historical event, so that I can trust its credibility.
- As a non-technical user, I want plain-language output instead of raw hydraulic data, so that I can act on it without specialist training.

---

## 13. Functional Requirements

- The system shall allow a user to select a point on a map representing a dam or lake.
- The system shall automatically retrieve DEM data for the selected region.
- The system shall estimate breach parameters (width, formation time, peak outflow) using established empirical relationships based on dam/lake volume and height.
- The system shall run a flood-routing simulation and output a time-stepped flood extent.
- The system shall overlay flood extent on a map with estimated arrival times to nearby settlements.
- The system shall generate a plain-language summary of impacted villages and estimated arrival windows.
- The system shall provide at least one pre-loaded historical case study for validation demonstration.

---

## 14. Non-Functional Requirements

- The simulation pipeline should complete within a demo-acceptable time frame (target: under a few minutes for a moderate watershed).
- The UI should be usable by a non-technical administrator without training.
- The system should clearly communicate the accuracy limitations of open-source DEM data.
- The system should be deployable as a web application accessible without specialized software installation.
- The system should degrade gracefully (clear error messaging) when DEM or satellite data is unavailable for a selected region.

---

## 15. Success Metrics

- Time from site selection to usable output (target: minutes, not hours)
- Accuracy of historical case-study replay against known/reported flood extent (qualitative validation)
- Clarity of output as judged by non-technical reviewers (can a judge understand the impact summary without explanation)
- Judge/mentor feedback on credibility of the uncertainty communication
- Successful demo run on at least one real Himalayan case study

---

## 16. Assumptions

- Open-source DEM data (SRTM/ASTER, 30m) is sufficient for a defensible demo-level scenario, with known accuracy limitations disclosed
- Empirical breach-parameter formulas (published in dam-safety literature) are an acceptable substitute for full geotechnical breach analysis in an MVP context
- A simplified flood-routing method (diffusive-wave/cellular automaton) is an acceptable substitute for a full 2D shallow-water solver at hackathon scope
- Historical case-study data (rainfall, flood extent reports) for at least one validation event is publicly available

---

## 17. Constraints

- Hackathon timeline prevents building or validating a full research-grade hydraulic solver
- No access to high-resolution LIDAR DEM data — limited to open 30m-resolution sources
- No real-time satellite feed integration feasible within hackathon scope
- Limited compute resources compared to what full 2D shallow-water modelling requires
- Team lacks dedicated hydraulic engineering expertise — must rely on established empirical/simplified methods rather than novel physics

---

## 18. Edge Cases

- Selected site has no meaningful downstream settlements within the DEM-covered area
- DEM data has voids/gaps at the selected location
- Dam/lake geometry input is unrealistic (e.g., near-zero volume) and produces a degenerate simulation
- Very large watershed selection causes simulation time to exceed demo-acceptable limits
- Historical case-study site's terrain has changed significantly since the reference event, affecting replay accuracy

---

## 19. Security/Privacy Requirements

- No personally identifiable information is collected from users of the tool
- Population/settlement data used for impact estimates should come from public/open sources (e.g., census, OSM) with no individual-level data
- If deployed with user accounts (e.g., for authority login), authentication and access control should follow standard practices (not required for hackathon MVP demo)
- Satellite/DEM data sources used should be open-license and properly attributed

---

## 20. Future Scalability

- Extend from Himalayan case-study rivers to pan-India coverage as DEM and validation data availability allows
- Integrate real-time satellite change-detection for continuous new-hazard monitoring rather than manual site selection
- Replace simplified flood-routing engine with a trained ML surrogate for near-instant, higher-fidelity results
- Integrate with national early-warning/alert infrastructure (NDMA alert systems, SMS gateways)
- Support multi-agency access with role-based permissions (district vs. state vs. central authority views)
- Incorporate crowd-sourced or IoT sensor ground-truth data to improve breach parameter estimation over time
