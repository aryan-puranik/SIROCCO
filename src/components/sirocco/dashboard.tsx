import { useEffect, useMemo, useState } from "react";
import {
  ACTION_LABEL,
  FLAG_LABEL,
  cloneSites,
  computeBoard,
  type ActionId,
  type BaCode,
  type Flag,
  type Horizon,
  type LivePayload,
  type SiteParams,
} from "@/lib/engine";
import { cn } from "@/lib/cn";
import { clockLabel, fmtK, fmtMw, hourLabel } from "@/lib/format";
import liveJson from "@/data/live.json";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const LIVE = liveJson as LivePayload;
const HORIZONS: Horizon[] = [24, 48, 72];


function flagClass(f: Flag) {
  if (f === "over") return "text-over";
  if (f === "under") return "text-under";
  if (f === "ramp") return "text-ramp";
  return "text-muted";
}

function flagBg(f: Flag) {
  if (f === "over") return "bg-over";
  if (f === "under") return "bg-under";
  if (f === "ramp") return "bg-ramp";
  return "bg-subtle";
}

function actionClass(a: ActionId) {
  if (a === "charge" || a === "discharge") return "text-accent";
  if (a === "curtail" || a === "backup") return "text-danger";
  if (a === "prewarm") return "text-warn";
  return "text-muted";
}

export function Dashboard() {
  const live = LIVE;
  const [ba, setBa] = useState<BaCode>("CISO");
  const [horizon, setHorizon] = useState<Horizon>(72);
  const [params, setParams] = useState<Record<string, SiteParams>>(() => cloneSites(live.sites));
  const [selected, setSelected] = useState<string | null>(
    live.sites.find((s) => s.ba_code === "CISO")?.site_id ?? live.sites[0]?.site_id ?? null,
  );
  const [focus, setFocus] = useState(0);

  useEffect(() => {
    const now = Date.now();
    const idx = live.hours.findIndex((h) => new Date(h).getTime() >= now);
    if (idx >= 0) setFocus(idx);
  }, [live.hours]);

  const board = useMemo(() => computeBoard(live, params, ba, horizon, focus), [live, params, ba, horizon, focus]);

  const selectedSite = selected && params[selected] ? params[selected] : null;
  const selectedPlant = board.plants.find((p) => p.site.site_id === selected) ?? null;
  const defaults = live.sites.find((s) => s.site_id === selected);

  function patch(id: string, partial: Partial<SiteParams>) {
    setParams((prev) => ({ ...prev, [id]: { ...prev[id], ...partial } }));
  }

  function resetSite(id: string) {
    const orig = live.sites.find((s) => s.site_id === id);
    if (!orig) return;
    setParams((prev) => ({ ...prev, [id]: { ...orig } }));
  }

  const focusSafe = Math.min(focus, board.points.length - 1);
  const cur = board.points[focusSafe];

  return (
    <div className="min-h-dvh overflow-x-hidden bg-bg text-fg">
      <header className="sticky top-0 z-30 border-b border-border bg-bg/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-2 px-3 py-2.5 sm:gap-3 sm:px-5">
          <div className="flex items-baseline gap-3">
            <h1 className="text-lg font-medium tracking-tight sm:text-xl">Sirocco</h1>
            <span className="hidden items-center gap-1.5 whitespace-nowrap font-mono text-xs tracking-[0.18em] text-accent uppercase sm:inline-flex">
              <span className="live-dot size-1.5 rounded-full bg-accent" />
              Live
            </span>
          </div>
          <div className="ml-auto flex items-center gap-1">
            {(["CISO", "ERCO"] as BaCode[]).map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => {
                  setBa(code);
                  const first = live.sites.find((s) => s.ba_code === code);
                  setSelected(first?.site_id ?? null);
                }}
                className={cn(
                  "h-8 rounded-sm px-2 font-mono text-xs tracking-wide sm:px-2.5",
                  ba === code ? "bg-fg text-bg" : "text-muted hover:text-fg",
                )}
              >
                {code === "CISO" ? "CAISO" : "ERCOT"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-0.5 rounded-sm bg-bg-subtle p-0.5">
            {HORIZONS.map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => setHorizon(h)}
                className={cn(
                  "h-7 rounded-sm px-2 font-mono text-xs",
                  horizon === h ? "bg-bg-elevated text-fg" : "text-muted hover:text-fg",
                )}
              >
                {h}h
              </button>
            ))}
          </div>
          <time className="hidden font-mono text-xs text-subtle tabular-nums md:block">
            {clockLabel(cur.t)} UTC
          </time>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1400px] gap-3 px-3 py-3 sm:px-5 sm:py-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Kpi board={board} />

        <section className="min-w-0 rounded-lg border border-border bg-bg-elevated p-3 lg:col-span-1 lg:row-start-2">
          <div className="mb-2 flex items-end justify-between">
            <h2 className="text-xs tracking-[0.16em] text-subtle uppercase">Generation</h2>
            <div className="flex gap-3 font-mono text-[10px] tracking-wide text-muted uppercase">
              <span className="flex items-center gap-1.5">
                <i className="size-2 rounded-full bg-solar" /> Solar
              </span>
              <span className="flex items-center gap-1.5">
                <i className="size-2 rounded-full bg-wind" /> Wind
              </span>
              <span className="flex items-center gap-1.5">
                <i className="size-2 rounded-full bg-fg/50" /> P10–P90
              </span>
            </div>
          </div>
          <Ribbon points={board.points} focus={focusSafe} onFocus={setFocus} />
        </section>

        <Actions events={board.events} focus={focusSafe} onFocus={setFocus} />

        <Heatmap points={board.points} focus={focusSafe} onFocus={setFocus} />

        <Fleet
          plants={board.plants}
          selected={selected}
          onSelect={(id) => setSelected((s) => (s === id ? null : id))}
        />

        <SitePanel
          site={selectedSite}
          plant={selectedPlant}
          orig={defaults}
          hours={live.hours.slice(0, board.points.length)}
          onPatch={patch}
          onReset={resetSite}
        />
      </main>
    </div>
  );
}

