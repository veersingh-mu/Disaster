# Problem Statement 26161 — Dam Break Inundation Modelling Using Hydrodynamic Modelling
### Deep Strategic Analysis — SIH 2026

---

## 1. The Actual Problem

Strip away the jargon: **when a dam or natural landslide-formed lake breaches, nobody currently knows — in time to act — how much water will hit which villages, how fast, and how high.** The problem statement bundles two very different failure modes together, and this matters:

- **Engineered dam failures** (structural failure, overtopping) — rare, well-studied, decades of hydraulic engineering literature (HEC-RAS, MIKE 11, etc.)
- **Glacial Lake Outburst Floods (GLOF) / landslide dam breaches** (Rishi Ganga 2021, South Lhonak/Sikkim 2023, Kosi 2008) — the real driver of recent Himalayan disasters, far less predictable, forms and breaches on short notice, often with no prior survey data

NTRO (a *space-based intelligence agency*, not a water resources body) posting this tells you something: this is likely about **rapid scenario generation from remote sensing when a new obstruction is just spotted forming** — not slow, deliberate dam-safety auditing of existing structures. That reframes the whole problem from "run a hydrodynamic model" to "run a hydrodynamic model *fast, with almost no ground truth, under time pressure*."

---

## 2. Root Causes

- Terrain in the Himalayas changes faster than survey data is updated (new lakes, landslide dams form in weeks)
- Existing hydrodynamic tools (HEC-RAS, MIKE, DELFT3D) are accurate but require expert setup, licensed software, and hours-to-days of manual calibration — not built for "we spotted a new lake yesterday" urgency
- DEM (Digital Elevation Model) resolution from open sources (SRTM/ASTER, 30m) is too coarse for valley-scale flood extent accuracy — this is a real technical ceiling, not just a UX problem
- No standardized, repeatable pipeline connecting satellite detection → breach simulation → impact/evacuation output for *any* river, on demand

---

## 3. Target Users

- Disaster management authorities (NDMA, SDMA, district collectors) — need actionable evacuation maps, not hydraulic equations
- NTRO / defense & intelligence analysts — need fast scenario generation for strategic/security assessment (note: dams near borders, e.g., China-built dams upstream, are a real NTRO interest)
- HADR (Humanitarian Assistance & Disaster Relief) response teams — need real-time "where does the water go" during an active event, not just pre-event planning

---

## 4. Stakeholders

Central/state disaster management bodies, CWC (Central Water Commission), local administration, downstream population, dam-owning agencies, defense/intelligence (given NTRO), insurance/reinsurance bodies, NGOs doing HADR.

---

## 5. Existing Solutions & Weaknesses

| Solution | Weakness |
|---|---|
| HEC-RAS 2D | Gold standard accuracy, but steep learning curve, manual mesh/boundary setup, not automatable for "any river on demand" |
| MIKE 11/21 (DHI) | Proprietary, expensive licensing — a dealbreaker for a govt-wide "any river" tool |
| Academic GLOF studies (Rishi Ganga, Sikkim) | One-off, manually done post-disaster, not operational/real-time |
| Google/NASA flood forecasting initiatives | Focus on riverine/monsoon flooding, not sudden dam/lake-breach inundation |

**Challenge:** the real gap isn't "no hydrodynamic model exists" — it's that no one has made the *pipeline* (DEM ingestion → breach parameters → 2D flood routing → shareable evacuation output) fast and automated enough for non-specialists to run on short notice for an arbitrary, possibly newly-formed water body.

---

## 6. User Pain Points

