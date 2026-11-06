"""Exercise the real archive parser/preflight, not a parallel Markdown checker."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from archive_fixture import govern_existing

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('retrospective_archive', ROOT / 'scripts/archive-subrequirement.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
MARKER = '<!-- ai-delivery-retrospective:reviewed-at:2026-09-02 -->'
HEADER = '''<!-- ai-delivery-retrospective:problem-index:v2 -->
| ID | Observable trigger | Applicable scenario | Shortest path | knowledge_type | reuse_scope | index_decision | confidence | importance | Status | Details |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
'''
ROW = '| RET-001 | label typo | local copy | read source | temporary-decision | requirement | exclude | unverified | low | awaiting reproduction | [details](#ret-001) |\n'
END = '<!-- /ai-delivery-retrospective:problem-index:v2 -->\n'
DETAIL = '<a id="ret-001"></a>\n## RET-001: Reported typo\nUser report retained. Cause unknown.\n'

class StructureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.req = Path(self.tmp.name) / '.ai-delivery/requirements/req-check'
        self.req.mkdir(parents=True)
        meta=Path(self.tmp.name)/'.ai-delivery/meta';meta.mkdir()
        (meta/'project-binding.json').write_text('{"version":3,"layout":{}}')
        (meta/'workflow-policy.json').write_text('{"version":4,"verification_contract_version":2}')
        (self.req / 'sub-requirements/SR-001').mkdir(parents=True)
        self.ledger = self.req / 'retrospective.md'
        self.valid = MARKER + '\n' + HEADER + ROW + END + DETAIL

    def parse(self, text):
        self.ledger.write_text(text)
        return archive.read_retrospective_entries(self.ledger)

    def rejected(self, text, message):
        self.ledger.write_text(text)
        with self.assertRaisesRegex(SystemExit, message):
            archive.preflight_retrospective_index(self.req, 'req-check', archive.datetime.datetime(2026, 9, 2), None, False)
        status = self.req / 'status.json'
        status.write_text('{"requirement_id":"req-check","sub_requirements":{"SR-001":{"status":"merged"}}}')
        govern_existing(self.req)
        before = status.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/archive-subrequirement.py'), '--req-root', str(self.req), '--subreq', 'SR-001', '--no-delivery-report', '--now', '2026-09-02T12:00:00+00:00'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr + result.stdout, message)
        self.assertEqual(before, status.read_bytes())

    def test_non_indexable_user_issue_is_preserved(self):
        rows = self.parse(self.valid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(archive.indexable_entries(rows), [])

    def test_heading_slug_and_existing_explicit_anchor(self):
        self.assertEqual(len(self.parse(self.valid.replace('(#ret-001)', '(#ret-001-reported-typo)').replace('<a id="ret-001"></a>\n', ''))), 1)

    def test_existing_anchor_and_link_variants_remain_valid(self):
        for target in ['(#ret-001 "record title")', '(<#ret-001>)', '(<#ret-001> "record title")']:
            with self.subTest(target=target):
                text = self.valid.replace('(#ret-001)', target).replace('<a id="ret-001">', '<a class="stable" id="ret-001">')
                self.assertEqual(len(self.parse(text)), 1)
                self.assertEqual(archive.retrospective_detail_anchor('[details]' + target), 'ret-001')

    def test_valid_link_variants_route_to_the_same_index_fragment(self):
        template = (ROOT / '.agents/skills/ai-delivery-orchestrator/templates/retrospective-index-template.md').read_text().split('-->', 1)[1]
        for target in ['(#ret-001 "record title")', '(<#ret-001>)', '(<#ret-001> "record title")']:
            with self.subTest(target=target):
                text = self.valid.replace('(#ret-001)', target).replace('temporary-decision | requirement | exclude | unverified | low', 'reusable | project | include | confirmed | high')
                self.parse(text)
                index = archive.register_retrospective_index(self.req, 'req-check', archive.datetime.datetime(2026, 9, 2), template)
                self.assertIn('retrospective.md#ret-001)', index.read_text())
                self.assertNotIn('record title', index.read_text())

    def test_anchor_cannot_escape_its_own_heading_section(self):
        text = self.valid.replace('(#ret-001)', '(#summary)') + '\n## Summary\n<a id="summary"></a>\n'
        self.rejected(text, 'RET-001.*anchor')

    def test_sibling_preheading_anchor_is_not_owned_by_previous_ret(self):
        self.rejected(self.valid.replace('(#ret-001)', '(#summary)') + '\n<a id="summary"></a>\n## Summary\n', 'RET-001.*anchor')

    def test_data_attribute_is_not_an_html_anchor(self):
        for attr in ['data-id', 'data-name']:
            self.rejected(self.valid.replace('id="ret-001"', attr + '="ret-001"'), 'RET-001.*anchor')

    def test_multiple_stable_anchors_and_nested_own_section(self):
        text = self.valid.replace('<a id="ret-001"></a>', '<a id="ret-001" name="ret-001"></a>\n<a name="old-id"></a>')
        self.assertEqual(len(self.parse(text)), 1)
        self.assertEqual(len(self.parse(text.replace('(#ret-001)', '(#old-id)'))), 1)
        nested = self.valid.replace('(#ret-001)', '(#own-detail)') + '\n<a id="own-detail"></a>\n### Detail evidence\n'
        self.assertEqual(len(self.parse(nested)), 1)

    def test_real_dates_failed_attempts_and_quoted_patch_words_are_allowed(self):
        text = self.valid + '\n### Failure on 2026-09-01\nfailed; verification on 2026-09-02 is partial.\n```text\n## This round additions\n```\n> User said: append retrospective\n'
        self.assertEqual(len(self.parse(text)), 1)

    def test_duplicate_map_markers(self):
        self.rejected(self.valid + HEADER + END, 'exactly one.*problem-index')

    def test_duplicate_id(self):
        self.rejected(self.valid.replace(END, ROW + END), 'RET-001.*duplicate')

    def test_missing_detail(self):
        self.rejected(self.valid.replace(DETAIL, ''), 'RET-001.*detail')

    def test_broken_anchor(self):
        self.rejected(self.valid.replace('(#ret-001)', '(#missing)'), 'RET-001.*anchor')

    def test_wrong_record_anchor(self):
        self.rejected(self.valid.replace('(#ret-001)', '(#summary)') + '\n## Summary\n', 'RET-001.*anchor')

    def test_anchor_cannot_point_to_another_record(self):
        row2 = ROW.replace('RET-001', 'RET-002').replace('#ret-001', '#ret-002')
        detail2 = DETAIL.replace('RET-001', 'RET-002').replace('ret-001', 'ret-002')
        text = self.valid.replace(END, row2 + END) + detail2
        self.rejected(text.replace('[details](#ret-001)', '[details](#ret-002)'), 'RET-001.*anchor')

    def test_orphan_detail(self):
        self.rejected(self.valid + '\n## RET-002: Forgotten map row\nDetails\n', 'RET-002.*orphan')

    def test_patch_sections_fail_with_line_number(self):
        for heading in ['## 2026-11-03 supplemental retrospective', '## This round additions', '## ' + '\u672c\u8f6e\u65b0\u589e', '## 2026-11-03' + '\u8865\u5ba1']:
            with self.subTest(heading=heading):
                self.rejected(self.valid + '\n' + heading + '\nnew knowledge\n', r'retrospective.md:\d+:.*revision-batch')

    def test_duplicate_reviewed_marker(self):
        self.rejected(self.valid + '\n' + MARKER, 'exactly one marker')

    def test_empty_ledger_is_still_valid(self):
        self.assertEqual(self.parse(MARKER), [])
        self.assertEqual(self.parse(MARKER + '\n' + HEADER + END), [])

if __name__ == '__main__':
    unittest.main()
