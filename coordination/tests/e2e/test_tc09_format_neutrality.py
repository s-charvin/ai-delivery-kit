from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.e2e._util import HappyPathDriver


class TestTC09FormatNeutrality:
    def test_4_formats_pass_review(self, env):
        driver = HappyPathDriver(env)
        driver.create_pipeline("fullstack")

        formats_to_test = [
            ("artifacts/n1/product-spec.ecc.md", b"# ECC Spec\n\nProduct specification content here.\n- item 1\n- item 2\n"),
            ("artifacts/n1/product-spec.openspec.yaml", yaml.safe_dump({
                "openapi": "3.0.0",
                "info": {"title": "test", "version": "1.0.0"},
                "paths": {},
            }).encode("utf-8")),
            ("artifacts/n1/product-spec.spec-kit.json", json.dumps({
                "schema_version": "1.0",
                "name": "test-spec",
                "artifacts": [],
            }).encode("utf-8")),
            ("artifacts/n1/product-spec.custom.yaml", yaml.safe_dump({
                "custom_format": True,
                "version": 1,
                "metadata": {"author": "test"},
            }).encode("utf-8")),
        ]

        pr_id, _fp = driver._submit_to_hub(
            node_id="n1",
            content=formats_to_test[0][1],
            classification=1,
            change_class="compatible",
            pr_extra_template=None,
            artifact_type="product_spec",
            path=formats_to_test[0][0],
        )
        for path_val, content_bytes in formats_to_test:
            cb = {path_val: content_bytes}
            review_result = driver._run_engine_review("n1", pr_id, cb)
            verdict = review_result.get("verdict")
            assert verdict != "reject", (
                f"format path {path_val} was rejected: "
                f"rejected_by={review_result.get('rejected_by')}, "
                f"checks={review_result.get('checks')}"
            )

        sha1 = driver.submit_and_approve("n1")
        assert sha1, "final standard format submit_and_approve still passes"
