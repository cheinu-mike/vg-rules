# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Blank Glyph

"""The release gate must fail closed on incomplete or stale evidence."""

import copy
import unittest
import compliance


class GateTests(unittest.TestCase):
    def setUp(self):
        self.records = []
        for platform, version in compliance.REQUIRED:
            self.records.append({'platform': platform, 'blender': version, 'expected_blender': version,
                                 'blender_architecture': 'arm64' if platform.endswith('arm64') else 'x86_64',
                                 'archive_sha256': 'extension', 'legacy_sha256': 'legacy', 'github_sha': 'revision',
                                 'status': 'PASS', 'checks': [{'name': n, 'status': 'PASS'} for n in compliance.STAGES],
                                 'installed_checks': list(compliance.INSTALLED)})
        self.gui = [{'platform': 'windows-x64', 'blender': v, 'status': 'PASS', 'archive_sha256': 'extension',
                     'checks': [{'name': n, 'status': 'PASS'} for n in compliance.GUI_STAGES],
                     'images': {n: {} for n in ('warning', 'confirmation', 'cancelled', 'continued', 'undo')}}
                    for v in compliance.VERSIONS]

    def errors(self, records=None, gui=None):
        return compliance.evaluate(self.records if records is None else records, self.gui if gui is None else gui,
                                   'extension', 'legacy')[2]

    def test_complete_required_matrix_passes_without_unsupported_intel_52(self):
        self.assertEqual(len(self.records), 11)
        self.assertEqual(self.errors(), [])

    def test_missing_or_duplicate_platform_is_blocker(self):
        self.assertTrue(self.errors(self.records[:-1]))
        self.assertTrue(self.errors(self.records + [self.records[0]]))

    def test_stale_installer_and_wrong_architecture_block_release(self):
        for key, value in (('archive_sha256', 'old'), ('legacy_sha256', 'old'),
                           ('blender_architecture', 'unknown'), ('expected_blender', None), ('github_sha', None)):
            with self.subTest(key=key):
                records = copy.deepcopy(self.records)
                records[0][key] = value
                self.assertTrue(self.errors(records))

    def test_failed_missing_or_duplicate_stage_blocks_even_overall_pass(self):
        for variant in ('failed', 'missing', 'duplicate'):
            records = copy.deepcopy(self.records)
            checks = records[0]['checks']
            if variant == 'failed':
                checks[0]['status'] = 'FAIL'
            elif variant == 'missing':
                checks.pop()
            else:
                checks.append(checks[0])
            self.assertTrue(self.errors(records))

    def test_read_only_offline_installed_suite_evidence_required(self):
        records = copy.deepcopy(self.records)
        records[0]['installed_checks'] = []
        self.assertTrue(self.errors(records))

    def test_gui_missing_failed_stale_or_incomplete_blocks_release(self):
        self.assertTrue(self.errors(gui=[]))
        for change in ('failed', 'stale', 'incomplete', 'images'):
            gui = copy.deepcopy(self.gui)
            if change == 'failed':
                gui[0]['checks'][0]['status'] = 'FAIL'
            elif change == 'stale':
                gui[0]['archive_sha256'] = 'old'
            elif change == 'incomplete':
                gui[0]['checks'].pop()
            else:
                gui[0]['images'].pop('undo')
            self.assertTrue(self.errors(gui=gui))


if __name__ == '__main__':
    unittest.main()

