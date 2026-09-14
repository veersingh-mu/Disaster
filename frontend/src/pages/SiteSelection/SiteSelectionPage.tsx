import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import maplibregl from 'maplibre-gl';
import { demService } from '../../services/dem';
import { scenariosService } from '../../services/scenarios';
import { BreachType } from '../../types/api';

const PRESETS = [
  {
    name: 'Rishi Ganga (Chamoli 2021)',
    lat: 30.3833,
    lon: 79.7333,
    breachType: 'landslide_glof' as BreachType,
    height: 35.0,
    volume: 26000000.0,
    radius: 35.0,
  },
  {
    name: 'Tehri High Dam (Bhagirathi)',
    lat: 30.3783,
    lon: 78.4803,
    breachType: 'structural' as BreachType,
    height: 260.5,
    volume: 4000000000.0,
    radius: 75.0,
  },
  {
    name: 'South Lhonak Glacial Lake (Sikkim)',
    lat: 27.915,
    lon: 88.204,
    breachType: 'landslide_glof' as BreachType,
    height: 42.0,
    volume: 65000000.0,
    radius: 50.0,
  },
];

export const SiteSelectionPage: React.FC = () => {
  const navigate = useNavigate();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);

  // Form State
  const [name, setName] = useState<string>('Rishi Ganga GLOF Scenario');
  const [latitude, setLatitude] = useState<number>(30.3833);
  const [longitude, setLongitude] = useState<number>(79.7333);
  const [breachType, setBreachType] = useState<BreachType>('landslide_glof');
  const [damHeight, setDamHeight] = useState<number>(35.0);
  const [damVolume, setDamVolume] = useState<number>(26000000.0);
  const [simulationRadius, setSimulationRadius] = useState<number>(35.0);
  const [isDemEstimated, setIsDemEstimated] = useState<boolean>(false);
  const [simulationMode, setSimulationMode] = useState<'full' | 'fast'>('full');

  // DEM status state
  const [demLoading, setDemLoading] = useState<boolean>(false);
  const [demElevation, setDemElevation] = useState<number | null>(null);
  const [demSlope, setDemSlope] = useState<number | null>(null);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Read edit query parameter
  const [searchParams] = useSearchParams();
  const editScenarioId = searchParams.get('editScenarioId');

  // Geographic DEM bounds check (India & Himalayan basin coverage: 6-38°N, 68-98°E)
  const isWithinCoverage =
    latitude >= 6.0 && latitude <= 38.0 && longitude >= 68.0 && longitude <= 98.0;

  useEffect(() => {
    if (!editScenarioId) return;

    const loadScenario = async () => {
      try {
        const sc = await scenariosService.getScenario(editScenarioId);
        setName(`${sc.name} (Revision)`);
        if (sc.latitude && sc.longitude) {
          setLatitude(sc.latitude);
          setLongitude(sc.longitude);
          if (markerRef.current) markerRef.current.setLngLat([sc.longitude, sc.latitude]);
          if (mapInstanceRef.current) mapInstanceRef.current.flyTo({ center: [sc.longitude, sc.latitude], zoom: 10 });
        }
        if (sc.breach_type) setBreachType(sc.breach_type);
        if (sc.dam_height_m) setDamHeight(sc.dam_height_m);
        if (sc.dam_volume_m3) setDamVolume(sc.dam_volume_m3);
        if (sc.simulation_radius_km) setSimulationRadius(sc.simulation_radius_km);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setFormError(`Failed to load scenario ${editScenarioId} for editing: ${msg}`);
      }
    };

    loadScenario();
  }, [editScenarioId]);

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: [
              'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          },
        },
        layers: [
          {
            id: 'osm-layer',
            type: 'raster',
            source: 'osm',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [longitude, latitude],
      zoom: 9.5,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    // Create breach origin pin
    const marker = new maplibregl.Marker({ color: '#ba1a1a', draggable: true })
      .setLngLat([longitude, latitude])
      .addTo(map);

    marker.on('dragend', () => {
      const lngLat = marker.getLngLat();
      setLatitude(parseFloat(lngLat.lat.toFixed(5)));
      setLongitude(parseFloat(lngLat.lng.toFixed(5)));
      setIsDemEstimated(false);
    });

    map.on('click', (e) => {
      const { lng, lat } = e.lngLat;
      const roundedLat = parseFloat(lat.toFixed(5));
      const roundedLon = parseFloat(lng.toFixed(5));
      setLatitude(roundedLat);
      setLongitude(roundedLon);
      marker.setLngLat([roundedLon, roundedLat]);
      setIsDemEstimated(false);
    });

    mapInstanceRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePresetSelect = (preset: (typeof PRESETS)[0]) => {
    setName(preset.name);
    setLatitude(preset.lat);
    setLongitude(preset.lon);
    setBreachType(preset.breachType);
    setDamHeight(preset.height);
    setDamVolume(preset.volume);
    setSimulationRadius(preset.radius);

    if (mapInstanceRef.current && markerRef.current) {
      mapInstanceRef.current.flyTo({ center: [preset.lon, preset.lat], zoom: 12 });
      markerRef.current.setLngLat([preset.lon, preset.lat]);
    }
  };

  const handleAutoFillDEM = async () => {
    try {
      setDemLoading(true);
      setFormError(null);
      const res = await demService.previewDEM(latitude, longitude, simulationRadius);

      setDemElevation(res.elevation_m);
      setDemSlope(res.slope_degrees || null);
      setDamHeight(res.estimated_dam_height_m);
      setDamVolume(res.estimated_dam_volume_m3);
      setIsDemEstimated(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setFormError(`DEM Query Failed: ${msg}`);
    } finally {
      setDemLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError('Please enter a scenario name.');
      return;
    }
    if (damHeight <= 0) {
      setFormError('Dam height must be greater than 0 meters.');
      return;
    }
    if (damVolume <= 0) {
      setFormError('Reservoir volume must be greater than 0 cubic meters.');
      return;
    }

    const isWithinCoverage =
      latitude >= 6.0 && latitude <= 38.0 && longitude >= 68.0 && longitude <= 98.0;

    if (!isWithinCoverage) {
      setFormError(
        'Selected location is outside DEM coverage (Himalayan & Indian river basins: 6.0°–38.0° N, 68.0°–98.0° E). Please select a location within the covered belt.'
      );
      return;
    }

    try {
      setIsSubmitting(true);
      let targetScenarioId: string;

      if (editScenarioId) {
        // Re-use existing scenario row to prevent duplication
        const updated = await scenariosService.updateScenario(editScenarioId, {
          name: name.trim(),
          simulation_radius_km: simulationRadius,
        });
        targetScenarioId = updated.id;
      } else {
        // Create new scenario
        const scenario = await scenariosService.createScenario({
          name: name.trim(),
          latitude,
          longitude,
          breach_type: breachType,
          dam_height_m: damHeight,
          dam_volume_m3: damVolume,
          simulation_radius_km: simulationRadius,
          is_dem_estimated: isDemEstimated,
        });
        targetScenarioId = scenario.id;
      }

      // 2. Trigger Simulation Run against the scenario
      await scenariosService.triggerSimulation(targetScenarioId, simulationMode);

      // 3. Navigate to Loading Screen
      navigate(`/scenarios/${targetScenarioId}/simulating`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to initialize simulation.';
      setFormError(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col lg:flex-row h-[calc(100vh-48px)] overflow-hidden bg-background">
      {/* Left Pane: Interactive Map */}
      <div className="flex-1 relative flex flex-col border-b lg:border-b-0 lg:border-r border-outline/30">
        {/* Preset Toolbar Overlay */}
        <div className="absolute top-3 left-3 z-10 bg-surface-container-lowest/90 backdrop-blur-sm p-2 border border-outline/30 flex items-center gap-1.5 shadow-md text-xs">
          <span className="font-mono text-[10px] text-on-surface-variant font-bold uppercase tracking-wider mr-1">
            Site Presets:
          </span>
          {PRESETS.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => handlePresetSelect(p)}
              className="px-2 py-1 text-[11px] bg-surface-container-low border border-outline/20 hover:bg-primary hover:text-white transition-colors"
            >
              {p.name.split(' ')[0]}
            </button>
          ))}
        </div>

        {/* Map Canvas */}
        <div ref={mapContainerRef} className="w-full h-full min-h-[350px]" />

        {/* Coordinates Readout Overlay */}
        <div className="absolute bottom-3 left-3 z-10 bg-surface-container-lowest/90 backdrop-blur-sm px-3 py-1.5 border border-outline/30 font-mono text-xs text-on-surface flex items-center gap-3 shadow-md">
          <div className="flex items-center gap-1">
            <span className="text-secondary">LAT:</span>
            <span className="font-bold">{latitude.toFixed(5)}° N</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-secondary">LON:</span>
            <span className="font-bold">{longitude.toFixed(5)}° E</span>
          </div>
          <span className="text-[10px] text-primary font-sans">
            (Click or drag marker on map to relocate site)
          </span>
        </div>
      </div>

      {/* Right Pane: Scenario Configuration Panel */}
      <div className="w-full lg:w-[460px] bg-surface-container-lowest flex flex-col overflow-y-auto p-space-lg shadow-lg border-l border-outline/20">
        <div className="border-b border-outline/20 pb-3 mb-4">
          <div className="flex items-center gap-1.5 text-primary mb-1">
            <span className="material-symbols-outlined text-lg">tune</span>
            <span className="font-mono text-[11px] uppercase font-bold tracking-wider">
              Parameter Specification
            </span>
          </div>
          <h2 className="text-xl font-bold text-on-surface font-heading">
            Breach Scenario Configuration
          </h2>
          <p className="text-xs text-on-surface-variant mt-1">
            Define breach initiation mechanics, topographic barriers, and downstream simulation radius.
          </p>
        </div>

        {editScenarioId && (
          <div className="mb-3 p-2.5 bg-secondary-container/40 border border-secondary/30 text-on-secondary-container text-xs flex items-center gap-2 font-mono">
            <span className="material-symbols-outlined text-base text-secondary">tune</span>
            <span>Pre-filled parameters from Scenario. Adjust configuration and re-solve.</span>
          </div>
        )}

        {formError && (
          <div className="mb-4 p-space-sm bg-error-container text-on-error-container border border-error/30 text-xs font-mono">
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 text-xs font-body">
          {/* Scenario Name */}
          <div>
            <label
              htmlFor="scenario-name-input"
              className="block font-mono text-[11px] text-on-surface-variant uppercase font-semibold mb-1"
            >
              Scenario Name
            </label>
            <input
              id="scenario-name-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-surface-container-low border border-outline/30 text-on-surface focus:outline-none focus:border-primary font-medium"
              placeholder="e.g. Tapovan Hydroelectric Project Breach"
              required
            />
          </div>

          {/* Coordinates & DEM Auto-fill Button */}
          <div className="p-3 bg-surface-container-low border border-outline/20 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] text-on-surface font-semibold uppercase">
                Breach Site Location
              </span>
              <button
                type="button"
                onClick={handleAutoFillDEM}
                disabled={demLoading}
                aria-label="Query and auto-fill dam parameters from DEM terrain profile"
                className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-primary-container text-white hover:bg-primary transition-colors"
              >
                <span className="material-symbols-outlined text-xs">terrain</span>
                <span>{demLoading ? 'Querying DEM...' : 'Auto-Fill from DEM'}</span>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
              <div>
                <span className="text-on-surface-variant text-[10px] font-medium">LATITUDE:</span>
                <div className="font-bold text-on-surface">{latitude}° N</div>
              </div>
              <div>
                <span className="text-on-surface-variant text-[10px] font-medium">LONGITUDE:</span>
                <div className="font-bold text-on-surface">{longitude}° E</div>
              </div>
            </div>

            {demElevation !== null && (
              <div className="mt-1 pt-1.5 border-t border-outline/20 grid grid-cols-2 gap-2 font-mono text-[11px] text-emerald-800 bg-emerald-50 p-2">
                <div>
                  <span className="text-[10px]">ELEVATION:</span>
                  <div className="font-bold">{demElevation} m</div>
                </div>
                <div>
                  <span className="text-[10px]">MEAN SLOPE:</span>
                  <div className="font-bold">{demSlope}° (Steep)</div>
                </div>
              </div>
            )}

            {!isWithinCoverage && (
              <div className="mt-2 p-2.5 bg-amber-500/10 border-l-4 border-amber-500 text-on-surface text-xs font-mono flex items-start gap-2">
                <span className="material-symbols-outlined text-base text-amber-600 mt-0.5">warning</span>
                <div>
                  <div className="font-bold text-amber-700 uppercase text-[11px]">Terrain Coverage Warning</div>
                  <p className="text-[11px] text-on-surface-variant leading-relaxed mt-0.5">
                    Terrain data unavailable for this region. Selected location is outside current DEM coverage
                    (Himalayan &amp; Indian river basins: 6.0°–38.0° N, 68.0°–98.0° E). Please select a site within the covered belt.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Breach Type Selector */}
          <div>
            <label className="block font-mono text-[11px] text-on-surface-variant uppercase font-semibold mb-1.5">
              Breach Initiation Mechanics
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setBreachType('landslide_glof')}
                aria-pressed={breachType === 'landslide_glof'}
                className={`p-2.5 text-left border transition-all ${
                  breachType === 'landslide_glof'
                    ? 'border-primary bg-primary-fixed/30 text-primary font-bold'
                    : 'border-outline/20 bg-surface-container-low text-on-surface hover:border-outline/40'
                }`}
              >
                <div className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-base">landslide</span>
                  <span className="font-semibold text-xs">Landslide / GLOF</span>
                </div>
                <div className="text-[10px] text-on-surface-variant mt-1 font-medium">
                  Moraine lake overtopping & high-energy incision
                </div>
              </button>

              <button
                type="button"
                onClick={() => setBreachType('structural')}
                aria-pressed={breachType === 'structural'}
                className={`p-2.5 text-left border transition-all ${
                  breachType === 'structural'
                    ? 'border-primary bg-primary-fixed/30 text-primary font-bold'
                    : 'border-outline/20 bg-surface-container-low text-on-surface hover:border-outline/40'
                }`}
              >
                <div className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-base">dam</span>
                  <span className="font-semibold text-xs">Structural Failure</span>
                </div>
                <div className="text-[10px] text-on-surface-variant mt-1 font-medium">
                  Internal erosion, piping, or concrete barrier loss
                </div>
              </button>
            </div>
          </div>

          {/* Dam Height & Reservoir Volume */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="dam-height-input"
                className="block font-mono text-[11px] text-on-surface-variant uppercase font-semibold mb-1"
              >
                Dam / Barrier Height (m)
              </label>
              <input
                id="dam-height-input"
                type="number"
                step="0.5"
                min="1"
                max="400"
                value={damHeight}
                onChange={(e) => {
                  setDamHeight(parseFloat(e.target.value) || 0);
                  setIsDemEstimated(false);
                }}
                className="w-full px-3 py-2 bg-surface-container-low border border-outline/30 font-mono font-medium focus:outline-none focus:border-primary"
                required
              />
            </div>

            <div>
              <label
                htmlFor="dam-volume-input"
                className="block font-mono text-[11px] text-on-surface-variant uppercase font-semibold mb-1"
              >
                Reservoir Vol (m³)
              </label>
              <input
                id="dam-volume-input"
                type="number"
                step="100000"
                min="10000"
                value={damVolume}
                onChange={(e) => {
                  setDamVolume(parseFloat(e.target.value) || 0);
                  setIsDemEstimated(false);
                }}
                className="w-full px-3 py-2 bg-surface-container-low border border-outline/30 font-mono font-medium focus:outline-none focus:border-primary"
                required
              />
              <div className="font-mono text-[10px] text-on-surface-variant mt-0.5 font-medium">
                = {(damVolume / 1e6).toFixed(2)} Million m³
              </div>
            </div>
          </div>

          {/* Simulation Radius Slider */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label
                htmlFor="simulation-radius-slider"
                className="font-mono text-[11px] text-on-surface-variant uppercase font-semibold"
              >
                Downstream Simulation Radius
              </label>
              <span className="font-mono text-xs font-bold text-primary">{simulationRadius} km</span>
            </div>
            <input
              id="simulation-radius-slider"
              type="range"
              min="5"
              max="100"
              step="5"
              value={simulationRadius}
              onChange={(e) => setSimulationRadius(parseInt(e.target.value))}
              className="w-full accent-primary"
            />
            <div className="flex justify-between font-mono text-[10px] text-on-surface-variant mt-0.5 font-medium">
              <span>5 km (Local)</span>
              <span>50 km (Regional)</span>
              <span>100 km (Basin)</span>
            </div>
          </div>

          {/* Solver Engine / Simulation Mode Toggle */}
          <div>
            <label className="block font-mono text-[11px] text-on-surface-variant uppercase font-semibold mb-1.5">
              Solver Engine / Execution Mode
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setSimulationMode('full')}
                className={`p-2.5 text-left border transition-all flex flex-col justify-between ${
                  simulationMode === 'full'
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-outline/30 bg-surface-container-low text-on-surface-variant hover:border-outline'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-xs font-bold uppercase tracking-wider">Full 2D Solve</span>
                  <span className="material-symbols-outlined text-sm">waves</span>
                </div>
                <div className="text-[10px] text-secondary leading-tight">
                  Hydrodynamic diffusive-wave physics model (~2-4s)
                </div>
              </button>

              <button
                type="button"
                onClick={() => setSimulationMode('fast')}
                className={`p-2.5 text-left border transition-all flex flex-col justify-between ${
                  simulationMode === 'fast'
                    ? 'border-secondary bg-secondary/10 text-secondary'
                    : 'border-outline/30 bg-surface-container-low text-on-surface-variant hover:border-outline'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-1">
                    ⚡ Fast AI Mode
                  </span>
                  <span className="material-symbols-outlined text-sm text-secondary">bolt</span>
                </div>
                <div className="text-[10px] text-secondary leading-tight">
                  ML surrogate for rapid what-if sweeps (&lt;50ms, 100x+)
                </div>
              </button>
            </div>
          </div>

          {/* DEM Auto-fill Badge */}
          {isDemEstimated && (
            <div className="p-2 bg-secondary-container/40 border border-secondary/30 text-on-secondary-container text-[11px] flex items-center gap-1.5 font-mono">
              <span className="material-symbols-outlined text-sm text-secondary">verified</span>
              <span>Height & volume conditioned by regional DEM slope profile.</span>
            </div>
          )}

          {/* Submit Action */}
          <button
            type="submit"
            disabled={isSubmitting || !isWithinCoverage}
            className={`mt-2 w-full py-3 font-semibold text-xs uppercase tracking-wider transition-colors shadow-md flex items-center justify-center gap-2 ${
              !isWithinCoverage
                ? 'bg-outline-variant text-secondary cursor-not-allowed'
                : 'bg-primary text-on-primary hover:bg-primary-container'
            }`}
          >
            {isSubmitting ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent animate-spin inline-block" />
                <span>Launching Simulation Worker...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-base">
                  {editScenarioId ? 'refresh' : 'play_arrow'}
                </span>
                <span>
                  {editScenarioId
                    ? 'Update & Re-run Simulation'
                    : 'Initialize & Run Simulation'}
                </span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
