#!/usr/bin/env python3
"""
Weather fetcher for locally configured sites — official KTTV observations only.

Uses the official KTTV API (kttv_client.py). Based on current development
testing, live access requires a Vietnam egress IP. If access is unavailable,
the program reports a per-site error rather than substituting another source.

Usage:
    python fetch_weather.py [--sites-file FILE] [--site NAME|all] [--json]
                            [--dedup [--state FILE]]

Dedup mode (for cron): with --dedup, a site is only emitted when its data
timestamp (KTTV `valid_time`) differs from the last one recorded in the state
file (default: private/kttv_state.json next to this script). This lets you poll more
often than the ~10-min update cadence without writing duplicate rows — key your
storage on `time`, not on fetch time.
Exit codes: 0 = all requested sites succeeded; 1 = at least one site errored.
In --dedup mode the exit code is unchanged; unchanged-but-successful sites are
simply omitted from output (not treated as errors).
"""

import argparse
import json
import os
import sys

import kttv_client

DEFAULT_SITES_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "private", "sites.json"
)


def load_sites(path):
    """Load named latitude/longitude pairs from a local JSON file."""
    with open(path, encoding="utf-8") as f:
        raw_sites = json.load(f)

    if not isinstance(raw_sites, dict) or not raw_sites:
        raise ValueError("site configuration must be a non-empty JSON object")

    sites = {}
    for name, location in raw_sites.items():
        if not isinstance(name, str) or not name:
            raise ValueError("each site name must be a non-empty string")
        if not isinstance(location, dict):
            raise ValueError(f"site {name!r} must contain a JSON object")
        lat = location.get("lat")
        lon = location.get("lon")
        if (
            not isinstance(lat, (int, float))
            or isinstance(lat, bool)
            or not isinstance(lon, (int, float))
            or isinstance(lon, bool)
        ):
            raise ValueError(f"site {name!r} must contain numeric lat and lon values")
        sites[name] = (lat, lon)
    return sites


