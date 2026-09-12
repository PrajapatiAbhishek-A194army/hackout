import React, { useState, useEffect } from 'react';
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
  Layers,
  Map as MapIcon,
  Globe,
  Mountain,
  Maximize2
} from 'lucide-react';

// Free, reliable, non-watermarked tile basemaps (100% free, zero API key required)
const BASEMAP_PROVIDERS = {
  osm: {
    id: 'osm',
    name: 'Street (OSM)',
    icon: '🗺️',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
    maxZoom: 19
  },
  satellite: {
    id: 'satellite',
    name: 'Satellite (Esri)',
    icon: '🛰️',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 18
  },
  topo: {
    id: 'topo',
    name: 'Topographic (Esri)',
    icon: '🏔️',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong)',
    maxZoom: 18
  }
};

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
      'NR': { center: [27.5, 74.0], zoom: 6 },
      'WR': { center: [22.0, 72.0], zoom: 6 },
      'SR': { center: [12.0, 77.5], zoom: 6 },
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

// Helper to create high-visibility custom SVG HTML divIcon for Solar, Wind, and Hybrid
function createPlantIcon(plant, telemetry, isSelected = false) {
  const status = telemetry?.operational_status || plant.status || 'NORMAL';
  const isSolar = plant.plant_type === 'solar';
  const isWind = plant.plant_type === 'wind';
  const isHybrid = plant.plant_type === 'hybrid';

  // Distinct color palettes per technology type
  let techTheme = {
    badgeBg: 'bg-amber-500',
    markerBg: 'background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);',
    borderColor: '#fbbf24',
    shadowColor: 'rgba(245, 158, 11, 0.45)',
    label: '☀️ Solar',
    textBadge: 'bg-amber-950/90 text-amber-200 border-amber-500/50'
  };

  if (isWind) {
    techTheme = {
      badgeBg: 'bg-teal-500',
      markerBg: 'background: linear-gradient(135deg, #06b6d4 0%, #0d9488 100%);',
      borderColor: '#22d3ee',
      shadowColor: 'rgba(6, 182, 212, 0.45)',
      label: '💨 Wind',
      textBadge: 'bg-teal-950/90 text-teal-200 border-teal-500/50'
    };
  } else if (isHybrid) {
    techTheme = {
      badgeBg: 'bg-purple-500',
      markerBg: 'background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);',
      borderColor: '#c084fc',
      shadowColor: 'rgba(168, 85, 247, 0.45)',
      label: '⚡ Hybrid',
      textBadge: 'bg-purple-950/90 text-purple-200 border-purple-500/50'
    };
  }

  // Status indicators & alert pulses
  let statusBadge = '';
  if (status === 'WARNING' || status === 'CURTAILED') {
    statusBadge = `
      <span class="absolute -top-1 -right-1 flex h-3 w-3">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-3 w-3 bg-amber-500 border border-white"></span>
      </span>
    `;
  } else if (status === 'CRITICAL' || status === 'TRIPPED') {
    statusBadge = `
      <span class="absolute -top-1 -right-1 flex h-3.5 w-3.5">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-500 opacity-80"></span>
        <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-rose-600 border border-white"></span>
      </span>
    `;
  }

  // Selected highlight ring
  const selectedHalo = isSelected ? `
    <span class="absolute -inset-2.5 rounded-full border-2 border-emerald-400 animate-pulse pointer-events-none" style="box-shadow: 0 0 15px rgba(52, 211, 153, 0.7)"></span>
  ` : '';

  // Clean SVG icons for Solar (Sun), Wind (Turbine), and Hybrid (Zap)
  const svgIcon = isSolar 
    ? `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white drop-shadow-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`
    : isWind
    ? `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white drop-shadow-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>`
    : `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-white drop-shadow-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`;

  const html = `
    <div class="relative flex flex-col items-center justify-center cursor-pointer group" style="transform: translateZ(0);">
      ${selectedHalo}
      <div class="relative flex items-center justify-center w-9 h-9 rounded-full shadow-lg border-2 transition-all duration-200 group-hover:scale-125" 
           style="${techTheme.markerBg} border-color: ${techTheme.borderColor}; box-shadow: 0 4px 12px ${techTheme.shadowColor};">
        ${svgIcon}
        ${statusBadge}
      </div>
      <div class="mt-1 px-1.5 py-0.5 rounded-md text-[10px] font-bold border shadow-md whitespace-nowrap pointer-events-none transition-transform duration-150 group-hover:scale-105 ${techTheme.textBadge}">
        ${techTheme.label} • ${Math.round(plant.capacity_mw).toLocaleString()} MW
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-plant-marker',
    iconSize: [80, 56],
    iconAnchor: [40, 20],
    popupAnchor: [0, -22]
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

  // Selected Basemap state (defaults to 100% free OpenStreetMap)
  const [activeBasemap, setActiveBasemap] = useState('osm');

  // Regional Balancing Hub Centroids & Estimated Interconnection Capacity
  const regionalClusters = [
    { code: 'NR', name: 'Northern Grid Corridor', center: [27.8, 73.5], capacity: '3,309 MW', color: '#10b981' },
    { code: 'WR', name: 'Western Grid Corridor', center: [23.5, 70.8], capacity: '5,790 MW', color: '#0ea5e9' },
    { code: 'SR', name: 'Southern Grid Corridor', center: [11.2, 77.4], capacity: '3,550 MW', color: '#8b5cf6' },
    { code: 'ER', name: 'Eastern Grid Corridor', center: [22.8, 86.0], capacity: '1,800 MW', color: '#f59e0b' },
  ];

  const currentBasemap = BASEMAP_PROVIDERS[activeBasemap] || BASEMAP_PROVIDERS.osm;

  return (
    <div className="relative w-full h-[620px] lg:h-[720px] rounded-3xl overflow-hidden shadow-elevated border border-slate-200">
      
      {/* Top Left: Clean Basemap Layer Switcher (Street / Satellite / Topo) */}
      <div className="absolute top-4 left-4 z-[400] flex items-center gap-1 bg-white/95 backdrop-blur-md p-1.5 rounded-2xl border border-slate-200/90 shadow-md text-xs pointer-events-auto">
        <span className="text-[11px] font-bold text-slate-500 px-2 flex items-center gap-1">
          <Layers className="w-3.5 h-3.5 text-slate-600" />
          <span className="hidden sm:inline">Map:</span>
        </span>
        {Object.values(BASEMAP_PROVIDERS).map((bm) => (
          <button
            key={bm.id}
            onClick={() => setActiveBasemap(bm.id)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-xl font-semibold transition-all ${
              activeBasemap === bm.id
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
            }`}
            title={`Switch to ${bm.name}`}
          >
            <span>{bm.icon}</span>
            <span className="hidden sm:inline">{bm.name.split(' ')[0]}</span>
          </button>
        ))}
      </div>

      {/* Top Right: Floating Quick Region Jump Controls */}
      <div className="absolute top-4 right-4 z-[400] flex flex-wrap items-center gap-1.5 bg-white/95 backdrop-blur-md p-1.5 rounded-2xl border border-slate-200/90 shadow-md text-xs pointer-events-auto">
        <span className="text-[11px] font-bold text-slate-500 px-2 hidden md:inline">Jump:</span>
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

      {/* Bottom Left: Comprehensive Plant & Grid Status Legend */}
      <div className="absolute bottom-4 left-4 z-[400] bg-white/95 backdrop-blur-md p-3.5 rounded-2xl border border-slate-200/90 shadow-lg text-xs space-y-2 pointer-events-auto max-w-xs">
        <div>
          <span className="font-extrabold text-slate-900 block text-[11px] uppercase tracking-wider mb-1.5">
            Renewable Assets
          </span>
          <div className="grid grid-cols-1 gap-1.5">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-white text-[11px] font-bold shadow-xs">
                ☀️
              </span>
              <span className="text-slate-700 font-medium">Solar Photovoltaic Farms</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-teal-500 text-white text-[11px] font-bold shadow-xs">
                💨
              </span>
              <span className="text-slate-700 font-medium">Wind Turbine Generation Parks</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-purple-500 text-white text-[11px] font-bold shadow-xs">
                ⚡
              </span>
              <span className="text-slate-700 font-medium">Hybrid Renewable Complexes</span>
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-200/80">
          <span className="font-bold text-slate-700 block text-[10px] uppercase tracking-wider mb-1">
            Operational Health
          </span>
          <div className="flex items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-xs" />
              <span className="text-slate-600">Normal</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-xs" />
              <span className="text-slate-600">Warning / Curtail</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-xs" />
              <span className="text-slate-600">Critical</span>
            </div>
          </div>
        </div>
      </div>

      {/* Leaflet Map */}
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        scrollWheelZoom={true}
        className="w-full h-full z-10"
      >
        {/* Active Free Basemap Layer (No API Key Required) */}
        <TileLayer
          key={currentBasemap.id}
          attribution={currentBasemap.attribution}
          url={currentBasemap.url}
          maxZoom={currentBasemap.maxZoom}
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
              fillOpacity: 0.07,
              weight: 1.5,
              dashArray: '4, 8'
            }}
          />
        ))}

        {/* 2. Capacity Heat Circles Overlay */}
        {filters.showHeatmap && plants.map((p) => {
          const cap = p.capacity_mw || 1000;
          const radius = Math.min(130000, Math.max(40000, cap * 24)); // radius in meters
          const color = p.plant_type === 'solar' ? '#f59e0b' : p.plant_type === 'wind' ? '#06b6d4' : '#8b5cf6';
          
          return (
            <Circle
              key={`heat-${p.id}`}
              center={[p.latitude, p.longitude]}
              radius={radius}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: 0.16,
                weight: 1.2,
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
            {/* Tamil Nadu Coastal Wind Pass */}
            <Circle
              center={[8.6, 77.6]}
              radius={95000}
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

        {/* 4. Plant Markers for Solar, Wind, and Hybrid */}
        {plants.map((plant) => {
          const telemetry = telemetryMap[plant.id] || telemetryMap[plant.code];
          const isSelected = selectedPlant && (selectedPlant.id === plant.id || selectedPlant.code === plant.code);
          const icon = createPlantIcon(plant, telemetry, isSelected);
          const genMW = telemetry?.current_generation_mw ?? (plant.capacity_mw * 0.74);
          const cuf = telemetry?.capacity_factor_pct ?? Math.round((genMW / plant.capacity_mw) * 100);
          const status = telemetry?.operational_status || plant.status || 'NORMAL';
          const isSolar = plant.plant_type === 'solar';
          const isWind = plant.plant_type === 'wind';

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
                <div className="p-2.5 max-w-xs space-y-2.5 text-slate-900 font-sans">
                  
                  {/* Popup Header */}
                  <div className="flex items-start justify-between gap-2 pb-2 border-b border-slate-200">
                    <div>
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                          isSolar ? 'bg-amber-100 text-amber-900' :
                          isWind ? 'bg-teal-100 text-teal-900' :
                          'bg-purple-100 text-purple-900'
                        }`}>
                          {isSolar ? '☀️ Solar Farm' : isWind ? '💨 Wind Park' : '⚡ Hybrid Complex'}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">#{plant.code}</span>
                      </div>
                      <h4 className="font-bold text-sm text-slate-900 leading-tight">{plant.name}</h4>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${
                      status === 'NORMAL' ? 'bg-emerald-100 text-emerald-800' :
                      status === 'WARNING' || status === 'CURTAILED' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {status}
                    </span>
                  </div>

                  {/* Telemetry Summary */}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-50 p-2 rounded-xl border border-slate-200">
                      <span className="text-[10px] text-slate-500 block font-medium">Rated Capacity</span>
                      <span className="font-bold text-slate-800 text-sm">{Number(plant.capacity_mw).toLocaleString()} MW</span>
                    </div>
                    <div className={`p-2 rounded-xl border ${
                      isSolar ? 'bg-amber-50/80 border-amber-200 text-amber-900' :
                      isWind ? 'bg-teal-50/80 border-teal-200 text-teal-900' :
                      'bg-purple-50/80 border-purple-200 text-purple-900'
                    }`}>
                      <span className="text-[10px] opacity-75 block font-medium">Live Generation</span>
                      <span className="font-bold text-sm">{Number(genMW).toFixed(1)} MW</span>
                    </div>
                  </div>

                  {/* CUF & Weather */}
                  <div className="text-[11px] text-slate-600 space-y-1 bg-slate-50/70 p-2 rounded-xl border border-slate-100">
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-slate-500">Capacity Factor (CUF):</span>
                      <span className="font-bold text-slate-800">{cuf}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-slate-500">Grid Interconnection:</span>
                      <span className="font-semibold text-slate-700">{plant.region?.name || plant.technology?.split(' ')[0] || 'Active 400kV'}</span>
                    </div>
                    {telemetry?.weather && (
                      <div className="flex justify-between items-center pt-0.5 border-t border-slate-200/60">
                        <span className="font-medium text-slate-500">Local Weather:</span>
                        <span className="font-semibold text-slate-700">
                          {isSolar ? `${Math.round(telemetry.weather.irradiance_ghi)} W/m² GHI` : `${telemetry.weather.wind_speed_100m || '8.4'} m/s Wind`} • {telemetry.weather.ambient_temp_c || '32'}°C
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <button
                    onClick={() => onSelectPlant && onSelectPlant(plant)}
                    className="w-full mt-2 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-sm active:scale-[0.98]"
                  >
                    <span>Inspect Plant Telemetry & Forecast</span>
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
