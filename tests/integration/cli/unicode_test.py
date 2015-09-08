# -*- coding: utf-8 -*-

from ...testcases import DustyIntegrationTestCase
from ...fixtures import unicode_fixture

class TestBundlesCLI(DustyIntegrationTestCase):
    def test_bundles_with_unicode_names(self):
        unicode_fixture()
        self.run_command('bundles activate bundle-Ɯ')
        result = self.run_command('bundles list')
        self.assertInSameLine(result, u'bundle-Ɯ', 'X')
