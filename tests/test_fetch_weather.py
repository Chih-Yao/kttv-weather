import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetch_weather
import kttv_client


class LoadSitesTests(unittest.TestCase):
    def test_load_sites_reads_named_coordinates_from_local_json(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "sites.json"
            config_path.write_text(
                json.dumps({"site-a": {"lat": 1.25, "lon": 2.5}}),
                encoding="utf-8",
            )

            self.assertEqual(
                fetch_weather.load_sites(config_path),
                {"site-a": (1.25, 2.5)},
            )


class ClientCredentialsTests(unittest.TestCase):
    def test_client_uses_injected_credentials_for_offline_signing(self):
        with patch.object(kttv_client.time, "time", return_value=1700000000.0):
            client = kttv_client.KTTVClient(
                api_key="test-client",
                secret_key="test-secret",
            )
            signature, timestamp = client._sign(
                "GET", "/api/mobile_app_data/get_data_realtime/0/0"
            )

        self.assertEqual(timestamp, "1700000000")
        self.assertEqual(len(signature), 64)
        self.assertEqual(
            client._headers("GET", "/example")["X-Api-Key"],
            "test-client",
        )

    def test_http_error_message_does_not_echo_response_body(self):
        error = kttv_client.KTTVError(400, "private-response-body")

        self.assertEqual(str(error), "KTTV API returned HTTP 400")

    @patch(
        "kttv_client.urllib.request.urlopen",
        side_effect=kttv_client.urllib.error.URLError("internal-proxy.example"),
    )
    def test_network_error_does_not_echo_network_reason(self, _):
        client = kttv_client.KTTVClient(
            api_key="test-client",
            secret_key="test-secret",
        )

        with self.assertRaises(kttv_client.KTTVNetworkError) as raised:
            client.get_realtime(0, 0)

        self.assertEqual(
            str(raised.exception),
            "Could not reach the KTTV service. Based on current development "
            "testing, live access requires a Vietnam egress IP.",
        )


class FetchSitePrivacyTests(unittest.TestCase):
    @patch("fetch_weather.kttv_client.KTTVClient")
    def test_fetch_site_does_not_return_coordinates(self, client_class):
        client = client_class.return_value
        client.get_realtime.return_value = {"data": [{"valid_time": "now"}]}
        client.get_forecast.return_value = {"data": []}

        result = fetch_weather.fetch_site("site-a", 1.25, 2.5)

        self.assertEqual(result["site"], "site-a")
        self.assertNotIn("lat", result)
        self.assertNotIn("lon", result)
        self.assertNotIn("raw", result)
        self.assertNotIn("forecast_raw", result)

    @patch("fetch_weather.kttv_client.KTTVClient")
    def test_fetch_site_marks_unsuccessful_payload_as_error(self, client_class):
        client_class.return_value.get_realtime.return_value = {
            "success": False,
            "data": [],
        }

        result = fetch_weather.fetch_site("site-a", 1.25, 2.5)

        self.assertEqual(result["source"], "error")
        self.assertEqual(result["error"], "KTTV failed: no usable realtime data")

    @patch("fetch_weather.kttv_client.KTTVClient", side_effect=RuntimeError("private"))
    def test_fetch_site_does_not_echo_unexpected_error_details(self, _):
        result = fetch_weather.fetch_site("site-a", 1.25, 2.5)

        self.assertEqual(result["error"], "KTTV failed unexpectedly")


if __name__ == "__main__":
    unittest.main()
