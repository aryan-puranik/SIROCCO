# Sirocco joined dataset

Eight real US plants (CAISO + ERCOT). Two years hourly. Live 72-hour forecast.

## Join key

`site_id` + `timestamp_utc`  (plants)  
`ba_code` + `timestamp_utc`  (grid)

## Tables

| File | Grain | Role |
|---|---|---|
| sites.csv | plant | Static parameters (S) |
| weather_hourly.csv.gz | site × hour | NASA POWER MERRA-2 (W) |
| generation_hourly.csv.gz | site × hour | Physics MW (Y) |
| ba_hourly.csv.gz | BA × hour | Demand + net load (D) |
| panel_hourly.csv.gz | site × hour | Full join used by the dashboard |
| model_train_h{24,48,72}.csv.gz | issue × horizon | Train matrix φ(x) → y_mw |
| forecast_72h.csv | site × future hour | MET Norway NWP → q10/q50/q90 |

## Model contract

**Input** `φ(x)`: NWP weather at t+h, lags of Y at issue time, site params, calendar, physics baseline  
**Output**: `y_mw` at t+h (plus q10/q50/q90 at inference)

Over/under is **not** a model output. It is `net_load = demand − renewable` after the forecast.

## Sources this build

- Sites: WRI GPPD / EIA-860 identities
- Historical weather: NASA POWER hourly (Open-Meteo was rate-limited)
- Live forecast: MET Norway Locationforecast 2.0
- Generation: isotropic POA + PV clip; IEC Class II wind curve
- Demand: temperature-calibrated typical CAISO/ERCOT load (EIA-930 was 503)
