# UI/UX Design Brief
## FloodPath — Rapid Dam & Glacial Lake Breach Inundation Scenario Tool
### SIH 2026 — Problem Statement 26161

---

## Design Plan (Working Notes)

**Grounding:** This is a life-safety geospatial tool used in two very different moments — calm scenario-planning by an analyst, and urgent evacuation decision-making by a district officer under time pressure. The visual language should come from cartography and topographic survey work (the actual subject matter — DEMs, contour lines, elevation, water) rather than generic SaaS dashboard conventions. It should feel closer to a well-made field survey instrument than a startup product.

- **Color:** `#0F1B2B` (ink — primary text/chrome), `#1C2E42` (deep slate — panel/nav backgrounds), `#6B7785` (contour gray — secondary text, borders, inactive states), `#EDF1F4` (mist — light background, not a warm cream), `#1B4F72` (deep water — primary data/accent color, used for flood-extent and primary actions), `#E8A33D` (caution amber, reserved strictly for moderate-hazard indication), `#C0392B` (hazard red, reserved strictly for severe-hazard indication and destructive actions).
- **Type:** IBM Plex Sans for all UI and headline text (technical, legible, already associated with data/government-adjacent platforms — appropriate register without being decorative). IBM Plex Mono for coordinates, timestamps, and numeric readouts only — a functional use of monospace for real geodata, not a decorative label treatment.
- **Layout:** Map-dominant, split-pane — a persistent map/canvas occupies the primary visual field with a contextual side panel for controls and results, echoing the working layout of real GIS/survey tools rather than a card-grid dashboard.
- **Principles:** Clarity over decoration; the map and data are the interface, not a backdrop for UI chrome. Color carries meaning only (hazard severity, water depth) — never used decoratively. One deliberate moment of motion: the flood-extent time-slider animates the flood spreading across the map, which is the single memorable interaction of the whole product.

**Self-review against generic defaults:** Rejected the warm-cream/serif/terracotta look and the near-black/single-accent look — both are stylistic defaults unrelated to this subject. Rejected the SaaS rounded-card-grid pattern for the main working screens — this is a spatial data tool, not a content dashboard, so the map itself is the primary surface, with cards used only for secondary summary/list content. Monospace is used narrowly for genuine data (coordinates, timestamps), not as a label decoration. No ALL-CAPS eyebrows, no middle-dot meta strings, no arrow-suffixed buttons.

---

## 1. Design Philosophy

FloodPath is a decision-support instrument, not a marketing product. Every design choice should reduce the time and cognitive load between "a hazard exists" and "I know what to do about it." Clarity, restraint, and trustworthiness take priority over visual flourish. The map is the primary interface; UI chrome stays quiet and disciplined around it.

---

## 2. Visual Style

Cartographic and instrument-like: topographic contour motifs used sparingly as structural elements (not decoration), clean geometric panels, flat fills with no gradients except where they represent real data (water depth, elevation). No skeuomorphism, no glassmorphism, no decorative shadows beyond functional elevation cues.

---

## 3. Color System

| Token | Hex | Usage |
|---|---|---|
| Ink | `#0F1B2B` | Primary text, icons on light backgrounds |
| Deep Slate | `#1C2E42` | Navigation bar, side panel background |
| Contour Gray | `#6B7785` | Secondary text, borders, disabled states |
| Mist | `#EDF1F4` | App background |
| Surface White | `#FFFFFF` | Cards, form panels, modals |
| Deep Water (Primary) | `#1B4F72` | Primary buttons, active states, flood-extent base color |
| Water Scale (data) | `#BFE3F0` → `#1B4F72` → `#0B2E4A` | Sequential scale for flood depth visualization only |
| Caution Amber | `#E8A33D` | Moderate-hazard indicators only |
| Hazard Red | `#C0392B` | Severe-hazard indicators, destructive actions (e.g., delete scenario) |
| Success Green | `#3E8E5A` | Confirmation states only |

Color is functional, not decorative — amber and red never appear outside hazard-severity or destructive-action contexts.

---

## 4. Typography

- **Primary typeface:** IBM Plex Sans — used for all headings, body text, labels, and buttons.
- **Data typeface:** IBM Plex Mono — used only for coordinates, timestamps, numeric simulation readouts.
- **Type scale:** 
  - Display (page-level, rare): 32px / 40px line-height / Medium
  - H1 (screen title): 24px / 32px / Medium
  - H2 (section title): 18px / 26px / Medium
  - Body: 15px / 22px / Regular
  - Small/meta: 13px / 18px / Regular
  - Data/mono: 13px / 18px / Regular, IBM Plex Mono
