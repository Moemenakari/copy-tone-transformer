"""Tests with a fake async client, so no API key is needed.

Run with:  python -m unittest test_copywriter.py
"""

import asyncio
import json
import unittest

from copywriter import expand_platforms, measure, parse_args, resolve_settings, run_batch
from models import CopyRequest, MarketingCopy
from prompts import build_prompt


class FakeAsyncModels:
    def __init__(self, fail_platform=None):
        self.calls = []
        self.fail_platform = fail_platform

    async def generate_content(self, model, contents, config):
        self.calls.append({"prompt": contents, "temperature": config.temperature, "top_p": config.top_p})
        if self.fail_platform and f"PLATFORM: {self.fail_platform}" in contents:
            raise RuntimeError("simulated API error")
        data = {"headline": "Stay cold", "body": "Great bottle.", "call_to_action": "Buy now",
                "hashtags": ["#eco"], "subject_line": None}
        return type("R", (), {"text": json.dumps(data)})()


class FakeClient:
    def __init__(self, fail_platform=None):
        self.aio = type("A", (), {})()
        self.aio.models = FakeAsyncModels(fail_platform)


def make_request(platform="linkedin", tone="witty"):
    return CopyRequest(product_name="EcoBottle", description="Steel bottle, cold for 24h",
                       platform=platform, tone=tone)


class TestTemplate(unittest.TestCase):
    def test_variables_are_injected(self):
        prompt = build_prompt(make_request("instagram", "luxury"))
        self.assertIn("PRODUCT: EcoBottle", prompt)
        self.assertIn("PLATFORM: Instagram", prompt)
        self.assertIn("TONE: luxury", prompt)
        self.assertIn("2200", prompt)

    def test_email_asks_for_subject(self):
        self.assertIn("subject_line", build_prompt(make_request("email")))
        self.assertNotIn("subject_line", build_prompt(make_request("linkedin")))


class TestSettings(unittest.TestCase):
    def test_tone_defaults(self):
        self.assertEqual(resolve_settings("professional"), (0.3, 0.8))
        self.assertEqual(resolve_settings("witty"), (0.9, 0.95))

    def test_override_and_validation(self):
        self.assertEqual(resolve_settings("witty", 0.2, 0.5), (0.2, 0.5))
        with self.assertRaises(ValueError):
            resolve_settings("witty", temperature=3.0)
        with self.assertRaises(ValueError):
            resolve_settings("witty", top_p=0)

    def test_platform_list(self):
        self.assertEqual(expand_platforms("all"), ["linkedin", "instagram", "email"])
        self.assertEqual(expand_platforms("LinkedIn, twitter"), ["linkedin", "twitter"])

    def test_cli_rejects_unknown_platform(self):
        with self.assertRaises(SystemExit):
            parse_args(["--product", "X", "--description", "Y", "--platform", "tiktok"])


class TestLengthCheck(unittest.TestCase):
    def test_twitter_limit(self):
        short = MarketingCopy(headline="Hi", body="Short", call_to_action="Go", hashtags=[])
        long = MarketingCopy(headline="Hi", body="x" * 300, call_to_action="Go", hashtags=[])
        self.assertTrue(measure(short, "twitter")[1])
        self.assertFalse(measure(long, "twitter")[1])


class TestBatch(unittest.TestCase):
    def test_runs_all_platforms_with_tone_settings(self):
        client = FakeClient()
        requests = [make_request(p) for p in ["linkedin", "instagram", "email"]]
        results = asyncio.run(run_batch(client, requests))
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.copy_text.headline == "Stay cold" for r in results))
        self.assertTrue(all(c["temperature"] == 0.9 for c in client.aio.models.calls))

    def test_one_failure_does_not_stop_others(self):
        client = FakeClient(fail_platform="Instagram")
        requests = [make_request(p) for p in ["linkedin", "instagram", "email"]]
        results = asyncio.run(run_batch(client, requests))
        self.assertIsInstance(results[1], Exception)
        self.assertEqual(results[0].platform, "linkedin")
        self.assertEqual(results[2].platform, "email")


if __name__ == "__main__":
    unittest.main()
