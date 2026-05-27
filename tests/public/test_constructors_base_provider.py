import unittest
from pathlib import PurePath
from typing import override

from src.the_downloader.provider import BaseProvider
from src.the_downloader.types.protocol import CheckCanceled, UpdateProgress


class ExampleProvider(BaseProvider):
    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        return None


class BaseProviderConstructorTests(unittest.TestCase):
    def test_base_provider_exposes_shared_settings_as_readonly_properties(self) -> None:
        provider = ExampleProvider(
            chunk_size=123,
            timeout=45,
            ca_cert_path="cert.pem",
        )

        self.assertEqual(provider.chunk_size, 123)
        self.assertEqual(provider.timeout, 45)
        self.assertEqual(provider.ca_cert_path, "cert.pem")

        with self.assertRaises(AttributeError):
            setattr(provider, "chunk_size", 999)


if __name__ == "__main__":
    unittest.main()