- Line length capped near 70–75 characters for body/summary text.
- No all-caps labels; sentence case throughout.

---

## 5. Spacing

Base unit: 8px. Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64px. Panel padding: 24px. Form field vertical rhythm: 16px between fields. Section separation: 32px. Consistent application of the scale is more important than any individual value — no arbitrary one-off spacing.

---

## 6. Layout

Map-dominant split-pane structure for all core working screens:

```
┌─────────────────────────────────────────────┐
│ Top Nav (Deep Slate)                         │
├───────────────┬───────────────────────────────┤
│               │                               │
│  Side Panel   │        Map / Canvas           │
│  (controls,   │        (primary surface)      │
│   forms,      │                               │
│   results     │                               │
│   summary)    │                               │
│               │                               │
└───────────────┴───────────────────────────────┘
```

Dashboard and list-based screens (past runs, case studies) use a simpler single-column card list rather than the split-pane, since there is no map focus on those screens.

---

## 7. Navigation

Persistent top nav bar (Deep Slate background, Surface White text) with: Dashboard, New Scenario, Case Studies, Profile. Contextual back-navigation within the core flow (Site Selection → Configuration → Results) shown as a simple breadcrumb, not a stepper with numbered markers (this flow is not a fixed linear sequence the user always completes in order — they may jump back).

---

## 8. Buttons

- **Primary:** Deep Water fill, white text, 8px corner radius. Used for one primary action per screen (e.g., "Run simulation").
- **Secondary:** White fill, Deep Water border and text. Used for supporting actions (e.g., "Edit configuration").
- **Destructive:** Hazard Red fill, white text. Used only for irreversible actions (e.g., "Delete scenario").
- **Disabled:** Contour Gray fill at reduced opacity, no hover state.
- Button labels are verbs describing the exact result ("Run simulation," "Save changes"), never "Submit" or "OK."

---

## 9. Forms

Single-column layout, label above field, 16px vertical rhythm. Inline validation appears directly below the field on blur, in Hazard Red text with a specific corrective message. DEM-derived auto-filled fields are visually marked (subtle Contour Gray helper text: "estimated from terrain data — adjust if known") rather than presented as user-entered values. Required fields marked with a plain asterisk, no color-only indication.

---

## 10. Cards

Used for dashboard summary content only (past runs, case study list) — not used for the core map-based flow. White surface, 1px Contour Gray border (not a soft shadow), 8px corner radius, 24px internal padding. Each card shows: title, one-line meta (date/location), and a single primary action.

---

## 11. Tables

Used for the village-level impact list in Results. Left-aligned text, right-aligned numeric columns (arrival time, distance), IBM Plex Mono for numeric cells. Row hover state in Mist background. No zebra striping — rely on spacing and hairline row dividers for scanability.

---

## 12. Modals

Reserved for irreversible or high-consequence confirmations only (e.g., "Delete this scenario?"). Centered, Surface White, 32px padding, single clear action pair (Cancel / Confirm). Not used for supplementary content that could instead live inline or in the side panel.

---

## 13. Alerts

Inline banner style, not floating toasts, for anything the user needs to act on (e.g., data-coverage warnings). Severity-coded left border (Amber for caution, Red for error, Green for success, Deep Water for neutral info) with plain-language message text — no icon-only alerts.

---

## 14. Dashboards

Single-column card list: "Start new scenario" prompt/CTA at top when empty or as a persistent action, followed by past-runs list, followed by featured historical case studies. No decorative KPI tiles or metrics that aren't backed by real user data.

---

## 15. Charts

- **Time-slider flood progression:** the primary "chart" is the map itself with a horizontal time scrubber below it — this is the product's signature interaction.
- **Arrival-time bar list:** simple horizontal bars per affected village, sorted by arrival time, Deep Water fill, labeled directly (no separate legend needed).
- Avoid decorative chart types (no gauges, no donut charts) — this data is spatial and temporal, and should stay in map/timeline form wherever possible.

---

## 16. Icons

Simple line icons (1.5px stroke), no filled/duotone style, consistent 20px grid. Icons always paired with a text label in navigation and buttons — never icon-only for primary actions, to keep the tool usable by non-technical district-officer users under time pressure.

---

## 17. Responsive Behavior

Breakpoints: Desktop (≥1200px, full split-pane), Tablet (768–1199px, collapsible side panel that overlays the map on demand), Mobile (<768px, see Section 18). Map remains the dominant element at all breakpoints; side panel content reflows below or into a drawer rather than being cut.

