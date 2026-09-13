export type Tech = "solar" | "wind";

export type Site = {
  site_id: string;
  name: string;
  tech: Tech;
  lat: number;
  lon: number;
  altitude_m: number;
  ba_code: string;
  ba_name: string;
  capacity_mw: number;
  timezone: string;
  tilt_deg: number | null;
  azimuth_deg: number | null;
  dc_ac_ratio: number | null;
  hub_height_m: number | null;
  rotor_d_m: number | null;
  turbine_type: string | null;
  storage_mwh: number;
  region: string;
};

export type Overview = {
  built_at: string;
  sites: number;
  weather_rows: number;
  generation_rows: number;
  ba_rows: number;
  panel_rows: number;
  train_h24_rows: number;
  forecast_rows: number;
  start: string;
  end: string;
  capacity_mw_total: number;
  sources: Record<string, string>;
  notes: string[];
};

export type DailyRow = {
  site_id: string;
  tech: Tech;
  ba_code: string;
  date: string;
  y_mwh: number;
  cf_mean: number;
  ghi_mean: number;
  wind_mean: number;
  temp_mean: number;
  flag_over: number;
  flag_under: number;
  demand_mean: number;
};

export type HourlyRow = {
  site_id: string;
  timestamp_utc: string;
  tech: Tech;
  y_physics_mw: number;
  ghi_wm2: number;
  wind_ms_80: number;
  temp_c: number;
  capacity_factor: number;
  demand_mw: number;
  net_load_mw: number;
  flag_over: number;
  flag_under: number;
  flag_ramp: number;
};

export type BaDaily = {
  ba_code: string;
  date: string;
  demand_mean: number;
  demand_max: number;
  renewable_mean: number;
  net_load_mean: number;
  over_hours: number;
  under_hours: number;
};

export type ForecastRow = {
  site_id: string;
  timestamp_utc: string;
  tech: Tech;
  ba_code: string;
  horizon_h: number;
  ghi_wm2: number;
  temp_c: number;
  cloud_pct: number;
  wind_ms_80: number;
  y_physics_mw: number;
  q10_mw: number;
  q50_mw: number;
  q90_mw: number;
  capacity_mw: number;
  capacity_factor: number;
  demand_forecast_mw: number;
  demand_mw: number;
};

export type TrainRow = {
  site_id: string;
  tech: Tech;
  horizon_h: number;
  y_mw: number;
  y_physics_nwp_mw: number;
  residual_mw: number;
  nwp_ghi_wm2: number;
  actual_ghi_wm2: number;
  nwp_wind_ms_80: number;
  actual_wind_ms_80: number;
};

export const TABS = [
  { id: "pipeline", label: "Pipeline" },
  { id: "fleet", label: "Fleet" },
  { id: "history", label: "History" },
  { id: "grid", label: "Grid" },
  { id: "model", label: "Model I/O" },
  { id: "live", label: "Live 72h" },
  { id: "files", label: "Files" },
] as const;

export type TabId = (typeof TABS)[number]["id"];

export const DOWNLOADS = [
  { file: "sites.csv", label: "sites.csv", grain: "1 row = plant", rows: "8" },
  { file: "weather_hourly.csv.gz", label: "weather_hourly.csv.gz", grain: "site × hour", rows: "140,160" },
  { file: "generation_hourly.csv.gz", label: "generation_hourly.csv.gz", grain: "site × hour", rows: "140,160" },
  { file: "ba_hourly.csv.gz", label: "ba_hourly.csv.gz", grain: "BA × hour", rows: "35,040" },
  { file: "panel_hourly.csv.gz", label: "panel_hourly.csv.gz", grain: "S ⋈ W ⋈ P ⋈ D", rows: "140,160" },
  { file: "model_train_h24.csv.gz", label: "model_train_h24.csv.gz", grain: "issue × horizon 24", rows: "46,528" },
  { file: "model_train_h48.csv.gz", label: "model_train_h48.csv.gz", grain: "issue × horizon 48", rows: "46,464" },
  { file: "model_train_h72.csv.gz", label: "model_train_h72.csv.gz", grain: "issue × horizon 72", rows: "46,400" },
  { file: "forecast_72h.csv", label: "forecast_72h.csv", grain: "site × future hour", rows: "576" },
  { file: "schema.json", label: "schema.json", grain: "dictionary", rows: "—" },
  { file: "manifest.json", label: "manifest.json", grain: "build metadata", rows: "—" },
];

export function fmtMw(n: number | null | undefined, digits = 0) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function fmtPct(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(0)}%`;
}

export function shortTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    hour12: false,
  });
}

export function shortDate(iso: string) {
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}
