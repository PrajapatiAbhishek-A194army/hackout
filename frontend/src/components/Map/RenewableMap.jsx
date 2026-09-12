import React, { useEffect } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Circle, 
  useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  Sun, 
  Wind, 
  Zap, 
  ShieldAlert, 
  ArrowRight, 
  Activity, 
  BatteryCharging,
  Maximize2
} from 'lucide-react';

// Controller to smoothly pan & zoom map when selected plant or region changes
function MapViewController({ selectedPlant, selectedRegion }) {
  const map = useMap();

  useEffect(() => {
    if (selectedPlant && selectedPlant.latitude && selectedPlant.longitude) {
      map.flyTo([selectedPlant.latitude, selectedPlant.longitude], 8, {
        duration: 1.5,
        easeLinearity: 0.25
      });
    }
  }, [selectedPlant, map]);

  useEffect(() => {
    if (!selectedRegion || selectedRegion === 'all') return;
    
    // Region bounding coordinates
    const regionCenters = {
      'NR': { center: [28.6, 75.5], zoom: 6 },
      'WR': { center: [22.5, 71.5], zoom: 6 },
      'SR': { center: [12.5, 77.5], zoom: 6 },
      'ER': { center: [23.5, 85.5], zoom: 6 },
      'NER': { center: [26.2, 92.5], zoom: 6 },
    };

    const target = regionCenters[selectedRegion];
    if (target) {
      map.flyTo(target.center, target.zoom, { duration: 1.2 });
    }
  }, [selectedRegion, map]);

  return null;
}

// Helper to create high-performance custom SVG HTML divIcon
function createPlantIcon(plant, telemetry) {
  const status = telemetry?.operational_status || plant.status || 'NORMAL';
  const isSolar = plant.plant_type === 'solar';
  const isWind = plant.plant_type === 'wind';
  
  // Status colors
  let ringColor = '#10b981'; // emerald
  let bgColor = '#065f46';
  let pulseClass = '';

  if (status === 'WARNING' || status === 'CURTAILED') {
    ringColor = '#f59e0b'; // amber
    bgColor = '#92400e';
    pulseClass = 'animate-ping opacity-75';
  } else if (status === 'CRITICAL' || status === 'TRIPPED') {
    ringColor = '#f43f5e'; // rose
    bgColor = '#9f1239';
    pulseClass = 'animate-ping opacity-80';
  }

  // Tech icon SVG
  const svgIcon = isSolar 
    ? `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-amber-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`
    : isWind
    ? `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-teal-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>`
    : `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-purple-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;

  const html = `
    <div class="relative flex items-center justify-center cursor-pointer group">
      ${(status === 'WARNING' || status === 'CRITICAL') ? `
        <span class="absolute w-10 h-10 rounded-full ${pulseClass}" style="background-color: ${ringColor}"></span>
      ` : ''}
      <div class="relative flex items-center justify-center w-8 h-8 rounded-full shadow-lg border-2 transition-transform duration-200 group-hover:scale-110" 
           style="background-color: ${bgColor}; border-color: ${ringColor}">
        ${svgIcon}
      </div>
      <div class="absolute -bottom-5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-900/90 text-white shadow whitespace-nowrap pointer-events-none">
        ${Math.round(plant.capacity_mw)} MW
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-plant-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18]
  });
}