---

## 18. Mobile UX

Given the HADR field-coordinator persona, mobile usability matters beyond a courtesy breakpoint. Map full-bleed with a bottom sheet (not a side panel) for configuration/results content, expandable by drag. Primary action button fixed at the bottom of the viewport, always reachable by thumb. Forms simplified to essential fields only on mobile, with an option to "adjust advanced parameters" that expands the full form.

---

## 19. Accessibility

- Minimum contrast ratio 4.5:1 for body text (all core palette pairings verified against this).
- Visible keyboard focus states on all interactive elements (2px Deep Water outline).
- Color never used as the sole indicator of hazard severity — severity also stated in text ("Moderate," "Severe").
- Respect `prefers-reduced-motion` — disable the time-slider flood animation's automatic playback for users with this preference; scrubbing remains available.
- All map interactions have a non-map equivalent (e.g., a search/list-based site selector alongside map-click selection).

---

## 20. Loading States

Multi-step pipeline loading (Simulation Execution) shows named stages with a progress indicator, not a generic spinner — the user should always know which stage is running ("Fetching terrain data," "Estimating breach parameters," "Running flood simulation"). Skeleton placeholders (flat Mist-colored blocks, no shimmer animation) for list/card content. Map tiles load progressively with no blocking overlay.

---

## 21. Empty States

Plain-language, action-oriented per the app flow's specification — e.g., "No scenarios yet — start your first one" with a direct primary button, not a decorative illustration. Empty states are treated as an invitation to act, written in the interface's own voice.

---

## 22. Error States

Errors state exactly what happened and what to do next, in Hazard Red accent with plain text — no apologetic tone, no vague "something went wrong." Example: "Terrain data unavailable for this region. Try a location within the Himalayan belt (current coverage)." Failure/Retry screens (per App Flow Section 16) name the specific failed pipeline stage.

---

## 23. Success States

Understated — a Success Green inline confirmation (e.g., "Scenario saved") rather than a celebratory animation or modal, consistent with the tool's serious, instrument-like character.

---

## 24. Micro-interactions

Deliberately minimal. The one designed moment of motion is the time-slider scrub on the Results screen animating flood extent spreading across the map — this is the product's signature interaction and should feel smooth and direct (updates tied to slider position, no separate play/pause animation loop by default). Button and form-field state changes (hover, focus, disabled) use simple, fast transitions (120–150ms) with no bounce or elastic easing. No decorative hover animations on cards or list rows beyond the background-color shift noted in Section 11.

---

## Screen-by-Screen UI Requirements

### Landing Page
Full-bleed hero using a static, muted topographic map of the Himalayan belt as background texture (not a stock photo), Deep Slate overlay panel with product name, one-sentence description, and a single primary CTA ("Enter tool"). No secondary marketing sections needed for a hackathon demo — keep it to one screen.

### Authentication
Centered white card (max-width 400px) on Mist background, IBM Plex Sans form, role-selection presented as large tappable option cards for demo mode rather than a dropdown, given time pressure on district-officer users.

### Onboarding
3–4 full-screen steps, Deep Water accent illustrations built from simple line-art (map pin, contour lines, water-drop motif) — consistent with the cartographic visual language, not generic onboarding stock icons. Skip option always visible.

### Dashboard
Single-column card list per Section 14. Persistent "New scenario" primary button in the top-right of the content area.

### Site Selection (Map)
Full-bleed map, floating search bar top-left (Surface White, subtle border, no shadow), selected-point marker in Deep Water. Side panel appears once a point is selected, showing coordinates (IBM Plex Mono) and a "Confirm location" primary button.

### Scenario Configuration Form
Side panel form per Section 9, map remains visible and interactive on the right so the user retains spatial context while configuring.

### Simulation Loading
Side panel shows the staged progress indicator; map shows a subtle pulsing outline of the affected watershed being computed, reinforcing what's happening without a decorative full-screen loader.

### Results View
Map dominant with layer toggles (extent, depth, arrival time) as a compact control cluster top-right of the map. Time-slider fixed along the bottom of the map. Side panel shows the plain-language impact summary and the village table (Section 11) below the fold.

### Historical Case Studies List
Card list per Section 10, each card showing event name, year, and location; selecting one routes into the Results View pre-populated.

### Profile/Settings
Simple single-column form, same treatment as Section 9.

### Failure/Retry Screen
Centered content within the side panel (map remains visible but muted), Hazard Red accent icon, plain-language failure message, "Retry" primary and "Edit configuration" secondary buttons side by side.
