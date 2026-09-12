## Brand & Style
This design system governs a critical life-safety geospatial simulation and breach assessment instrument. The aesthetic is unapologetically disciplined, tactical, and rigorous—rooted in physical cartographic tooling, hydro-meteorological command consoles, and field survey hardware.

The interface serves emergency managers, civil hydrologists, and disaster response teams who require immediate situational clarity under extreme pressure. Every pixel exists to communicate spatial veracity and quantitative precision; decorative visual effects, skeuomorphic illusions, and soft consumer abstractions are strictly prohibited. The system adopts an engineered, data-dense posture where visual hierarchy is dictated by typographic scale, technical line-weights, and strict geospatial color-coding.

## Layout & Spacing

The layout is an instrument-grade, map-first viewport workspace designed to preserve uninterrupted situational visibility.

### Layout Model
1. **Persistent Global Bar (`48px` fixed height)**: Rendered in Deep Slate (`#1C2E42`). Hosts system status, dataset identifiers, coordinates tracking, active run status, and primary workspace switchers.
2. **Primary Viewport (Dynamic Fluid Vector Plane)**: Maps and spatial telemetry canvas consume 100% of remaining width and height.
3. **Collapsible Split Inspection Docks**: 
   - **Left Dock (`320px` to `420px`)**: Parameter inputs, dam characteristics, breach geometry variables, and hydrograph controls.
   - **Right Dock (`420px` to `560px`)**: Simulation output analytics, cross-section elevation charts, downstream arrival matrices, and population impact summaries.
4. **Temporal Scrubber / Playback Bar (`72px` fixed bottom)**: Anchored over the bottom edge of the map, housing high-resolution time stepping, play/pause controls, and peak inundation markers.

### Responsive Behavior
- **Desktop Viewport (> 1280px)**: Persistent two-pane split with simultaneous parameter inputs, center map view, and real-time telemetry drawer.
- **Field Terminal / Tablet (768px - 1279px)**: Inspector drawers collapse into fixed-width sliding overlays (`panel-width-md`) triggered via top-nav icons. Spatial controls shift to compact vertical tool-strips docked to the map edge.
- **Tactical Mobile (< 767px)**: Viewport displays map-only mode with a bottom sheet modal architecture. Telemetry collapses to tabular cards expandable by swiping up; interactive map tools shift to a thumb-accessible right-side floating HUD.

## Elevation & Depth

Visual hierarchy is communicated through high-contrast boundary definition, structural layering, and hairline borders rather than ambient depth or drop shadows. This preserves crisp readability against high-contrast satellite raster layers and multi-band synthetic aperture radar (SAR) feeds.

### Depth Rules
- **No Decorative Shadows**: Do not apply blurred ambient shadows, colored glows, or diffuse elevation shadows to panels, cards, or inputs.
- **Hairline Graticule Borders**: All panels, cards, modals, and input fields use a crisp `1px` solid outline colored with Contour Gray (`#6B7785`) or Deep Slate (`#1C2E42` at 15% opacity).
- **Surface Layering**:
  - **Level 0 (Base)**: Dynamic WebGL Map Canvas / Raster Layers.
  - **Level 1 (Dock Frame)**: Solid Mist (`#EDF1F4`) structural backgrounds with `1px` borders.
  - **Level 2 (Active Panels & Inspection Cards)**: Solid Surface White (`#FFFFFF`) with `1px` Contour Gray border.
  - **Level 3 (Floating HUD & Map Controls)**: Surface White (`#FFFFFF`) with a `1px` solid Contour Gray border and a zero-blur hard technical offset (`box-shadow: 0 2px 0 0 rgba(15, 27, 43, 0.08)`).
  - **Level 4 (System Overlays / Breach Alerts)**: Deep Slate (`#1C2E42`) or Alert Red banner layers with absolute z-index priority.

## Components

### 1. Buttons & Control Triggers
- **Primary Action (Run Scenario, Commit Breach)**: Solid Deep Water (`#1B4F72`) background, Surface White (`#FFFFFF`) text, `0px` radius, `32px` standard height, uppercase `12px` IBM Plex Sans semi-bold tracking. Hover: `#0B2E4A`. Focus: `2px` solid `#0F1B2B` with `1px` white inner gap.
- **Secondary Action (Inspect Profile, Export Shapefile)**: Transparent background, `1px` solid Contour Gray (`#6B7785`), Ink (`#0F1B2B`) text. Hover: Mist (`#EDF1F4`) fill.
- **Hazard Action (Trigger Emergency Broadcast)**: Solid Hazard Red (`#C0392B`) background, white text. Active state: Flash inversion to Ink (`#0F1B2B`).

### 2. Status Chips & Telemetry Badges
- Built with a strict height of `20px`, padding `0 6px`, monospaced typography (`code-sm`).
- **Nominal State**: Background `#EDF1F4`, text `#1C2E42`, border `1px` solid `#6B7785`.
- **Warning State**: Background `#FFF8E7`, text `#A06800`, border `1px` solid `#E8A33D`.
- **Critical Alert**: Background `#FDF2F2`, text `#C0392B`, border `1px` solid `#C0392B`, prepended with a blinking square signal indicator.

### 3. Inspection Cards & Structural Panels
- Surface White (`#FFFFFF`) background, bounded by a `1px` solid Contour Gray (`#6B7785`) border.
- Header bars must feature a distinct `28px` sub-header block in Mist (`#EDF1F4`) with uppercase technical labels (`label-sm`) and explicit parameter units (`[m/s]`, `[m³]`, `[WGS84]`).

### 4. Input Fields & Parameter Steppers
- Input containers feature a rigid `32px` height, Surface White fill, and `1px` Contour Gray border.
- Floating focus: border shifts immediately to Deep Water (`#1B4F72`) without ambient outer ring glow.
- Numeric parameters (e.g., Lake Volume, Breach Width, Manning's Roughness $n$) must be rendered in JetBrains Mono (`code-md`) accompanied by a fixed right-side unit suffix lockup (`m³`, `m`, `s`).

### 5. Checkboxes & Toggle Radios
- Box size `14px x 14px`, `0px` border radius, `1px` solid Contour Gray.
- Checked state: Solid Deep Slate fill with an inner white cross-hair or check mark. Radio buttons use a centered `6px` square dot instead of a circular fill.

### 6. Specialized Domain Components
- **Hydrograph Cross-Section Inspector**: An inline SVG coordinate display mapping elevation vs. cross-channel distance. Depth fills use the hydrologic ramp (`#BFE3F0` to `#1B4F72`) paired with hairline dashed reference rules for peak water marks.
- **Temporal Timeline Scrubber**: A high-density chronological timeline bar situated along the bottom viewport edge. Milestones (e.g., "Breach Initiation", "Peak Discharge", "Terminal Floodplain Inundation") are plotted as sharp triangular flags directly above the track.
- **Spatial Coordinate HUD**: A docked status strip displaying real-time cursor position in both decimal degrees and UTM coordinates alongside active camera zoom level and map scale.