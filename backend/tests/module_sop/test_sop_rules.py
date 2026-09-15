import unittest

from app.modules.sop.domain.rules import validate_forecast


class ForecastRuleTests(unittest.TestCase):
    def test_missing_forecast_is_not_evaluable(self):
        result = validate_forecast(None, [100, 110, 120])

        self.assertFalse(result["evaluable"])
        self.assertIsNone(result["score"])
        self.assertEqual(result["findings"][0]["code"], "FORECAST_MISSING_OR_INVALID")

    def test_insufficient_history_is_not_silently_scored(self):
        result = validate_forecast(120, [100, 110])

        self.assertFalse(result["evaluable"])
        self.assertEqual(result["findings"][0]["code"], "INSUFFICIENT_HISTORY")

    def test_large_deviation_is_flagged_deterministically(self):
        first = validate_forecast(200, [100, 110, 120])
        second = validate_forecast(200, [100, 110, 120])

        self.assertEqual(first, second)
        self.assertTrue(first["evaluable"])
        self.assertIn("FORECAST_DEVIATION_HIGH", {item["code"] for item in first["findings"]})
        self.assertEqual(first["rule_version"], "forecast-check.v0.1-draft")


if __name__ == "__main__":
    unittest.main()