function Kpi({ board }: { board: NonNullable<ReturnType<typeof computeBoard>> }) {
  const { kpi } = board;
  const items = [
    { k: "GEN", v: `${fmtMw(kpi.gen, 0)}`, u: "MW", c: "text-fg" },
    { k: "DEMAND", v: `${fmtK(kpi.demand, 1)}`, u: "MW", c: "text-fg" },
    { k: "NET", v: `${fmtK(kpi.net, 1)}`, u: "MW", c: flagClass(kpi.status) },
    { k: "SHARE", v: `${(kpi.share * 100).toFixed(0)}`, u: "%", c: flagClass(kpi.status) },
    { k: "STATUS", v: FLAG_LABEL[kpi.status], u: "", c: flagClass(kpi.status) },
    { k: "SOC", v: `${(kpi.soc * 100).toFixed(0)}`, u: "%", c: "text-accent" },
  ];
  return (
    <section className="grid grid-cols-3 gap-2 sm:grid-cols-6 lg:col-span-2">
      {items.map((it) => (
        <div key={it.k} className="rounded-md border border-border bg-bg-elevated px-3 py-2.5">
          <p className="font-mono text-[10px] tracking-[0.16em] text-subtle uppercase">{it.k}</p>
          <p className={cn("mt-1 font-mono text-2xl leading-none tabular-nums sm:text-3xl", it.c)}>
            {it.v}
            <span className="ml-1 text-xs text-subtle">{it.u}</span>
          </p>
        </div>
      ))}
    </section>
  );
}

