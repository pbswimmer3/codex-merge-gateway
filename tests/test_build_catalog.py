import unittest

from build_catalog import MERGE_MODELS, make_entry


class MakeEntryTests(unittest.TestCase):
    def test_gateway_models_review_with_their_own_slug(self):
        template = {
            "slug": "gpt-5.5",
            "display_name": "GPT-5.5",
            "description": "Template",
        }

        for spec in MERGE_MODELS:
            entry = make_entry(template, spec)
            self.assertEqual(entry["auto_review_model_override"], spec["slug"])


if __name__ == "__main__":
    unittest.main()
