import {
  applyQuantiles,
  physicsMw,
  type SiteParams,
  type WeatherHour,
} from "./physics";

export type { SiteParams };

export type BaCode = "CISO" | "ERCO";

export type Horizon = 24 | 48 | 72;
export type Flag = "over" | "under" | "ramp" | "ok";
export type ActionId = "charge" | "discharge" | "curtail" | "backup" | "prewarm" | "hold";

export type PlantSeries = {
  ghi: number[];
  dni: number[];
  dhi: number[];
  temp: number[];
  cloud: number[];
  wind80: number[];
  pressure: number[];
  zenith: number[];
  sunAz: number[];
  yPhys: number[];
  res10: number[];
  res50: number[];
  res90: number[];
};

export type LivePayload = {
  issuedAt: string;
  horizonH: number;
  hours: string[];
  penetration: Record<BaCode, number>;
  metrics: {
    split: string;
    target: string;
    solar: { mae_pct_capacity: number; mae_skill: number; coverage_80: number };
    wind: { mae_pct_capacity: number; mae_skill: number; coverage_80: number };
  };
  sites: SiteParams[];
  ba: Record<BaCode, { demand: number[]; demandForecast: number[] }>;
  plants: Record<string, PlantSeries>;
};

export type HourPoint = {
  i: number;
  t: string;
  demand: number;
  fleet10: number;
  fleet50: number;
  fleet90: number;
  solar50: number;
  wind50: number;
  baRen10: number;
  baRen50: number;
  baRen90: number;
  share: number;
  net: number;
  flag: Flag;
  action: ActionId;
  soc: number;
  surplus: number;
};

export type EventRow = {
  id: string;
  type: Exclude<Flag, "ok">;
  action: ActionId;
  start: number;
  end: number;
  startIso: string;
  endIso: string;
  hours: number;
  mw: number;
  share: number;
  confidence: number;
  costUsd: number;
  tco2: number;
};

export type PlantNow = {
  site: SiteParams;
  q10: number[];
  q50: number[];
  q90: number[];
  cf: number;
  dirty: boolean;
};

export type Board = {
  points: HourPoint[];
  events: EventRow[];
  plants: PlantNow[];
  storageMwh: number;
  fleetCap: number;
  kpi: {
    gen: number;
    demand: number;
    net: number;
    share: number;
    status: Flag;
    overH: number;
    underH: number;
    rampH: number;
    soc: number;
  };
};

const COST_CURTAIL = 32;
const COST_BACKUP = 165;
const CO2_BACKUP = 0.42;


function clip(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n));
}

export function cloneSites(sites: SiteParams[]): Record<string, SiteParams> {
  const out: Record<string, SiteParams> = {};
  for (const s of sites) out[s.site_id] = { ...s };
  return out;
}

export function paramsEqual(a: SiteParams, b: SiteParams) {
  return (
    near(a.tilt_deg, b.tilt_deg) &&
    near(a.azimuth_deg, b.azimuth_deg) &&
    near(a.dc_ac_ratio, b.dc_ac_ratio) &&
    near(a.hub_height_m, b.hub_height_m) &&
    near(a.storage_mwh, b.storage_mwh)
  );
}

function near(a: number | null | undefined, b: number | null | undefined) {
  if (a == null && b == null) return true;
  if (a == null || b == null) return false;
  return Math.abs(a - b) < 1e-4;
}

function weatherAt(p: PlantSeries, i: number): WeatherHour {
  return {
    ghi: p.ghi[i],
    dni: p.dni[i],
    dhi: p.dhi[i],
    temp: p.temp[i],
    cloud: p.cloud[i],
    wind80: p.wind80[i],
    pressure: p.pressure[i],
    zenith: p.zenith[i],
    sunAz: p.sunAz[i],
  };
}

