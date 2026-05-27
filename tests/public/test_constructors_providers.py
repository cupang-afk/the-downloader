import unittest
from pathlib import Path
from unittest.mock import patch

from src.the_downloader.provider import (
    Aria2Provider,
    CurlProvider,
    RequestsProvider,
    WgetProvider,
)


class ProviderConstructorTests(unittest.TestCase):
    def test_requests_provider_accepts_shared_provider_settings(self) -> None:
        provider = RequestsProvider(
            chunk_size=123,
            timeout=45,
            ca_cert_path="cert.pem",
        )

        self.assertEqual(provider.chunk_size, 123)
        self.assertEqual(provider.timeout, 45)
        self.assertEqual(provider.ca_cert_path, "cert.pem")

    def test_aria2_provider_accepts_binary_path_then_shared_settings(self) -> None:
        with patch(
            "src.the_downloader.provider.aria2.resolve_binary",
            return_value=Path("aria2c"),
        ) as resolve_binary:
            provider = Aria2Provider(
                "custom-aria2c",
                chunk_size=123,
                timeout=45,
                ca_cert_path="cert.pem",
            )

        resolve_binary.assert_called_once_with("custom-aria2c")
        self.assertEqual(provider.bin, Path("aria2c"))
        self.assertEqual(provider.chunk_size, 123)
        self.assertEqual(provider.timeout, 45)
        self.assertEqual(provider.ca_cert_path, "cert.pem")

    def test_curl_provider_accepts_binary_path_then_shared_settings(self) -> None:
        with patch(
            "src.the_downloader.provider.curl.resolve_binary",
            return_value=Path("curl"),
        ) as resolve_binary:
            provider = CurlProvider(
                "custom-curl",
                chunk_size=123,
                timeout=45,
                ca_cert_path="cert.pem",
            )

        resolve_binary.assert_called_once_with("custom-curl")
        self.assertEqual(provider.bin, Path("curl"))
        self.assertEqual(provider.chunk_size, 123)
        self.assertEqual(provider.timeout, 45)
        self.assertEqual(provider.ca_cert_path, "cert.pem")

    def test_wget_provider_accepts_binary_path_then_shared_settings(self) -> None:
        with patch(
            "src.the_downloader.provider.wget.resolve_binary",
            return_value=Path("wget"),
        ) as resolve_binary:
            provider = WgetProvider(
                "custom-wget",
                chunk_size=123,
                timeout=45,
                ca_cert_path="cert.pem",
            )

        resolve_binary.assert_called_once_with("custom-wget")
        self.assertEqual(provider.bin, Path("wget"))
        self.assertEqual(provider.chunk_size, 123)
        self.assertEqual(provider.timeout, 45)
        self.assertEqual(provider.ca_cert_path, "cert.pem")


if __name__ == "__main__":
    unittest.main()
