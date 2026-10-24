# SPDX-License-Identifier: MIT
"""Reviewed metadata binding only; synthetic records never admit a real model."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from prepare_first_case import data_plan_path, record


class ReviewedDataPlan(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.plan = self.root / "original-plan.json"
        self.plan.write_text(json.dumps(dict(nonce="a" * 32, original_receipt=dict(sha256="b" * 64))))
        self.marker = self.root / "marker.json"
        self.marker.write_text(json.dumps(dict(schema="ps5-qwen-model-directory-owner-v1",
            nonce="a" * 32, original_receipt_sha256="b" * 64)))
        self.failure = self.root / "retained-failure.json"
        self.failure.write_text(json.dumps(dict(phase="mkdir", title_launches=0, GPU_calls=0)))
        self.directory = self.root / "directory.json"
        self.directory.write_text(json.dumps(dict(schema="ps5-qwen-model-directory-preparation-v1",
            parent_ownership_restored=True, marker_full_readback_verified=True,
            plan_sha256=record(self.plan)["sha256"], owner_nonce="a" * 32, marker=record(self.marker))))
        self.review = self.root / "review.json"
        self.review_value = dict(schema="ps5-qwen-reviewed-directory-resume-complete-v1",
            existing_empty_directory_verified=True, prepare_and_MKD_repeated=False,
            marker_uploaded_once=True, finalize_positive=True, parent_ownership_restored=True,
            automatic_retries=0, title_launches=0, GPU_calls=0, original_failure=record(self.failure),
            original_plan=record(self.plan), directory_preparation=record(self.directory))
        self.review.write_text(json.dumps(self.review_value))
        self.complete = dict(schema="ps5-qwen-model-data-continuation-complete-v2",
            original_plan=record(self.plan), reviewed_directory_resume=record(self.review),
            directory_preparation=record(self.directory))

    def check(self):
        return data_plan_path(self.complete, self.root / "new-data/complete.json", self.root)

    def test_legacy_layout_is_preserved(self):
        path = self.root / "legacy/complete.json"
        self.assertEqual(data_plan_path(dict(schema="ps5-qwen-model-data-continuation-complete-v1"),
            path, self.root), path.parent / "plan/plan.private.json")

    def test_positive_review_retains_original_plan(self):
        self.assertEqual(self.check(), self.plan)

    def test_changed_marker_is_rejected(self):
        self.marker.write_text("changed")
        with self.assertRaises(ValueError): self.check()

    def test_changed_or_different_plan_is_rejected(self):
        self.plan.write_text("{}")
        with self.assertRaises(ValueError): self.check()

    def test_repeated_or_unfinished_review_is_rejected(self):
        for key, value in (("prepare_and_MKD_repeated", True), ("finalize_positive", False), ("GPU_calls", True)):
            with self.subTest(key=key):
                changed = dict(self.review_value, **{key: value})
                self.review.write_text(json.dumps(changed))
                self.complete["reviewed_directory_resume"] = record(self.review)
                with self.assertRaises(ValueError): self.check()

    def test_external_metadata_path_is_rejected(self):
        self.complete["original_plan"] = record(Path(__file__).resolve())
        with self.assertRaises(ValueError): self.check()


if __name__ == "__main__": unittest.main()