function Ribbon({
  points,
  focus,
  onFocus,
}: {
  points: ReturnType<typeof computeBoard>["points"];
  focus: number;
  onFocus: (i: number) => void;
}) {
  const data = points.map((p) => ({
    i: p.i,
    t: p.t,
    fleet10: p.fleet10,
    fleet50: p.fleet50,
    fleet90: p.fleet90,
    solar50: p.solar50,
    wind50: p.wind50,
    band: Math.max(p.fleet90 - p.fleet10, 0),
    flag: p.flag,
    share: p.share,
  }));
  return (
    <div>
      <div className="h-60 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            onClick={(e) => {
              const i = (e as { activeTooltipIndex?: number } | null)?.activeTooltipIndex;
              if (typeof i === "number") onFocus(i);
            }}
          >
          <CartesianGrid stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="i"
            tickFormatter={(v) => {
              const p = points[Number(v)];
              return p ? hourLabel(p.t).replace(" ", "\n") : "";
            }}
            interval={11}
            tick={{ fill: "var(--color-subtle)", fontSize: 10, fontFamily: "IBM Plex Mono" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => fmtK(Number(v), 1)}
            width={44}
            tick={{ fill: "var(--color-subtle)", fontSize: 10, fontFamily: "IBM Plex Mono" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ stroke: "var(--color-fg)", strokeOpacity: 0.25 }}
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const p = payload[0].payload as (typeof data)[0];
              return (
                <div className="rounded-sm border border-border bg-bg px-2.5 py-2 font-mono text-xs">
                  <p className="text-subtle">{hourLabel(p.t)}</p>
                  <p className="mt-1 tabular-nums">{fmtMw(p.fleet50, 0)} MW</p>
                  <p className={cn("tabular-nums", flagClass(p.flag))}>
                    {FLAG_LABEL[p.flag]} {(p.share * 100).toFixed(0)}%
                  </p>
                </div>
              );
            }}
          />
          <Area dataKey="fleet10" stackId="b" fill="transparent" stroke="none" isAnimationActive={false} />
          <Area
            dataKey="band"
            stackId="b"
            fill="var(--color-fg)"
            fillOpacity={0.12}
            stroke="none"
            isAnimationActive={false}
          />
          <Area
            dataKey="solar50"
            stackId="g"
            fill="var(--color-solar)"
            fillOpacity={0.55}
            stroke="none"
            isAnimationActive={false}
          />
          <Area
            dataKey="wind50"
            stackId="g"
            fill="var(--color-wind)"
            fillOpacity={0.55}
            stroke="none"
            isAnimationActive={false}
          />
          <Line
            dataKey="fleet50"
            stroke="var(--color-fg)"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
        </ResponsiveContainer>
      </div>
      <FocusBar n={points.length} focus={focus} flags={points.map((p) => p.flag)} onFocus={onFocus} />
    </div>
  );
}

function FocusBar({
  n,
  focus,
  flags,
  onFocus,
}: {
  n: number;
  focus: number;
  flags: Flag[];
  onFocus: (i: number) => void;
}) {
  return (
    <div className="mt-2 flex h-2 overflow-hidden rounded-full">
      {Array.from({ length: n }).map((_, i) => (
        <button
          key={i}
          type="button"
          aria-label={`hour ${i}`}
          onClick={() => onFocus(i)}
          className={cn(
            "h-full min-w-0 flex-1",
            i === focus ? "opacity-100" : "opacity-50 hover:opacity-80",
            flags[i] === "over" && "bg-over",
            flags[i] === "under" && "bg-under",
            flags[i] === "ramp" && "bg-ramp",
            flags[i] === "ok" && "bg-bg-subtle",
          )}
        />
      ))}
    </div>
  );
}

