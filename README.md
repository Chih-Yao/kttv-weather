[繁體中文](README.zh-TW.md) | English

# KTTV Weather Client

A lightweight, Python-standard-library utility for retrieving weather data from
the KTTV service. This repository intentionally contains no project-specific
locations, credentials, deployment settings, or operational data.

## Features

- Retrieves real-time observations, forecasts, and location information.
- Provides batch fetching, JSON output, and optional duplicate suppression for
  scheduled jobs.
- Keeps locations in a local configuration file and credentials in local
  environment variables.
- Uses no third-party Python packages.

## Requirements

- Python 3.9 or later.
- `rsync` and SSH only when using the deployment helper.

## Local configuration

Create a private site configuration, then replace the placeholder values with
your own local site labels and coordinates:

```bash
mkdir -p private
cp sites.example.json private/sites.json
```

Set the service credentials in the environment where the client runs:

```bash
export KTTV_API_KEY='your-local-value'
export KTTV_SECRET_KEY='your-local-value'
```

`private/`, environment files, state files, logs, and local operational
notes are ignored by Git. Do not commit their contents.

## Quick start

Run the offline signing check:

```bash
python3 kttv_client.py selftest
```

Fetch all sites from the local configuration:

```bash
python3 fetch_weather.py
```

Fetch one locally named site, request JSON, or suppress unchanged scheduled
results:

```bash
python3 fetch_weather.py --site site-a
python3 fetch_weather.py --json
python3 fetch_weather.py --json --dedup
```

Use another local configuration path when needed:

```bash
python3 fetch_weather.py --sites-file private/another-sites.json
```

The batch command accepts `--site NAME|all`, `--json`, `--dedup`, and
`--state FILE`. Its default state file is `private/kttv_state.json` beside the
script. Put a custom state file under `private/` or outside the repository.

For a direct one-off request, use the client with values supplied locally:

```bash
python3 kttv_client.py realtime <latitude> <longitude>
python3 kttv_client.py forecast <latitude> <longitude>
python3 kttv_client.py dayforecast <latitude> <longitude>
python3 kttv_client.py location <latitude> <longitude>
python3 kttv_client.py search <keyword>
```

## Network note

Live requests are subject to upstream network access controls. Based on current
development testing, run them through a Vietnam egress IP and verify
connectivity in the target environment.

## Deployment

Preview a deployment without copying files:

```bash
./deploy.sh user@host:/target/path
```

Append `--go` to perform the copy:

```bash
./deploy.sh user@host:/target/path --go
```

The helper deliberately excludes local site configuration, environment files,
state, logs, and private operational notes. Provision those separately on the
trusted target.

## Repository layout

| File | Purpose |
| --- | --- |
| `kttv_client.py` | Credential-aware KTTV client and offline signing self-test. |
| `fetch_weather.py` | Batch fetcher for sites defined in a local file. |
| `sites.example.json` | Anonymous local-configuration template. |
| `deploy.sh` | Optional rsync deployment helper. |
| `tests/` | Standard-library regression tests. |
