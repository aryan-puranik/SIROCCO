const API_BASE = '/api';

export const fetchPortfolioOverview = async () => {
  const res = await fetch(`${API_BASE}/sites/portfolio/overview`);
  if (!res.ok) throw new Error('Failed to fetch portfolio overview');
  return res.json();
};

export const fetchSites = async () => {
  const res = await fetch(`${API_BASE}/sites`);
  if (!res.ok) throw new Error('Failed to fetch sites');
  return res.json();
};

export const fetchSiteForecast = async (siteId, horizon = '24h') => {
  const res = await fetch(`${API_BASE}/forecasts/${siteId}?horizon=${horizon}`);
  if (!res.ok) throw new Error(`Failed to fetch forecast for site ${siteId}`);
  return res.json();
};

export const fetchExplainability = async (siteId) => {
  const res = await fetch(`${API_BASE}/explainability/${siteId}`);
  if (!res.ok) throw new Error(`Failed to fetch explainability for site ${siteId}`);
  return res.json();
};

export const runWhatIfSimulation = async (params) => {
  const res = await fetch(`${API_BASE}/simulator/what-if`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error('Failed to run what-if simulation');
  return res.json();
};

export const fetchAlerts = async () => {
  const res = await fetch(`${API_BASE}/faults-and-alerts`);
  if (!res.ok) throw new Error('Failed to fetch alerts');
  return res.json();
};

export const fetchRecommendations = async () => {
  const res = await fetch(`${API_BASE}/decision-engine`);
  if (!res.ok) throw new Error('Failed to fetch recommendations');
  return res.json();
};

export const fetchMetrics = async () => {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
};