export function computeBoard(
  live: LivePayload,
  params: Record<string, SiteParams>,
  ba: BaCode,
  horizon: Horizon,
  focus = 0,
): Board {
  const n = Math.min(horizon, live.hours.length);
  const sites = live.sites.filter((s) => s.ba_code === ba).map((s) => params[s.site_id] ?? s);
  const fleetCap = sites.reduce((a, s) => a + s.capacity_mw, 0);
  const storageMwh = sites.reduce((a, s) => a + s.storage_mwh, 0);
  const pen = live.penetration[ba];
  const demandArr = live.ba[ba].demand;

  const plantNow: PlantNow[] = sites.map((site) => {
    const series = live.plants[site.site_id];
    const q10: number[] = [];
    const q50: number[] = [];
    const q90: number[] = [];
    const orig = live.sites.find((s) => s.site_id === site.site_id)!;
    for (let i = 0; i < n; i++) {
      const w = weatherAt(series, i);
      const phys = physicsMw(site, w);
      const night = site.tech === "solar" && w.zenith >= 87;
      const q = applyQuantiles(phys, series.res10[i], series.res50[i], series.res90[i], site.capacity_mw, night);
      q10.push(q.q10);
      q50.push(q.q50);
      q90.push(q.q90);
    }
    return {
      site,
      q10,
      q50,
      q90,
      cf: fleetCap > 0 ? q50[clip(focus, 0, n - 1)] / site.capacity_mw : 0,
      dirty: !paramsEqual(site, orig),
    };
  });

  const points: HourPoint[] = [];

  for (let i = 0; i < n; i++) {
    const demand = demandArr[i];
    let fleet10 = 0,
      fleet50 = 0,
      fleet90 = 0,
      solar50 = 0,
      wind50 = 0;
    for (const p of plantNow) {
      fleet10 += p.q10[i];
      fleet50 += p.q50[i];
      fleet90 += p.q90[i];
      if (p.site.tech === "solar") solar50 += p.q50[i];
      else wind50 += p.q50[i];
    }
    const cf = fleetCap > 0 ? fleet50 / fleetCap : 0;
    const cf10 = fleetCap > 0 ? fleet10 / fleetCap : 0;
    const cf90 = fleetCap > 0 ? fleet90 / fleetCap : 0;
    const baRen50 = cf * pen * demand;
    const baRen10 = cf10 * pen * demand;
    const baRen90 = cf90 * pen * demand;
    const share = demand > 0 ? baRen50 / demand : 0;
    const net = demand - baRen50;
    points.push({
      i,
      t: live.hours[i],
      demand,
      fleet10,
      fleet50,
      fleet90,
      solar50,
      wind50,
      baRen10,
      baRen50,
      baRen90,
      share,
      net,
      flag: "ok",
      action: "hold",
      soc: 0,
      surplus: 0,
    });
  }

  const nets = points.map((p) => p.net);
  const qOver = quantile(nets, 0.18);
  const qUnder = quantile(nets, 0.82);
  const medNet = quantile(nets, 0.5);

  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    p.surplus = medNet - p.net;
    if (p.net <= qOver) p.flag = "over";
    else if (p.net >= qUnder) p.flag = "under";
    else if (i > 0 && Math.abs(p.fleet50 - points[i - 1].fleet50) > 0.12 * fleetCap) p.flag = "ramp";
  }

  let soc = storageMwh * 0.45;
  const cRate = Math.max(storageMwh * 0.35, 1);
  for (const p of points) {
    const headroom = Math.max(storageMwh - soc, 0);
    if (p.flag === "over") {
      if (headroom > 8) {
        p.action = "charge";
        soc += Math.min(Math.max(p.surplus, 0), headroom, cRate);
      } else p.action = "curtail";
    } else if (p.flag === "under") {
      if (soc > 8) {
        p.action = "discharge";
        soc -= Math.min(Math.max(-p.surplus, 0), soc, cRate);
      } else p.action = "backup";
    } else if (p.flag === "ramp") {
      p.action = "prewarm";
    }
    soc = clip(soc, 0, storageMwh);
    p.soc = soc;
  }


  const events = mergeEvents(points, live.hours);
  const fi = clip(focus, 0, n - 1);
  const cur = points[fi];

  return {
    points,
    events,
    plants: plantNow,
    storageMwh,
    fleetCap,
    kpi: {
      gen: cur.fleet50,
      demand: cur.demand,
      net: cur.net,
      share: cur.share,
      status: cur.flag,
      overH: points.filter((p) => p.flag === "over").length,
      underH: points.filter((p) => p.flag === "under").length,
      rampH: points.filter((p) => p.flag === "ramp").length,
      soc: storageMwh > 0 ? cur.soc / storageMwh : 0,
    },
  };
}

function mergeEvents(points: HourPoint[], hours: string[]): EventRow[] {
  const out: EventRow[] = [];
  let i = 0;
  while (i < points.length) {
    const f = points[i].flag;
    if (f === "ok") {
      i += 1;
      continue;
    }
    let j = i + 1;
    while (j < points.length && points[j].flag === f) j += 1;
    const slice = points.slice(i, j);
    const mw = mean(slice.map((p) => Math.abs(p.surplus)));
    const share = mean(slice.map((p) => p.share));
    const width = mean(slice.map((p) => (p.fleet50 > 1 ? (p.fleet90 - p.fleet10) / p.fleet50 : 0.4)));
    const confidence = clip(1 - width * 0.7, 0.35, 0.97);
    const action = majority(slice.map((p) => p.action));
    const hoursN = j - i;
    let costUsd = 0;
    let tco2 = 0;
    if (action === "curtail") costUsd = mw * hoursN * COST_CURTAIL;
    if (action === "backup") {
      costUsd = mw * hoursN * COST_BACKUP;
      tco2 = mw * hoursN * CO2_BACKUP;
    }
    if (action === "charge" || action === "discharge") costUsd = mw * hoursN * 8;
    out.push({
      id: `${f}-${i}`,
      type: f,
      action,
      start: i,
      end: j - 1,
      startIso: hours[i],
      endIso: hours[j - 1],
      hours: hoursN,
      mw,
      share,
      confidence,
      costUsd,
      tco2,
    });
    i = j;
  }
  return out.sort((a, b) => b.mw * b.hours - a.mw * a.hours);
}

function quantile(xs: number[], q: number) {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const i = clip(q, 0, 1) * (s.length - 1);
  const lo = Math.floor(i);
  const hi = Math.ceil(i);
  if (lo === hi) return s[lo];
  return s[lo] * (hi - i) + s[hi] * (i - lo);
}

function mean(xs: number[]) {
  if (!xs.length) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

function majority(xs: ActionId[]): ActionId {
  const c = new Map<ActionId, number>();
  for (const x of xs) c.set(x, (c.get(x) ?? 0) + 1);
  let best: ActionId = xs[0] ?? "hold";
  let n = 0;
  for (const [k, v] of c) {
    if (v > n) {
      best = k;
      n = v;
    }
  }
  return best;
}

export const ACTION_LABEL: Record<ActionId, string> = {
  charge: "CHARGE",
  discharge: "DISCHARGE",
  curtail: "CURTAIL",
  backup: "BACKUP",
  prewarm: "PREWARM",
  hold: "HOLD",
};

export const FLAG_LABEL: Record<Flag, string> = {
  over: "OVER",
  under: "UNDER",
  ramp: "RAMP",
  ok: "STABLE",
};
