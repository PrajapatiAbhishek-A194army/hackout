const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with status: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    return {
      status: 'offline',
      service: 'Unavailable',
      error: err.message,
      database: 'unreachable'
    };
  }
}

export async function fetchPlants(params = {}) {
  try {
    const query = new URLSearchParams();
    if (params.plant_type) query.append('plant_type', params.plant_type);
    if (params.region_id) query.append('region_id', params.region_id);
    if (params.state_id) query.append('state_id', params.state_id);
    if (params.status) query.append('status', params.status);
    
    const url = `${API_BASE_URL}/plants${query.toString() ? `?${query.toString()}` : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch plants: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('fetchPlants error:', err);
    return [];
  }
}

export async function fetchPlantDetail(plantId) {
  try {
    const res = await fetch(`${API_BASE_URL}/plants/${plantId}`);
    if (!res.ok) throw new Error(`Failed to fetch plant detail: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`fetchPlantDetail error for plant ${plantId}:`, err);
    return null;
  }
}

export async function fetchRegions() {
  try {
    const res = await fetch(`${API_BASE_URL}/regions`);
    if (!res.ok) throw new Error(`Failed to fetch regions: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('fetchRegions error:', err);
    return [];
  }
}

export async function fetchStates(regionId = null) {
  try {
    const url = regionId ? `${API_BASE_URL}/regions/states?region_id=${regionId}` : `${API_BASE_URL}/regions/states`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch states: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('fetchStates error:', err);
    return [];
  }
}

export async function fetchCurrentTelemetry() {
  try {
    const res = await fetch(`${API_BASE_URL}/telemetry/current`);
    if (!res.ok) throw new Error(`Failed to fetch live telemetry: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('fetchCurrentTelemetry error:', err);
    return null;
  }
}

export async function fetchAlertsSummary() {
  try {
    const res = await fetch(`${API_BASE_URL}/alerts/stats/summary`);
    if (!res.ok) throw new Error(`Failed to fetch alerts summary: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('fetchAlertsSummary error:', err);
    return null;
  }
}

export async function fetchFarmForecast(plantIdOrCode, horizonHours = 24) {
  try {
    const res = await fetch(`${API_BASE_URL}/aggregate/farm/${plantIdOrCode}?horizon_hours=${horizonHours}`);
    if (!res.ok) throw new Error(`Failed to fetch farm forecast: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`fetchFarmForecast error for ${plantIdOrCode}:`, err);
    return null;
  }
}

export async function fetchNationalForecast(horizonHours = 24) {
  try {
    const res = await fetch(`${API_BASE_URL}/aggregate/national?horizon_hours=${horizonHours}`);
    if (!res.ok) throw new Error(`Failed to fetch national forecast: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('fetchNationalForecast error:', err);
    return null;
  }
}

export default {
  checkBackendHealth,
  fetchPlants,
  fetchPlantDetail,
  fetchRegions,
  fetchStates,
  fetchCurrentTelemetry,
  fetchAlertsSummary,
  fetchFarmForecast,
  fetchNationalForecast
};
