"""Common Alerting Protocol (CAP v1.2) XML Emergency Broadcast API Router."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_user_scenario
from backend.app.errors import NotFoundError
from backend.app.models.affected_settlement import AffectedSettlement
from backend.app.models.scenario import Scenario
from backend.app.models.settlement import Settlement
from backend.app.models.simulation_run import SimulationRun

router = APIRouter(tags=["Alerts"])


def build_cap_xml(
    scenario: Scenario,
    run: SimulationRun,
    affected_rows: list,
) -> str:
    """Construct an OASIS CAP v1.2 compliant XML string for emergency dispatch."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    alert_id = f"IN-NDRF-FLOODPATH-{scenario.id}-{run.id}"

    alert = ET.Element(
        "alert",
        attrib={"xmlns": "urn:oasis:names:tc:emergency:cap:1.2"},
    )

    ET.SubElement(alert, "identifier").text = alert_id
    ET.SubElement(alert, "sender").text = "eoc-duty-officer@floodpath.ndrf.gov.in"
    ET.SubElement(alert, "sent").text = now_iso
    ET.SubElement(alert, "status").text = "Actual"
    ET.SubElement(alert, "msgType").text = "Alert"
    ET.SubElement(alert, "scope").text = "Public"
    ET.SubElement(alert, "incidents").text = f"SCENARIO-{scenario.id}"

    info = ET.SubElement(alert, "info")
    ET.SubElement(info, "category").text = "Geo"
    ET.SubElement(info, "event").text = (
        "Glacial Lake Outburst / Dam Breach Inundation"
        if scenario.breach_type.value == "landslide_glof"
        else "Structural Dam Breach Inundation"
    )
    ET.SubElement(info, "urgency").text = "Immediate"
    ET.SubElement(info, "severity").text = "Extreme"
    ET.SubElement(info, "certainty").text = "Observed"

    # Headline
    first_settlement = affected_rows[0][1].name if affected_rows else "downstream valley"
    first_arrival = affected_rows[0][0].arrival_time_minutes if affected_rows else 15
    headline = (
        f"CRITICAL FLOOD WAVE EVACUATION: {scenario.name} breached. "
        f"Impact at {first_settlement} in T+{first_arrival} min."
    )
    ET.SubElement(info, "headline").text = headline

    # Description with ordered village arrivals
    vol_m = float(scenario.dam_volume_m3) / 1e6
    desc_lines = [
        f"A rapid inundation wave has been initiated at ({scenario.latitude:.4f}° N, {scenario.longitude:.4f}° E).",
        f"Breach mechanism: {scenario.breach_type.value}. Dam height: {float(scenario.dam_height_m):.1f}m. Estimated volume: {vol_m:.1f}M m³.",
        "Downstream Arrival Timeline & Evacuation Priorities:",
    ]
    for aff, st in affected_rows:
        priority = "IMMEDIATE EVACUATION" if aff.arrival_time_minutes <= 30 else "STANDBY ALERT"
        depth_str = f"{float(aff.estimated_depth_m):.1f}m" if aff.estimated_depth_m else "N/A"
        desc_lines.append(
            f"- {st.name} ({st.district}, {st.state}): Arrival T+{aff.arrival_time_minutes} min | Est. Depth: {depth_str} | Priority: {priority}"
        )

    ET.SubElement(info, "description").text = "\n".join(desc_lines)
    ET.SubElement(info, "instruction").text = (
        "Evacuate all riparian populations to designated safe terrain points above the flood line immediately. "
        "Sound riverbank sirens and deploy NDRF/SDRF swift water rescue units."
    )

    # Area definition
    area = ET.SubElement(info, "area")
    ET.SubElement(area, "areaDesc").text = f"Downstream river basin {scenario.simulation_radius_km}km corridor"
    ET.SubElement(area, "circle").text = f"{scenario.latitude:.4f},{scenario.longitude:.4f} {scenario.simulation_radius_km}"

    for _, st in affected_rows:
        geocode = ET.SubElement(area, "geocode")
        ET.SubElement(geocode, "valueName").text = "VillageName"
        ET.SubElement(geocode, "value").text = st.name

    return ET.tostring(alert, encoding="utf-8", xml_declaration=True).decode("utf-8")


@router.get("/scenarios/{scenario_id}/alert/cap-xml")
def get_scenario_cap_xml_alert(
    scenario_id: UUID,
    scenario: Scenario = Depends(get_user_scenario),
    db: Session = Depends(get_db),
):
    """Generate an OASIS CAP v1.2 XML emergency broadcast payload for downstream responders."""
    latest_run = db.execute(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario.id)
        .order_by(desc(SimulationRun.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if latest_run is None:
        raise NotFoundError(
            message=f"No simulation runs found for scenario '{scenario.id}' to generate alert",
            error_code="RUN_NOT_FOUND",
        )

    affected_rows = db.execute(
        select(AffectedSettlement, Settlement)
        .join(Settlement, AffectedSettlement.settlement_id == Settlement.id)
        .where(AffectedSettlement.simulation_run_id == latest_run.id)
        .order_by(AffectedSettlement.arrival_time_minutes.asc())
    ).all()

    xml_content = build_cap_xml(scenario, latest_run, affected_rows)

    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="floodpath_cap_alert_{scenario.id}.xml"'
        },
    )
