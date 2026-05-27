import unittest

from src.the_downloader.utils.retry import retry


class RetryTests(unittest.TestCase):
    def test_retry_result_marks_first_attempt_success_as_succeeded(self) -> None:
        @retry(max_retries=3, delay=0)
        def succeeds() -> str:
            return "ok"

        result = succeeds()

        self.assertEqual(result.result, "ok")
        self.assertEqual(result.exceptions, [])
        self.assertTrue(result.succeeded)
        self.assertEqual(result.attempts, 1)

    def test_retry_result_marks_eventual_success_as_succeeded(self) -> None:
        attempts = 0

        @retry(max_retries=3, delay=0)
        def succeeds_after_retries() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("not yet")
            return "ok"

        result = succeeds_after_retries()

        self.assertEqual(result.result, "ok")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(len(result.exceptions), 2)
        self.assertTrue(all(isinstance(e, RuntimeError) for e in result.exceptions))

    def test_retry_result_marks_exhausted_retries_as_failed(self) -> None:
        @retry(max_retries=2, delay=0)
        def always_fails() -> str:
            raise ValueError("nope")

        result = always_fails()

        self.assertIsNone(result.result)
        self.assertFalse(result.succeeded)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(len(result.exceptions), 3)
        self.assertTrue(all(isinstance(e, ValueError) for e in result.exceptions))


if __name__ == "__main__":
    unittest.main()
