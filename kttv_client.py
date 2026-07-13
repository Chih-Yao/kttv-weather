#!/usr/bin/env python3
"""KTTV weather API client.

Credentials are supplied locally through the ``KTTV_API_KEY`` and
``KTTV_SECRET_KEY`` environment variables; this repository contains no
credential values or project-specific locations.

Based on current development testing, live requests require a Vietnam egress
IP. Verify connectivity from the environment where the client will run.

Usage:
    python kttv_client.py realtime <latitude> <longitude>
    python kttv_client.py forecast <latitude> <longitude>
    python kttv_client.py dayforecast <latitude> <longitude>
    python kttv_client.py location <latitude> <longitude>
    python kttv_client.py search <keyword>
    python kttv_client.py selftest
"""

import hashlib
import hmac
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://m.thoitietnguyhiem.gov.vn"
TIMEOUT = 10
API_KEY_ENV = "KTTV_API_KEY"
SECRET_KEY_ENV = "KTTV_SECRET_KEY"
USER_AGENT = "okhttp/4.9.2"


def _primary_sign(method, url, data, timestamp):
    return f"{method}|{url}|{data}|{timestamp}"


class KTTVConfigurationError(Exception):
    """Required local client configuration is missing."""


class KTTVError(Exception):
    """Non-2xx HTTP response from the API (carries status + body)."""

    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__(f"KTTV API returned HTTP {status}")


class KTTVNetworkError(Exception):
    """Connection refused or timed out while calling KTTV."""


class KTTVClient:
    def __init__(
        self,
        base_url=BASE_URL,
        timeout=TIMEOUT,
        sign_fn=_primary_sign,
        api_key=None,
        secret_key=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.sign_fn = sign_fn
        self.api_key = api_key or os.environ.get(API_KEY_ENV)
        self.secret_key = secret_key or os.environ.get(SECRET_KEY_ENV)
        if not self.api_key or not self.secret_key:
            raise KTTVConfigurationError(
                f"set {API_KEY_ENV} and {SECRET_KEY_ENV} in the local environment"
            )
        self._ssl_ctx = ssl.create_default_context()

    def _sign(self, method, url, data=""):
        now = time.time()
        timestamp = str(int(now))
        sign_string = self.sign_fn(method.upper(), url, data, timestamp)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature, timestamp

    def _headers(self, method, url, data=""):
        signature, timestamp = self._sign(method, url, data)
        return {
            "X-Api-Key": self.api_key,
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    def _request(self, method, url, body=None):
        data_str = "" if body is None else json.dumps(body, separators=(",", ":"))
        headers = self._headers(method, url, data_str)
        payload = data_str.encode("utf-8") if body is not None else None
        req = urllib.request.Request(
            self.base_url + url,
            data=payload,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(
                req, timeout=self.timeout, context=self._ssl_ctx
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return self._parse(response.status, raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise KTTVError(e.code, raw) from e
        except urllib.error.URLError as e:
            raise KTTVNetworkError(
                "Could not reach the KTTV service. Based on current development testing, live access "
                "requires a Vietnam egress IP."
            ) from e
        except (TimeoutError, ssl.SSLError) as e:
            raise KTTVNetworkError(
                "Could not reach the KTTV service. Based on current development "
                "testing, live access requires a Vietnam egress IP."
            ) from e

    @staticmethod
    def _parse(status, raw):
        if status != 200:
            raise KTTVError(status, raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise KTTVError(status, f"non-JSON body: {raw[:500]} ({e})") from e

    def get_realtime(self, lat, lon):
        return self._request(
            "GET", f"/api/mobile_app_data/get_data_realtime/{lat}/{lon}"
        )

    def get_forecast(self, lat, lon):
        return self._request(
            "GET", f"/api/mobile_app_data/get_data_forecast/{lat}/{lon}"
        )

    def get_day_forecast(self, lat, lon):
        return self._request(
            "GET", f"/api/mobile_app_data/get_day_forecast/{lat}/{lon}"
        )

    def get_location(self, lat, lon):
        return self._request(
            "GET", f"/api/mobile_app_location/get_location/{lat}/{lon}"
        )

    def search_location(self, keyword):
        segment = urllib.parse.quote(str(keyword), safe="")
        return self._request("GET", f"/api/mobile_app_location/search_location/{segment}")


def _selftest():
    fixed = 1700000000.0
    real_time = time.time
    time.time = lambda: fixed
    try:
        client = KTTVClient(api_key="test-client", secret_key="test-secret")
        signature, timestamp = client._sign(
            "GET", "/api/mobile_app_data/get_data_realtime/0/0"
        )
    finally:
        time.time = real_time

    expected_string = "GET|/api/mobile_app_data/get_data_realtime/0/0||1700000000"
    expected_signature = hmac.new(
        b"test-secret", expected_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    assert timestamp == "1700000000", f"timestamp mismatch: {timestamp!r}"
    assert signature == expected_signature, "signature computation drifted"
    print("selftest OK")
    return True


def _print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv):
    if not argv:
        print(__doc__)
        return 2

    command = argv[0]
    if command == "selftest":
        return 0 if _selftest() else 1
    if command not in {"realtime", "forecast", "dayforecast", "location", "search"}:
        print(f"unknown command: {command}")
        print(__doc__)
        return 2

    try:
        client = KTTVClient()
        if command == "realtime":
            _print_json(client.get_realtime(argv[1], argv[2]))
        elif command == "forecast":
            _print_json(client.get_forecast(argv[1], argv[2]))
        elif command == "dayforecast":
            _print_json(client.get_day_forecast(argv[1], argv[2]))
        elif command == "location":
            _print_json(client.get_location(argv[1], argv[2]))
        else:
            _print_json(client.search_location(argv[1]))
        return 0
    except KTTVConfigurationError as e:
        print(f"CONFIGURATION ERROR: {e}", file=sys.stderr)
        return 2
    except KTTVNetworkError as e:
        print(f"NETWORK ERROR: {e}", file=sys.stderr)
        return 3
    except KTTVError as e:
        print(f"API ERROR (HTTP {e.status})", file=sys.stderr)
        return 4
    except IndexError:
        print("missing arguments; see usage below\n", file=sys.stderr)
        print(__doc__)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
