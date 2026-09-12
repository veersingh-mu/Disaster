"""Performance and SLA Benchmarking Tests (Phase 14).

Verifies:
- Froehlich breach calculations complete in < 20ms
- ML Surrogate Model infers under 100ms
- DEM profile caching returns under 20ms
- Interactive API endpoints respond under 150ms
"""

import time

from fastapi.testclient import TestClient

from backend.app.main import app
from worker.ml.surrogate import MLSurrogateModel
from worker.pipeline.breach import calculate_breach_parameters
from worker.pipeline.dem import fetch_dem_profile


def test_froehlich_calculation_performance():
    """Verify Froehlich breach calculation satisfies sub-20ms SLA."""
    t0 = time.perf_counter()
    for _ in range(50):
        _ = calculate_breach_parameters(
            dam_height_m=40.0,
            dam_volume_m3=2_000_000.0,
            breach_type="piping",
        )
    elapsed_ms = ((time.perf_counter() - t0) / 50) * 1000.0
    assert elapsed_ms < 20.0, f"Froehlich calculation too slow: {elapsed_ms:.2f}ms"


def test_surrogate_model_performance():
    """Verify ML surrogate model satisfies sub-100ms SLA."""
    surrogate = MLSurrogateModel()
    t0 = time.perf_counter()
    for _ in range(20):
        _ = surrogate.predict(
            dam_height_m=35.0,
            dam_volume_m3=1_500_000.0,
            breach_type="overtopping",
            origin_lat=30.55,
            origin_lon=79.56,
            simulation_radius_km=15.0,
        )
    elapsed_ms = ((time.perf_counter() - t0) / 20) * 1000.0
    assert elapsed_ms < 100.0, f"ML Surrogate too slow: {elapsed_ms:.2f}ms"


def test_dem_cached_fetch_performance():
    """Verify cached DEM profile fetch satisfies sub-20ms SLA."""
    lat, lon = 30.55, 79.56
    # Prime cache
    _ = fetch_dem_profile(latitude=lat, longitude=lon, radius_km=10.0)

    # Benchmark cached read
    t0 = time.perf_counter()
    for _ in range(20):
        _ = fetch_dem_profile(latitude=lat, longitude=lon, radius_km=10.0)
    elapsed_ms = ((time.perf_counter() - t0) / 20) * 1000.0
    assert elapsed_ms < 20.0, f"Cached DEM fetch too slow: {elapsed_ms:.2f}ms"



def test_interactive_endpoint_latency():
    """Verify interactive endpoints respond in under 150ms."""
    client = TestClient(app)
    t0 = time.perf_counter()
    res = client.get("/health")
    latency_ms = (time.perf_counter() - t0) * 1000.0
    assert res.status_code == 200
    assert latency_ms < 150.0, f"Health endpoint too slow: {latency_ms:.2f}ms"