export default function RenewableMap({
  plants = [],
  telemetryMap = {},
  selectedPlant = null,
  onSelectPlant,
  filters = { showHeatmap: true, showWeather: false, showRegionalClusters: true, region: 'all' }
}) {
  // Indian Grid Centroid
  const defaultCenter = [22.5, 78.5];
  const defaultZoom = 5;

  // Regional Balancing Hub Centroids & Estimated Interconnection Capacity
  const regionalClusters = [
    { code: 'NR', name: 'Northern Grid Corridor', center: [27.8, 73.5], capacity: '3,309 MW', color: '#10b981' },
    { code: 'WR', name: 'Western Grid Corridor', center: [23.5, 70.8], capacity: '5,790 MW', color: '#0ea5e9' },
    { code: 'SR', name: 'Southern Grid Corridor', center: [11.2, 77.4], capacity: '3,550 MW', color: '#8b5cf6' },
  ];

  return (
    <div className="relative w-full h-[600px] lg:h-[700px] rounded-3xl overflow-hidden shadow-elevated border border-slate-200">
      
      {/* Floating Quick Region Jump Controls */}
      <div className="absolute top-4 right-4 z-[400] flex flex-wrap items-center gap-1.5 bg-white/90 backdrop-blur-md p-1.5 rounded-2xl border border-slate-200/80 shadow-md text-xs">
        <span className="text-[11px] font-bold text-slate-500 px-2 hidden sm:inline">Zoom:</span>
        <button
          onClick={() => onSelectPlant && onSelectPlant({ latitude: 22.5, longitude: 78.5, name: 'All India' })}
          className="px-2.5 py-1 rounded-xl font-semibold text-slate-700 hover:bg-slate-100 hover:text-slate-900 transition-colors"
        >
          All India
        </button>
        <button
          onClick={() => onSelectPlant && onSelectPlant({ latitude: 27.2, longitude: 73.0, name: 'Northern Grid' })}
          className="px-2.5 py-1 rounded-xl font-semibold text-emerald-700 hover:bg-emerald-50 transition-colors"
        >
          Northern (NR)
        </button>
        <button
          onClick={() => onSelectPlant && onSelectPlant({ latitude: 23.5, longitude: 70.8, name: 'Western Grid' })}
          className="px-2.5 py-1 rounded-xl font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
        >
          Western (WR)
        </button>
        <button
          onClick={() => onSelectPlant && onSelectPlant({ latitude: 12.0, longitude: 77.4, name: 'Southern Grid' })}
          className="px-2.5 py-1 rounded-xl font-semibold text-purple-700 hover:bg-purple-50 transition-colors"
        >
          Southern (SR)
        </button>
      </div>

      {/* Map Legend */}
      <div className="absolute bottom-4 left-4 z-[400] bg-white/90 backdrop-blur-md p-3 rounded-2xl border border-slate-200/80 shadow-md text-xs space-y-1.5 pointer-events-auto">
        <span className="font-bold text-slate-800 block text-[11px] uppercase tracking-wider mb-1">
          Grid Status Legend
        </span>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-xs" />
          <span className="text-slate-600">Normal Operation (High Confidence)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-xs" />
          <span className="text-slate-600">Warning / Ramp Risk / Curtailment</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-xs" />
          <span className="text-slate-600">Critical Imbalance / Tripped</span>
        </div>
      </div>

      {/* Leaflet Map */}
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        scrollWheelZoom={true}
        className="w-full h-full z-10"
      >
        {/* High-Contrast Positron CartoDB Basemap */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />

        <MapViewController 
          selectedPlant={selectedPlant} 
          selectedRegion={filters.region} 
        />

        {/* 1. Regional Cluster Corridors Overlay */}
        {filters.showRegionalClusters && regionalClusters.map((cluster) => (
          <Circle
            key={cluster.code}
            center={cluster.center}
            radius={180000} // 180 km radius
            pathOptions={{
              color: cluster.color,
              fillColor: cluster.color,
              fillOpacity: 0.08,
              weight: 1.5,
              dashArray: '4, 8'
            }}
          />
        ))}

        {/* 2. Capacity Heat Circles Overlay */}
        {filters.showHeatmap && plants.map((p) => {
          const cap = p.capacity_mw || 1000;
          const radius = Math.min(120000, Math.max(35000, cap * 22)); // radius in meters
          const color = p.plant_type === 'solar' ? '#f59e0b' : p.plant_type === 'wind' ? '#0d9488' : '#8b5cf6';
          
          return (
            <Circle
              key={`heat-${p.id}`}
              center={[p.latitude, p.longitude]}
              radius={radius}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: 0.18,
                weight: 1,
              }}
            />
          );
        })}

        {/* 3. Weather Atmosphere Overlay (Irradiance & Coastal Wind Jets) */}
        {filters.showWeather && (
          <>
            {/* Thar Desert Solar Hotspot */}
            <Circle
              center={[27.0, 71.5]}
              radius={160000}
              pathOptions={{
                color: '#f59e0b',
                fillColor: '#fbbf24',
                fillOpacity: 0.15,
                weight: 1.5,
                dashArray: '3, 6'
              }}
            />
            {/* Tamil Nadu Wind Pass Jet */}
            <Circle
              center={[8.5, 77.6]}
              radius={90000}
              pathOptions={{
                color: '#06b6d4',
                fillColor: '#22d3ee',
                fillOpacity: 0.2,
                weight: 1.5,
                dashArray: '3, 6'
              }}
            />
          </>
        )}

        {/* 4. Plant Markers */}
        {plants.map((plant) => {
          const telemetry = telemetryMap[plant.id] || telemetryMap[plant.code];
          const icon = createPlantIcon(plant, telemetry);
          const genMW = telemetry?.current_generation_mw ?? (plant.capacity_mw * 0.74);
          const cuf = telemetry?.capacity_factor_pct ?? Math.round((genMW / plant.capacity_mw) * 100);
          const status = telemetry?.operational_status || plant.status || 'NORMAL';

          return (
            <Marker
              key={plant.id}
              position={[plant.latitude, plant.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => onSelectPlant && onSelectPlant(plant)
              }}
            >
              <Popup className="custom-plant-popup">
                <div className="p-2.5 max-w-xs space-y-2 text-slate-900 font-sans">
                  
                  {/* Popup Header */}
                  <div className="flex items-start justify-between gap-2 pb-1.5 border-b border-slate-200">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                        {plant.plant_type} Plant • {plant.code}
                      </span>
                      <h4 className="font-bold text-sm text-slate-900 leading-tight">{plant.name}</h4>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      status === 'NORMAL' ? 'bg-emerald-100 text-emerald-800' :
                      status === 'WARNING' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {status}
                    </span>
                  </div>

                  {/* Telemetry Summary */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-50 p-2 rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-500 block">Rated Capacity</span>
                      <span className="font-bold text-slate-800">{Number(plant.capacity_mw).toLocaleString()} MW</span>
                    </div>
                    <div className="bg-emerald-50 p-2 rounded-lg border border-emerald-200">
                      <span className="text-[10px] text-emerald-700 block">Live Generation</span>
                      <span className="font-bold text-emerald-900">{Number(genMW).toFixed(1)} MW</span>
                    </div>
                  </div>

                  {/* CUF & Weather */}
                  <div className="text-[11px] text-slate-600 space-y-1 pt-1">
                    <div className="flex justify-between">
                      <span>Capacity Utilization:</span>
                      <span className="font-bold text-slate-800">{cuf}%</span>
                    </div>
                    {telemetry?.weather && (
                      <div className="flex justify-between">
                        <span>Local Weather:</span>
                        <span className="font-semibold text-slate-700">
                          {Math.round(telemetry.weather.irradiance_ghi)} W/m² • {telemetry.weather.ambient_temp_c}°C
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <button
                    onClick={() => onSelectPlant && onSelectPlant(plant)}
                    className="w-full mt-2 py-1.5 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                  >
                    <span>Inspect Plant Telemetry</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>

                </div>
              </Popup>
            </Marker>
          );
        })}

      </MapContainer>
    </div>
  );
}
