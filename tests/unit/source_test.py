import os
import tempfile
import shutil

import git
from mock import Mock, patch

from .utils import DustyTestCase
from dusty.commands.repos import override_repo
from dusty.source import (repo_is_overridden, short_repo_name,
                          git_error_handling, ensure_local_repo, update_local_repo,
                          _expand_repo_name)

class TestSource(DustyTestCase):
    def setUp(self):
        super(TestSource, self).setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(TestSource, self).tearDown()
        shutil.rmtree(self.temp_dir)

    def test_repo_is_overridden_true(self):
        override_repo('github.com/app/a', self.temp_dir)
        self.assertTrue(repo_is_overridden('github.com/app/a'))

    def test_repo_is_overridden_false(self):
        self.assertFalse(repo_is_overridden('github.com/app/a'))

    def test_short_repo_name(self):
        self.assertEqual(short_repo_name('github.com/app/a'), 'a')

    @patch('dusty.source.log_to_client')
    def test_git_error_handling(self, fake_log_to_client):
        with self.assertRaises(git.exc.GitCommandError):
            with git_error_handling():
                raise git.exc.GitCommandError('cmd', 'status')
        self.assertTrue(fake_log_to_client.called)

    @patch('git.Repo.clone_from')
    @patch('dusty.source.managed_repo_path')
    def test_ensure_local_repo_when_does_not_exist(self, fake_repo_path, fake_clone_from):
        temp_dir = os.path.join(self.temp_dir, 'a')
        fake_repo_path.return_value = temp_dir
        ensure_local_repo('github.com/app/a')
        fake_clone_from.assert_called_with('ssh://git@github.com/app/a', temp_dir)

    @patch('git.Repo.clone_from')
    @patch('dusty.source.managed_repo_path')
    def test_ensure_local_repo_when_repo_exist(self, fake_repo_path, fake_clone_from):
        fake_repo_path.return_value = self.temp_dir
        ensure_local_repo('github.com/app/a')
        self.assertFalse(fake_clone_from.called)

    @patch('git.Repo')
    @patch('dusty.source.ensure_local_repo')
    def test_update_local_repo(self, fake_local_repo, fake_repo):
        repo_mock = Mock()
        pull_mock = Mock()
        repo_mock.remote.return_value = pull_mock
        fake_repo.return_value = repo_mock
        update_local_repo('github.com/app/a')
        pull_mock.pull.assert_called_once_with('master')

    @patch('dusty.source.get_all_repos')
    def test_expand_repo_name_real_name(self, fake_get_repos):
      fake_get_repos.return_value = set(['github.com/app/a', 'github.com/app/b'])
      self.assertEquals(_expand_repo_name('a'), 'github.com/app/a')

    @patch('dusty.source.get_all_repos')
    def test_expand_repo_name_conflict(self, fake_get_repos):
      fake_get_repos.return_value = set(['github.com/app/a', 'github.com/lib/a'])
      with self.assertRaises(RuntimeError):
        _expand_repo_name('a')

    @patch('dusty.source.get_all_repos')
    def test_expand_repo_name_not_found(self, fake_get_repos):
      fake_get_repos.return_value = set(['github.com/app/a', 'github.com/lib/b'])
      with self.assertRaises(RuntimeError):
        _expand_repo_name('c')