function Actions({
  events,
  focus,
  onFocus,
}: {
  events: ReturnType<typeof computeBoard>["events"];
  focus: number;
  onFocus: (i: number) => void;
}) {
  return (
    <aside className="rounded-lg border border-border bg-bg-elevated p-3 lg:row-span-2 lg:row-start-2">
      <h2 className="text-xs tracking-[0.16em] text-subtle uppercase">Actions</h2>
      <ul className="mt-3 flex flex-col gap-1.5">
        {events.length === 0 && (
          <li className="font-mono text-sm text-muted">HOLD</li>
        )}
        {events.slice(0, 8).map((e) => {
          const active = focus >= e.start && focus <= e.end;
          return (
            <li key={e.id}>
              <button
                type="button"
                onClick={() => onFocus(e.start)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-sm px-2 py-2 text-left transition-colors duration-(--motion-quick)",
                  active ? "bg-bg-subtle" : "hover:bg-bg-subtle/60",
                )}
              >
                <span className={cn("h-8 w-0.5 rounded-full", flagBg(e.type))} />
                <span className="min-w-0 flex-1">
                  <span className={cn("block font-mono text-sm tracking-wide", actionClass(e.action))}>
                    {ACTION_LABEL[e.action]}
                  </span>
                  <span className="block font-mono text-[10px] text-subtle tabular-nums">
                    +{e.start}–{e.end}h · {e.hours}h
                  </span>
                </span>
                <span className="text-right">
                  <span className="block font-mono text-sm tabular-nums">{fmtMw(e.mw, 0)}</span>
                  <span className="block font-mono text-[10px] text-subtle tabular-nums">
                    {(e.confidence * 100).toFixed(0)}%
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

function Heatmap({
  points,
  focus,
  onFocus,
}: {
  points: ReturnType<typeof computeBoard>["points"];
  focus: number;
  onFocus: (i: number) => void;
}) {
  const rows = [0, 1, 2]
    .map((r) => points.filter((p) => Math.floor(p.i / 24) === r))
    .filter((row) => row.length > 0);
  return (
    <section className="rounded-lg border border-border bg-bg-elevated p-3">
      <h2 className="mb-2 text-xs tracking-[0.16em] text-subtle uppercase">Balance</h2>
      <div className="flex flex-col gap-1">
        {rows.map((row, r) => (
          <div key={r} className="flex items-center gap-2">
            <span className="w-8 shrink-0 font-mono text-[10px] text-subtle tabular-nums">+{r * 24}h</span>
            <div className="grid min-w-0 flex-1 grid-cols-24 gap-px" style={{ gridTemplateColumns: "repeat(24, minmax(0, 1fr))" }}>
              {Array.from({ length: 24 }).map((_, h) => {
                const p = row[h];
                if (!p) return <span key={h} className="h-7 rounded-[2px] bg-bg" />;
                return (
                  <button
                    key={h}
                    type="button"
                    onClick={() => onFocus(p.i)}
                    title={`${FLAG_LABEL[p.flag]} +${p.i}h`}
                    className={cn(
                      "h-7 rounded-[2px] transition-opacity duration-(--motion-quick)",
                      p.flag === "over" && "bg-over",
                      p.flag === "under" && "bg-under",
                      p.flag === "ramp" && "bg-ramp",
                      p.flag === "ok" && "bg-bg-subtle",
                      focus === p.i ? "ring-1 ring-fg opacity-100" : "opacity-80 hover:opacity-100",
                    )}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Fleet({
  plants,
  selected,
  onSelect,
}: {
  plants: ReturnType<typeof computeBoard>["plants"];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-bg-elevated p-3 lg:col-span-2">
      <h2 className="mb-2 text-xs tracking-[0.16em] text-subtle uppercase">Fleet</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        {plants.map((p) => {
          const active = selected === p.site.site_id;
          return (
            <button
              key={p.site.site_id}
              type="button"
              onClick={() => onSelect(p.site.site_id)}
              className={cn(
                "rounded-md border px-2 py-2 text-left transition-colors duration-(--motion-quick)",
                active ? "border-fg bg-bg-subtle" : "border-border hover:border-border-strong",
                p.dirty && "border-accent/50",
              )}
            >
              <p className="truncate font-mono text-[10px] tracking-wide text-muted uppercase">
                {p.site.tech === "solar" ? "PV" : "WD"} · {p.site.name.split(" ")[0]}
              </p>
              <p className="mt-1 font-mono text-lg tabular-nums">{(p.cf * 100).toFixed(0)}%</p>
              <div className="mt-2 h-1 rounded-full bg-bg">
                <div
                  className={cn("h-1 rounded-full", p.site.tech === "solar" ? "bg-solar" : "bg-wind")}
                  style={{ width: `${Math.round(clip01(p.cf) * 100)}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function clip01(n: number) {
  return Math.min(1, Math.max(0, n));
}

function SitePanel({
  site,
  plant,
  orig,
  hours,
  onPatch,
  onReset,
}: {
  site: SiteParams | null;
  plant: ReturnType<typeof computeBoard>["plants"][number] | null;
  orig: SiteParams | undefined;
  hours: string[];
  onPatch: (id: string, p: Partial<SiteParams>) => void;
  onReset: (id: string) => void;
}) {
  if (!site || !plant) {
    return (
      <section className="rounded-lg border border-dashed border-border bg-bg-elevated p-3 lg:col-span-2">
        <h2 className="text-xs tracking-[0.16em] text-subtle uppercase">Site</h2>
        <p className="mt-6 font-mono text-sm text-subtle">Select a plant</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-bg-elevated p-3 lg:col-span-2">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="truncate text-xs tracking-[0.16em] text-subtle uppercase">{site.name}</h2>
        <button
          type="button"
          onClick={() => onReset(site.site_id)}
          className="h-7 rounded-sm px-2 font-mono text-xs tracking-wide text-muted uppercase hover:text-fg"
        >
          Reset
        </button>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <Spark q10={plant.q10} q50={plant.q50} q90={plant.q90} tech={site.tech} />
          <p className="mt-1 font-mono text-xs text-subtle tabular-nums">
            {fmtMw(plant.q50[0] ?? 0, 0)}–{fmtMw(plant.q50[plant.q50.length - 1] ?? 0, 0)} MW · {hours.length}h
          </p>
        </div>
        <div className="flex flex-col gap-3">
        {site.tech === "solar" && (
          <>
            <Range
              label="Tilt"
              value={site.tilt_deg ?? 25}
              min={5}
              max={50}
              step={1}
              unit="°"
              onChange={(v) => onPatch(site.site_id, { tilt_deg: v })}
            />
            <Range
              label="Azimuth"
              value={site.azimuth_deg ?? 180}
              min={90}
              max={270}
              step={5}
              unit="°"
              onChange={(v) => onPatch(site.site_id, { azimuth_deg: v })}
            />
            <Range
              label="DC/AC"
              value={site.dc_ac_ratio ?? 1.25}
              min={1}
              max={1.55}
              step={0.01}
              unit=""
              digits={2}
              onChange={(v) => onPatch(site.site_id, { dc_ac_ratio: v })}
            />
          </>
        )}
        {site.tech === "wind" && (
          <Range
            label="Hub"
            value={site.hub_height_m ?? 80}
            min={60}
            max={140}
            step={1}
            unit="m"
            onChange={(v) => onPatch(site.site_id, { hub_height_m: v })}
          />
        )}
          <Range
            label="Storage"
            value={site.storage_mwh}
            min={0}
            max={site.tech === "wind" ? 250 : 200}
            step={5}
            unit=" MWh"
            onChange={(v) => onPatch(site.site_id, { storage_mwh: v })}
          />
        </div>
      </div>
      {orig && plant.dirty && (
        <p className="mt-3 font-mono text-xs text-accent">Δ vs nameplate</p>
      )}
    </section>
  );
}

function Range({
  label,
  value,
  min,
  max,
  step,
  unit,
  digits = 0,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  digits?: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="grid grid-cols-[4.25rem_minmax(0,1fr)_3.5rem] items-center gap-3">
      <span className="font-mono text-[10px] tracking-[0.14em] text-muted uppercase">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="text-right font-mono text-xs tabular-nums">
        {value.toFixed(digits)}
        {unit}
      </span>
    </label>
  );
}

function Spark({
  q10,
  q50,
  q90,
  tech,
}: {
  q10: number[];
  q50: number[];
  q90: number[];
  tech: "solar" | "wind";
}) {
  const w = 320;
  const h = 56;
  const n = q50.length;
  const ymax = Math.max(...q90, 1);
  const x = (i: number) => (i / Math.max(n - 1, 1)) * w;
  const y = (v: number) => h - (v / ymax) * (h - 4) - 2;
  const line = q50.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const band =
    q90.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ") +
    " " +
    [...q10]
      .reverse()
      .map((v, i) => `L${x(n - 1 - i).toFixed(1)},${y(v).toFixed(1)}`)
      .join(" ") +
    " Z";
  const stroke = tech === "solar" ? "var(--color-solar)" : "var(--color-wind)";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-14 w-full" aria-hidden>
      <path d={band} fill="var(--color-fg)" opacity={0.12} />
      <path d={line} fill="none" stroke={stroke} strokeWidth={1.6} />
    </svg>
  );
}
