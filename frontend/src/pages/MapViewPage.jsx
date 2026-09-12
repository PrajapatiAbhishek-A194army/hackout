import React, { useState, useEffect } from 'react';
import { 
  Compass, 
  Layers, 
  Activity, 
  Zap, 
  Sun, 
  Wind, 
  ShieldAlert, 
  Radio, 
  RefreshCw,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  MapPin
} from 'lucide-react';
import { RenewableMap, MapFilterBar, PlantDrawer } from '../components/Map';
import { Badge } from '../components';
import { 
  fetchPlants, 
  fetchRegions, 
  fetchCurrentTelemetry, 
  fetchAlertsSummary,
  fetchFarmForecast 
} from '../services/api';

export default function MapViewPage({ onSwitchToOverview }) {
  const [plants, setPlants] = useState([]);
  const [regions, setRegions] = useState([]);
  const [telemetry, setTelemetry] = useState(null);
  const [alertsSummary, setAlertsSummary] = useState(null);
  const [selectedPlant, setSelectedPlant] = useState(null);
  const [plantForecast, setPlantForecast] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Map Filter State
  const [filters, setFilters] = useState({
    type: 'all',
    status: 'all',
    region: 'all',
    minCapacity: 0,
    showHeatmap: true,
    showWeather: true,
    showRegionalClusters: true
  });

  // Load Initial Spatial & Telemetry Data
  const loadData = async () => {
    try {
      setLoading(true);
      const [plantsData, regionsData, telemData, alertData] = await Promise.all([
        fetchPlants(),
        fetchRegions(),
        fetchCurrentTelemetry(),
        fetchAlertsSummary()
      ]);

      setPlants(plantsData || []);
      setRegions(regionsData || []);
      setTelemetry(telemData || null);
      setAlertsSummary(alertData || null);
      setLastUpdated(new Date());

      // Default select first plant (e.g. Bhadla Solar)
      if (plantsData && plantsData.length > 0 && !selectedPlant) {
        setSelectedPlant(plantsData[0]);
      }
    } catch (err) {
      console.error('Failed to load spatial map data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Poll telemetry every 15 seconds
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  // Fetch forecast for selected plant
  useEffect(() => {
    if (selectedPlant?.code || selectedPlant?.id) {
      const identifier = selectedPlant.code || selectedPlant.id;
      fetchFarmForecast(identifier, 24).then((res) => {
        if (res && res.forecast_points) {
          setPlantForecast(res.forecast_points.map(pt => ({
            hour: pt.timestamp ? new Date(pt.timestamp).getHours() + ':00' : '00:00',
            predicted_mw: Math.round(pt.predicted_mw),
            lower_ci: Math.round(pt.lower_bound_mw || pt.predicted_mw * 0.9),
            upper_ci: Math.round(pt.upper_bound_mw || pt.predicted_mw * 1.1)
          })));
        } else {
          setPlantForecast([]);
        }
      });
    }
  }, [selectedPlant]);

  // Telemetry map indexed by plant ID and Code
  const telemetryMap = {};
  if (telemetry?.plants) {
    telemetry.plants.forEach(p => {
      telemetryMap[p.plant_id] = p;
      telemetryMap[p.plant_code] = p;
    });
  }

  // Filter Plants
  const filteredPlants = plants.filter((plant) => {
    // Type filter
    if (filters.type !== 'all' && plant.plant_type !== filters.type) return false;
    
    // Status filter
    const plantTelem = telemetryMap[plant.id] || telemetryMap[plant.code];
    const opStatus = (plantTelem?.operational_status || plant.status || 'NORMAL').toLowerCase();
    if (filters.status !== 'all' && opStatus !== filters.status.toLowerCase()) return false;
    
    // Region filter
    if (filters.region !== 'all') {
      const matchRegion = regions.find(r => r.code === filters.region || r.name === filters.region);
      if (matchRegion && plant.region_id !== matchRegion.id) return false;
    }
    
    // Capacity filter
    if (plant.capacity_mw < filters.minCapacity) return false;

    return true;
  });

  // Calculate live stats
  const totalFilteredCapacity = filteredPlants.reduce((sum, p) => sum + (p.capacity_mw || 0), 0);
  const totalLiveOutput = filteredPlants.reduce((sum, p) => {
    const t = telemetryMap[p.id] || telemetryMap[p.code];
    return sum + (t?.current_generation_mw || p.capacity_mw * 0.72);
  }, 0);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters({
      type: 'all',
      status: 'all',
      region: 'all',
      minCapacity: 0,
      showHeatmap: true,
      showWeather: true,
      showRegionalClusters: true
    });
  };

  return (
    <div className="space-y-6 py-6 animate-fadeIn">
      
      {/* Top Spatial Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/95 backdrop-blur-md p-5 rounded-3xl border border-slate-200/90 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-emerald-100 text-emerald-800">
              <Compass className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
              Interactive Renewable Generation Map
            </h1>
            <Badge variant="normal" dot pulse>
              Live GIS View
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 max-w-2xl">
            Spatially visualize national renewable generation nodes, corridor power flows, regional balancing clusters, and atmospheric telemetry.
          </p>
        </div>

        {/* Action Buttons & Telemetry Frequency */}
        <div className="flex items-center gap-3 shrink-0">
          {telemetry?.grid && (
            <div className="hidden sm:flex flex-col text-right text-xs bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200/70">
              <span className="text-slate-400 font-medium">Grid Frequency</span>
              <span className="font-bold text-slate-900 font-mono">
                {telemetry.grid.grid_frequency_hz} Hz ({telemetry.grid.frequency_status})
              </span>
            </div>
          )}

          <button
            onClick={loadData}
            title="Refresh spatial telemetry"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-emerald-600' : 'text-slate-500'}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {onSwitchToOverview && (
            <button
              onClick={onSwitchToOverview}
              className="flex items-center gap-1 px-3 py-2 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-xl hover:bg-emerald-100 transition-colors"
            >
              <span>National Overview</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Filter & Live Statistics Ribbon */}
      <MapFilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        regions={regions}
        stats={{
          totalCount: filteredPlants.length,
          totalCapacity: Math.round(totalFilteredCapacity),
          liveOutput: Math.round(totalLiveOutput),
          alertCount: alertsSummary?.total_active_alerts || 2
        }}
      />

      {/* Main Map & Interactive Side Drawer Section */}
      <div className="relative flex flex-col lg:flex-row gap-5 items-start">
        
        {/* Interactive Leaflet Map */}
        <div className="flex-1 w-full min-w-0">
          <RenewableMap
            plants={filteredPlants}
            telemetryMap={telemetryMap}
            selectedPlant={selectedPlant}
            onSelectPlant={(plant) => setSelectedPlant(plant)}
            filters={filters}
          />
        </div>

        {/* Slide-out / Sticky Plant Telemetry Drawer */}
        {selectedPlant && (
          <div className="w-full lg:w-96 shrink-0">
            <PlantDrawer
              plant={selectedPlant}
              telemetry={telemetryMap[selectedPlant.id] || telemetryMap[selectedPlant.code]}
              forecastData={plantForecast}
              alerts={alertsSummary?.alerts || []}
              onClose={() => setSelectedPlant(null)}
            />
          </div>
        )}

      </div>

      {/* Bottom Quick-Jump Plant Cards */}
      <div className="bg-white/95 backdrop-blur-md rounded-3xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-900">National Renewable Generation Nodes</h3>
          </div>
          <span className="text-xs text-slate-400">Click card to zoom & inspect</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {plants.map((plant) => {
            const isSelected = selectedPlant?.id === plant.id;
            const t = telemetryMap[plant.id] || telemetryMap[plant.code];
            const status = t?.operational_status || plant.status || 'NORMAL';
            
            return (
              <div
                key={plant.id}
                onClick={() => setSelectedPlant(plant)}
                className={`cursor-pointer p-3 rounded-2xl border transition-all ${
                  isSelected 
                    ? 'border-emerald-500 bg-emerald-50/50 shadow-sm ring-2 ring-emerald-500/20' 
                    : 'border-slate-200/80 bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`w-2 h-2 rounded-full ${
                    status === 'NORMAL' ? 'bg-emerald-500' :
                    status === 'WARNING' ? 'bg-amber-500' : 'bg-rose-500'
                  }`} />
                  <span className="text-[10px] font-bold text-slate-400 uppercase">
                    {plant.plant_type}
                  </span>
                </div>
                <h4 className="font-bold text-xs text-slate-900 truncate mb-1" title={plant.name}>
                  {plant.name.split(' ')[0]} {plant.name.split(' ')[1] || ''}
                </h4>
                <div className="text-[11px] text-emerald-700 font-bold">
                  {Number(plant.capacity_mw).toLocaleString()} MW
                </div>
                <div className="text-[10px] text-slate-400 truncate">
                  {plant.code}
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
