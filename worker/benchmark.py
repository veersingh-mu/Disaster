"""FloodPath Performance Benchmark Harness (Phase 14).

Benchmarks:
1. Froehlich (2008) empirical breach parameter calculation.
2. ML Surrogate Model inference vs Full 2D Diffusive Wave routing.
3. Regional DEM profile caching speedup (cold vs warm).
4. Full pipeline throughput and latency report.
"""

import json
import time
from typing import Any

from worker.ml.surrogate import MLSurrogateModel
from worker.pipeline.breach import BreachParameters, calculate_breach_parameters
from worker.pipeline.dem import fetch_dem_profile
from worker.pipeline.routing import simulate_flood_routing


def run_benchmarks() -> dict[str, Any]:
    print("=" * 70)
    print(" FLOODPATH PERFORMANCE & LATENCY BENCHMARK SUITE (SIH PS 26161)")
    print("=" * 70)

    results: dict[str, Any] = {}

    # -------------------------------------------------------------
    # 1. Breach Calculation Benchmark
    # -------------------------------------------------------------
    print("\n[1/4] Benchmarking Froehlich Breach Estimation...")
    breach_iterations = 200
    t0 = time.perf_counter()
    for _ in range(breach_iterations):
        _ = calculate_breach_parameters(
            dam_height_m=35.0,
            dam_volume_m3=1_500_000.0,
            breach_type="overtopping",
        )
    t_breach_total = time.perf_counter() - t0
    t_breach_avg_ms = (t_breach_total / breach_iterations) * 1000.0
    print(f"  --> {breach_iterations} iterations: {t_breach_avg_ms:.4f} ms/iter")
    results["breach_calc_ms"] = round(t_breach_avg_ms, 4)

    # -------------------------------------------------------------
    # 2. DEM Caching Benchmark (Cold vs Warm)
    # -------------------------------------------------------------
    print("\n[2/4] Benchmarking DEM Profile Fetch & Cache Speedup...")
    lat, lon = 30.55, 79.56
    # 1st run (Warm/Cache retrieval)
    t0 = time.perf_counter()
    dem_prof_1 = fetch_dem_profile(latitude=lat, longitude=lon, radius_km=25.0)
    t_dem_1 = (time.perf_counter() - t0) * 1000.0

    # 2nd run (Guaranteed in-memory / disk cache hit)
    t0 = time.perf_counter()
    dem_prof_2 = fetch_dem_profile(latitude=lat, longitude=lon, radius_km=25.0)
    t_dem_2 = (time.perf_counter() - t0) * 1000.0

    print(f"  --> 1st fetch: {t_dem_1:.3f} ms (elev: {dem_prof_1.elevation_m}m, slope: {dem_prof_1.mean_slope_degrees} deg)")
    print(f"  --> 2nd fetch (cache hit): {t_dem_2:.3f} ms")
    cache_speedup = t_dem_1 / max(t_dem_2, 0.0001)
    print(f"  --> Cache Speedup Factor: {cache_speedup:.1f}x")
    results["dem_first_fetch_ms"] = round(t_dem_1, 3)
    results["dem_cached_fetch_ms"] = round(t_dem_2, 3)
    results["dem_cache_speedup"] = round(cache_speedup, 1)

    # -------------------------------------------------------------
    # 3. Solver Comparison: Full 2D Solve vs ML Surrogate Solve
    # -------------------------------------------------------------
    print("\n[3/4] Benchmarking Solvers: Full 2D Diffusive Wave vs AI Surrogate...")
    breach = BreachParameters(
        peak_discharge_m3s=5200.0,
        breach_width_m=42.0,
        breach_bottom_width_m=28.0,
        breach_formation_time_hours=0.35,
        breach_side_slope_z=1.0,
        method="froehlich",
    )

    # A. Full 2D Solve
    t0 = time.perf_counter()
    _ = simulate_flood_routing(
        origin_lat=lat,
        origin_lon=lon,
        breach=breach,
        dem=dem_prof_2,
        simulation_radius_km=25.0,
    )
    t_full_2d_ms = (time.perf_counter() - t0) * 1000.0
    print(f"  --> Full 2D Routing Solve: {t_full_2d_ms:.2f} ms ({t_full_2d_ms / 1000.0:.3f} s)")

    # B. ML Surrogate Model
    surrogate = MLSurrogateModel()
    surrogate_iterations = 50
    t0 = time.perf_counter()
    for _ in range(surrogate_iterations):
        _ = surrogate.predict(
            dam_height_m=35.0,
            dam_volume_m3=1_500_000.0,
            breach_type="overtopping",
            origin_lat=lat,
            origin_lon=lon,
            simulation_radius_km=25.0,
        )
    t_surrogate_total = time.perf_counter() - t0
    t_surrogate_avg_ms = (t_surrogate_total / surrogate_iterations) * 1000.0
    print(f"  --> ML Surrogate Solve (avg of {surrogate_iterations} runs): {t_surrogate_avg_ms:.2f} ms")

    speedup_ratio = t_full_2d_ms / max(t_surrogate_avg_ms, 0.001)
    print(f"  --> [FAST] AI Acceleration Ratio: {speedup_ratio:.1f}x SPEEDUP!")
    results["full_2d_solve_ms"] = round(t_full_2d_ms, 2)
    results["surrogate_solve_ms"] = round(t_surrogate_avg_ms, 2)
    results["ai_speedup_ratio"] = round(speedup_ratio, 1)

    # -------------------------------------------------------------
    # 4. Summary & Verification
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" BENCHMARK PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"  * Froehlich Regression:   {results['breach_calc_ms']} ms  (Target: < 5 ms)")
    print(f"  * Fast AI Surrogate:      {results['surrogate_solve_ms']} ms (Target: < 50 ms)")
    print(f"  * Full 2D Routing:        {results['full_2d_solve_ms']} ms (Target: < 5000 ms)")
    print(f"  * DEM Cached Query:       {results['dem_cached_fetch_ms']} ms (Target: < 10 ms)")
    print(f"  * Speedup Factor:         {results['ai_speedup_ratio']}x")
    print("=" * 70)

    return results


if __name__ == "__main__":
    benchmark_results = run_benchmarks()
    with open("benchmark_results.json", "w") as f:
        json.dump(benchmark_results, f, indent=2)
    print("\nBenchmark results written to benchmark_results.json")