def _pick(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return None


def _normalize_kttv(raw):
    # KTTV realtime schema:
    #   {"data": [ { "valid_time","t2m","2r","rain","wind_speed","wind_dir",
    #                "total_cloud","cloud_text","wind_text","pmsl","icon",
    #                "nguycoluquet","nguycosatlo","giongset" } ],
    #    "success": true, "message": "..."}
    # `data` is a LIST (take the first/most-recent record).
    # wind_speed is in m/s and is kept as-is.
    if not isinstance(raw, dict) or raw.get("success") is False:
        raise ValueError("no usable realtime data")
    rows = raw.get("data")
    row = rows[0] if isinstance(rows, list) and rows else (rows if isinstance(rows, dict) else {})
    if not isinstance(row, dict) or not row:
        raise ValueError("no usable realtime data")
    normalized = {
        "time": _pick(row, ["valid_time", "time", "observed_at", "timestamp"]),
        "temperature_c": _pick(row, ["t2m", "temperature", "temp"]),
        "humidity_pct": _pick(row, ["2r", "humidity", "rh"]),
        "precipitation_mm": _pick(row, ["rain", "precipitation"]),
        "wind_speed_ms": _pick(row, ["wind_speed", "windspeed"]),
        "wind_dir_deg": _pick(row, ["wind_dir", "wind_direction"]),
        "wind_text": _pick(row, ["wind_text"]),
        "pressure_hpa": _pick(row, ["pmsl", "pressure"]),
        "cloud_pct": _pick(row, ["total_cloud"]),
        "cloud_text": _pick(row, ["cloud_text"]),
        "flash_flood_risk": row.get("nguycoluquet"),
        "landslide_risk": row.get("nguycosatlo"),
        "thunderstorm": row.get("giongset"),
    }
    if normalized["time"] is None:
        raise ValueError("no usable realtime data")
    return normalized


def fetch_site(name, lat, lon):
    """Fetch one site's official KTTV weather. Never raises; returns a result
    dict with source='error' and an 'error' message if the KTTV call fails."""
    result = {"site": name}
    try:
        client = kttv_client.KTTVClient()
        realtime = client.get_realtime(lat, lon)
        result.update(_normalize_kttv(realtime))
        result["source"] = "kttv"
        return result
    except (
        kttv_client.KTTVConfigurationError,
        kttv_client.KTTVNetworkError,
        kttv_client.KTTVError,
        ValueError,
    ) as e:
        result["source"] = "error"
        result["error"] = f"KTTV failed: {e}"
        return result
    except Exception:  # defensive: never let one site crash the run
        result["source"] = "error"
        result["error"] = "KTTV failed unexpectedly"
        return result


def _fmt(v, unit=""):
    return "n/a" if v is None else f"{v}{unit}"


def print_human(result):
    print(f"=== {result['site']} ===")
    if result["source"] == "error":
        print(f"  ERROR: {result['error']}")
        print()
        return
    print(f"  Source     : {result['source']}")
    print(f"  Time       : {_fmt(result.get('time'))}")
    print(f"  Temp       : {_fmt(result.get('temperature_c'), ' °C')}")
    print(f"  Humidity   : {_fmt(result.get('humidity_pct'), ' %')}")
    print(f"  Precip     : {_fmt(result.get('precipitation_mm'), ' mm')}")
    wind = _fmt(result.get("wind_speed_ms"), " m/s")
    wind_dir = _fmt(result.get("wind_dir_deg"), "°")
    wind_txt = result.get("wind_text")
    print(f"  Wind       : {wind} @ {wind_dir}" + (f" ({wind_txt})" if wind_txt else ""))
    if result.get("pressure_hpa") is not None:
        print(f"  Pressure   : {_fmt(result.get('pressure_hpa'), ' hPa')}")
    if result.get("cloud_pct") is not None:
        ctxt = result.get("cloud_text")
        print(f"  Cloud      : {_fmt(result.get('cloud_pct'), ' %')}" + (f" ({ctxt})" if ctxt else ""))
    # KTTV risk flags: -1/None means no warning; surface only when active (>=0 / truthy).
    if isinstance(result.get("flash_flood_risk"), (int, float)) and result["flash_flood_risk"] >= 0:
        print(f"  Flash-flood risk : {result['flash_flood_risk']}")
    if isinstance(result.get("landslide_risk"), (int, float)) and result["landslide_risk"] >= 0:
        print(f"  Landslide risk   : {result['landslide_risk']}")
    print()


DEFAULT_STATE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "private", "kttv_state.json"
)


def _load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _save_state(path, state):
    # Atomic write so a crash mid-write can't corrupt the state file.
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sites-file",
        default=DEFAULT_SITES_FILE,
        help="local JSON site configuration (default: private/sites.json beside the script)",
    )
    parser.add_argument(
        "--site",
        default="all",
        metavar="NAME",
        help="site name from --sites-file, or all (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument("--dedup", action="store_true",
                        help="only emit a site when its data timestamp changed since last run")
    parser.add_argument("--state", default=DEFAULT_STATE,
                        help="state file for --dedup (default: private/kttv_state.json beside the script)")
    args = parser.parse_args(argv)

    try:
        sites = load_sites(args.sites_file)
    except (OSError, ValueError) as e:
        parser.error(f"could not load --sites-file: {e}")

    if args.site == "all":
        names = list(sites)
    elif args.site in sites:
        names = [args.site]
    else:
        parser.error(f"unknown site {args.site!r} in --sites-file")
    results = [fetch_site(name, *sites[name]) for name in names]

    emitted = results
    if args.dedup:
        state = _load_state(args.state)
        fresh = []
        for r in results:
            # Errors are never "fresh"; they also must not overwrite a good timestamp.
            if r.get("source") == "error":
                continue
            ts = r.get("time")
            if ts is not None and state.get(r["site"]) != ts:
                fresh.append(r)
                state[r["site"]] = ts
        _save_state(args.state, state)
        emitted = fresh

    if args.json:
        print(json.dumps(emitted, ensure_ascii=False, indent=2))
    else:
        for r in emitted:
            print_human(r)
        if args.dedup and not emitted:
            print("(no sites with new data since last run)")

    return 1 if any(r["source"] == "error" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
