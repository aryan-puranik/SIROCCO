/** Site-level physics — same equations as scripts/build_sirocco_dataset.py */

export type Tech = "solar" | "wind";

export type SiteParams = {
  site_id: string;
  name: string;
  tech: Tech;
  lat: number;
  lon: number;
  altitude_m: number;
  ba_code: "CISO" | "ERCO";
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

export type WeatherHour = {
  ghi: number;
  dni: number;
  dhi: number;
  temp: number;
  cloud: number;
  wind80: number;
  pressure: number;
  zenith: number;
  sunAz: number;
};

function clip(x: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, x));
}

export function poaIsotropic(
  ghi: number,
  dni: number,
  dhi: number,
  zenith: number,
  azimuth: number,
  tilt: number,
  surfAz: number,
  albedo = 0.2,
) {
  const zenR = (clip(zenith, 0, 90) * Math.PI) / 180;
  const azR = (azimuth * Math.PI) / 180;
  const tiltR = (tilt * Math.PI) / 180;
  const saR = (surfAz * Math.PI) / 180;
  const aoi = Math.acos(
    clip(Math.cos(zenR) * Math.cos(tiltR) + Math.sin(zenR) * Math.sin(tiltR) * Math.cos(azR - saR), -1, 1),
  );
  const beam = dni * Math.max(Math.cos(aoi), 0);
  const sky = (dhi * (1 + Math.cos(tiltR))) / 2;
  const gnd = (ghi * albedo * (1 - Math.cos(tiltR))) / 2;
  if (zenith >= 87) return 0;
  return clip(beam + sky + gnd, 0, 1400);
}

export function pvAcMw(poa: number, tempC: number, capacityMw: number, dcAcRatio: number, gamma = -0.0038) {
  const tCell = tempC + (poa / 800) * 28;
  let dc = capacityMw * dcAcRatio * (poa / 1000) * (1 + gamma * (tCell - 25));
  dc = Math.max(dc, 0);
  let ac = Math.min(dc * 0.97, capacityMw);
  if (poa < 5) ac = 0;
  return ac;
}

export function windCf(v: number) {
  const cutIn = 3;
  const rated = 12.5;
  const cutOut = 25;
  if (v < cutIn || v >= cutOut) return 0;
  if (v >= rated) return 1;
  const x = (v - cutIn) / (rated - cutIn);
  return clip(x * x * x, 0, 1);
}

export function windAcMw(vHub: number, tempC: number, pressureHpa: number, capacityMw: number) {
  const tk = tempC + 273.15;
  const rho = (pressureHpa * 100) / (287.05 * Math.max(tk, 240));
  const dens = clip(rho / 1.225, 0.7, 1.3);
  return capacityMw * windCf(vHub) * dens;
}

export function hubWind(wind80: number, hubM: number) {
  return wind80 * (hubM / 80) ** 0.143;
}

export function physicsMw(site: SiteParams, w: WeatherHour): number {
  if (site.tech === "solar") {
    const poa = poaIsotropic(
      w.ghi,
      w.dni,
      w.dhi,
      w.zenith,
      w.sunAz,
      site.tilt_deg ?? 25,
      site.azimuth_deg ?? 180,
    );
    return pvAcMw(poa, w.temp, site.capacity_mw, site.dc_ac_ratio ?? 1.25);
  }
  const v = hubWind(w.wind80, site.hub_height_m ?? 80);
  return windAcMw(v, w.temp, w.pressure, site.capacity_mw);
}

export function applyQuantiles(
  phys: number,
  res10: number,
  res50: number,
  res90: number,
  cap: number,
  night: boolean,
) {
  if (night) return { q10: 0, q50: 0, q90: 0 };
  let q50 = clip(phys + res50, 0, cap);
  let q10 = clip(phys + res10, 0, cap);
  let q90 = clip(phys + res90, 0, cap);
  if (q10 > q50) q10 = q50;
  if (q90 < q50) q90 = q50;
  return { q10, q50, q90 };
}
