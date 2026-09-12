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

export default {
  checkBackendHealth
};
