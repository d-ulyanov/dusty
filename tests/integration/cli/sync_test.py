from mock import patch

from ...testcases import DustyIntegrationTestCase
from ...fixtures import busybox_single_app_bundle_fixture

class TestSyncCLI(DustyIntegrationTestCase):
    def setUp(self):
        super(TestSyncCLI, self).setUp()
        busybox_single_app_bundle_fixture()
        self.run_command('bundles activate busyboxa')
        self.run_command('up')

    def test_sync_repo(self):
        self.exec_in_container('busyboxa', 'rm -rf /repo')
        self.assertFileNotInContainer('busyboxa', '/repo/README.md')
        self.run_command('sync fake-repo')
        self.assertFileContentsInContainer('busyboxa',
                                           '/repo/README.md',
                                           '# fake-repo')