- Setting up a hydrodynamic model per river/lake takes specialist time SIH teams won't have in production use
- Coarse open DEMs (30m ASTER/SRTM) don't resolve narrow Himalayan valleys well — flood extent errors compound downstream
- No easy way to convert model output into something a district administrator can act on in 10 minutes (they don't want a hydrograph, they want "evacuate these 4 villages, water arrives in 40 minutes")
- Breach parameters (breach width, formation time) for a landslide dam are inherently uncertain — any tool needs to communicate uncertainty, not pretend precision

---

## 7–9. Solution Opportunities, Core Functionality, AI Opportunities

Given a software/data-science team can't rebuild HEC-RAS's physics from scratch in a hackathon, the realistic move is: **don't reinvent 2D shallow-water solvers — wrap and automate them, and use AI/ML where it adds real leverage, not window dressing.**

**Automated pipeline concept:**
User draws/selects a dam or lake point on a map → auto-fetch DEM (SRTM/ASTER, or Bhoonidhi/Sentinel) → auto-delineate the breach location and downstream channel → feed into a simplified 2D shallow-water solver (or a pre-validated simplified breach model like NWS BREACH / physically-based empirical breach-width regressions) → output flood extent + arrival time + depth over time.

**AI opportunities that are genuine, not decorative:**
- ML-based rapid DEM correction/void-filling and stream-burning (real, known technique) to improve coarse DEM quality without needing high-res LIDAR
- Satellite image change-detection (Sentinel-1 SAR, cloud-penetrating) to auto-flag new/growing glacial lakes — this is a legitimate, high-value AI application NTRO would care about
- Surrogate ML model trained on many HEC-RAS/2D-solver runs to predict inundation extent near-instantly for new scenarios (physics-informed surrogate — genuinely novel and demo-able)
- **NOT**: generic "AI chatbot" bolted onto a flood map — reviewers will see through that instantly

---

## 10. MVP Features (Hackathon-Realistic)

1. Map interface — pick any river/dam/lake point in India
2. Auto-fetch open DEM + basic breach parameter estimation (empirical formulas: breach width/time from dam/lake volume — published, usable without deep hydraulics expertise)
3. Simplified 2D flood routing (even a diffusive-wave or raster cellular-automaton flood-spread model is acceptable and far more buildable than full shallow-water equations in a hackathon timeframe)
4. Visual output: flood extent polygon over time, arrival-time-to-village estimates, depth heatmap
5. Plain-language impact summary: villages affected, estimated arrival time, suggested evacuation zone

---

## 11. Future Features

- Real-time satellite monitoring integration for new lake detection
- Multi-scenario comparison (different breach sizes/timings)
- Population/infrastructure overlay with census data
- Mobile alert integration for last-mile warning
- Historical validation against Rishi Ganga/Kosi/Sikkim events
- Multi-language SMS/IVR alerting

---

## 12. Risks & Assumptions (Challenged)

- **Assumption to challenge**: that a student team can produce hydraulically *accurate* results. You almost certainly can't beat HEC-RAS accuracy in a hackathon — and shouldn't try. The winning move is speed, automation, and usability, not raw simulation fidelity.
- **Risk**: DEM resolution ceiling (30m) may cap accuracy regardless of modeling sophistication — this needs to be stated openly in the pitch, not hidden.
- **Risk**: over-promising "real-time" when actual compute time for even a simplified 2D solve over a large watershed may be minutes, not seconds.
- **Assumption to challenge**: that "any river" is truly in scope. A demo focused on 2–3 validated Himalayan case studies (Rishi Ganga, Kosi) will be far more credible than a vague "works for any river in India" claim with no validation.
- **Risk**: breach parameter uncertainty is irreducible — a tool that shows a single deterministic flood line without an uncertainty band will look naive to domain-expert judges.

---

## 13. Technical Challenges

- Automating DEM acquisition + preprocessing (void-filling, hydrological conditioning) without manual GIS work
- Choosing a flood-routing method that balances speed and credibility (full 2D shallow-water vs. simplified diffusive-wave/cellular automaton)
- Estimating breach parameters (width, formation time, peak outflow) for an *un-surveyed* landslide dam with only satellite-derived geometry
- Converting raster flood output into actionable, village-level impact summaries (needs settlement/population data overlay)
- Performance: running this fast enough to feel "real-time" in a demo

---

## 14. What Would Make the Solution Genuinely Useful

- Honest uncertainty communication (a flood *range*, not a single confident line)
- Validation against at least one real historical event (Rishi Ganga or Kosi) with a plausible-looking result — validation is what separates a toy from a tool
- An output format a non-technical district administrator can act on in minutes
- A pipeline that works from satellite detection to output with minimal manual GIS setup

---

## 15. What Would Make It Stand Out in the Hackathon

- Leading the pitch with a real historical case study replay (e.g., "here's what our tool would have shown before Rishi Ganga 2021") rather than an abstract feature list
- Demonstrating the AI/ML surrogate-speed angle concretely (e.g., "full 2D solve: 20 minutes; our surrogate: 4 seconds")
- Being upfront about accuracy limitations and how the tool complements, rather than replaces, expert hydraulic modeling
- A genuinely usable, clean UI aimed at a district administrator persona, not a GIS specialist

---

## Recommended Product Direction

Build an **automated rapid-scenario dam/lake-breach inundation tool**, not a full hydraulic modeling suite:

1. Map-based selection of any dam or lake (with 2–3 validated historical case studies as the demo backbone)
2. Automated DEM fetch + conditioning pipeline
3. A simplified but defensible flood-routing engine (diffusive-wave or cellular-automaton — buildable in hackathon time, with a clear roadmap to full 2D shallow-water)
4. An ML surrogate layer trained on simplified-solver runs to showcase genuine AI value (speed) without needing to be a hydraulics research lab
5. Clear, uncertainty-aware, plain-language output aimed at disaster-response decision-makers

This framing plays to a full-stack/rapid-prototyping team's actual strengths — data pipeline automation, mapping/visualization, and a credible AI-speed narrative — rather than competing on hydraulic-modeling accuracy against tools with decades of engineering behind them.
