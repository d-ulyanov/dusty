from functools import wraps
from mock import patch

from nose.tools import nottest

from . import (get_all_test_configs, resources_for_test_config, specs_for_test_config,
               assembled_specs_for_test_config, nginx_config_for_test_config, docker_compose_yaml_for_test_config)
from dusty.compiler import spec_assembler
from ...testcases import DustyTestCase
from dusty import constants
from dusty.source import Repo
from ..utils import get_app_dusty_schema, get_lib_dusty_schema, get_bundle_dusty_schema, apply_required_keys

@nottest
def all_test_configs(test_func):
    @wraps(test_func)
    def inner(cls):
        for test_config in get_all_test_configs():
            case_specs = specs_for_test_config(test_config)
            assembled_specs = assembled_specs_for_test_config(test_config)
            print "Running test case: {}".format(test_config)
            test_func(cls, test_config, case_specs, assembled_specs)
            print "Test case {} completed".format(test_config)
    return inner

class TestCompilerTestCases(DustyTestCase):
    def test_compiler_test_configs(test_config):
        for test_config in get_all_test_configs():
            pass

class TestSpecAssemblerTestCases(DustyTestCase):
    @all_test_configs
    def test_retrieves_downstream_apps(self, test_config, case_specs, assembled_specs):
        downstream_apps = spec_assembler._get_referenced_apps(case_specs)
        assembled_apps = set(assembled_specs['apps'].keys())
        self.assertEqual(downstream_apps, assembled_apps)

    @all_test_configs
    def test_expands_libs_in_apps(self, test_config, case_specs, assembled_specs):
        spec_assembler._expand_libs_in_apps(case_specs)
        for app_name, app in case_specs['apps'].iteritems():
            self.assertEqual(set(app['depends']['libs']), set(assembled_specs['apps'][app_name]['depends']['libs']))

    @all_test_configs
    def test_assembles_specs(self, test_config, case_specs, assembled_specs, *args):
        self.maxDiff = None
        bundles = case_specs[constants.CONFIG_BUNDLES_KEY].keys()
        @patch('dusty.compiler.spec_assembler._get_active_bundles', return_value=bundles)
        def run_patched_assembler(case_specs, *args):
            spec_assembler._get_expanded_active_specs(case_specs)
        run_patched_assembler(case_specs)
        for spec_type in ('bundles', 'apps', 'libs', 'services'):
            for name, spec in assembled_specs[spec_type].iteritems():
                if spec:
                    for spec_level_key, value in spec.iteritems():
                        if spec_type == 'apps' and spec_level_key == 'depends' and value['libs'] == []:
                            value['libs'] = set([])
                        self.assertEquals(value, case_specs[spec_type][name][spec_level_key])

    def test_get_dependent_traverses_tree(self):
        specs = {
            'apps': {
                'app1': get_app_dusty_schema(
                    {'depends': {'apps': ['app2']},
                    'repo': '',
                    'image': ''
                }),
                'app2': get_app_dusty_schema(
                    {
                    'depends': {'apps': ['app3']},
                    'repo': '',
                    'image': ''
                }),
                'app3': get_app_dusty_schema(
                     {
                    'depends': {'apps': ['app4', 'app5']},
                    'repo': '',
                    'image': ''
                }),
                'app4': get_app_dusty_schema(
                     {
                    'depends': {'apps': ['app5']},
                    'repo': '',
                    'image': ''
                }),
                'app5': get_app_dusty_schema({'repo': '', 'image': ''}),
                'app6': get_app_dusty_schema({'repo': '', 'image': ''})
            }
        }
        self.assertEqual(set(['app2', 'app3', 'app4', 'app5']),
            spec_assembler._get_dependent('apps', 'app1', specs, 'apps'))

    def test_get_dependent_root_type(self):
        specs = {
            'apps': {
                'app1': get_app_dusty_schema(
                    {'depends': {
                        'apps': ['app2'],
                        'libs': ['lib1']},
                    'repo': '',
                    'image': ''
                }),
                'app2': get_app_dusty_schema(
                    {'repo': '',
                     'image': ''
                })
            },
            'libs': {
                'lib1': get_lib_dusty_schema(
                    {'depends': {'libs': ['lib2']},
                     'repo': ''}),
                'lib2': get_lib_dusty_schema({'repo': ''}),
                'lib3': get_lib_dusty_schema({'repo': ''})
            }
        }
        self.assertEqual(set(['lib1', 'lib2']),
            spec_assembler._get_dependent('libs', 'app1', specs, 'apps'))

class TestSpecAssemblerGetRepoTestCases(DustyTestCase):
    def test_get_repo_of_app_or_service_app(self):
        self.assertEqual(spec_assembler.get_repo_of_app_or_library('app-a'), Repo('github.com/app/a'))

    def test_get_repo_of_app_or_service_lib(self):
        self.assertEqual(spec_assembler.get_repo_of_app_or_library('lib-a'), Repo('github.com/lib/a'))

    def test_get_repo_of_app_or_service_neither(self):
        with self.assertRaises(KeyError):
            spec_assembler.get_repo_of_app_or_library('lib-b')

class TestGetExpandedLibSpecs(DustyTestCase):
    def test_get_expanded_lib_specs_1(self):
        specs =  {
                'apps': {
                    'app1': get_app_dusty_schema({
                        'depends': {
                            'libs': ['lib1', 'lib2'],
                            'apps': ['app2']
                        },
                        'repo': '',
                        'image': ''
                    }),
                    'app2': get_app_dusty_schema({
                        'depends': {},
                        'repo': '',
                        'image': ''
                    })
                },
                'libs': {
                    'lib1': get_lib_dusty_schema({
                        'depends': {
                            'libs': ['lib2']
                        },
                        'repo': ''
                    }),
                    'lib2': get_lib_dusty_schema({
                        'depends': {
                            'libs': ['lib3']
                        },
                        'repo': ''
                    }),
                    'lib3': get_lib_dusty_schema({
                        'depends': {},
                        'repo': ''
                    })
                }
            }
        expected_expanded_specs = {
                'apps': {
                    'app1': {
                        'commands': {
                            'always': ['sleep 1'],
                            'once': []
                        },
                        'depends': {
                            'libs': set(['lib1', 'lib2', 'lib3']),
                            'apps': ['app2'],
                            'services': []
                        },
                        'repo': '',
                        'image': ''
                    },
                    'app2': {
                        'commands': {
                            'always': ['sleep 1'],
                            'once': []
                        },
                        'repo': '',
                        'image': ''
                    }
                },
                'libs': {
                    'lib1': {
                        'depends': {
                            'libs': set(['lib2', 'lib3'])
                        },
                        'repo': ''
                    },
                    'lib2': {
                        'depends': {
                            'libs': set(['lib3'])
                        },
                        'repo': ''
                    },
                    'lib3': {
                        'repo': ''
                    }
                }
            }
        spec_assembler._get_expanded_libs_specs(specs)
        for spec_type in ('apps', 'libs'):
            for name, spec in expected_expanded_specs[spec_type].iteritems():
                for spec_level_key, value in spec.iteritems():
                    self.assertEquals(specs[spec_type][name][spec_level_key], value)


class TestGetDependentRepos(DustyTestCase):
    @patch('dusty.compiler.spec_assembler.get_specs')
    def test_get_same_container_repos_app(self, fake_get_specs):
        fake_get_specs.return_value = self.make_test_specs(apply_required_keys(
                                      {'apps': {'app1': {
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                    'depends': {'apps': ['app2', 'app3'],
                                                                 'libs': ['lib1']},
                                                    'repo': '/gc/app1'},
                                                'app2': {
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                    'depends': {'apps': ['app4'],
                                                    'libs': []},
                                                    'repo': '/gc/app2'
                                                },
                                                'app3': {
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                    'depends': {'apps': [], 'libs': []}, 'repo': '/gc/app3'
                                                },
                                                'app4': {
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                    'depends': {'apps': [], 'libs': []}, 'repo': '/gc/app4'}
                                                },
                                       'libs': {'lib1': {'depends': {'libs': ['lib2']}, 'repo': '/gc/lib1'},
                                                'lib2': {'depends': {'libs': []}, 'repo': '/gc/lib2'}}}))

        self.assertEquals(set(spec_assembler.get_same_container_repos('app1')),
                          set([Repo('/gc/app1'), Repo('/gc/lib1'), Repo('/gc/lib2')]))

    @patch('dusty.compiler.spec_assembler.get_specs')
    def test_get_same_container_repos_app_without_repo(self, fake_get_specs):
        fake_get_specs.return_value = self.make_test_specs(apply_required_keys({
                                            'apps': {
                                                'app1': {
                                                    'depends': {'apps': ['app2', 'app3'],
                                                                 'libs': ['lib1']},
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                },
                                                'app2': {
                                                    'depends': {'apps': ['app4'],
                                                    'libs': []},
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                    'repo': '/gc/app2'
                                                },
                                                'app3': {
                                                    'depends': {'apps': [], 'libs': []},
                                                    'repo': '/gc/app3',
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                },
                                                'app4': {
                                                    'depends': {'apps': [], 'libs': []},
                                                    'repo': '/gc/app4',
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                }
                                            },
                                           'libs': {'lib1': {'depends': {'libs': ['lib2']}, 'repo': '/gc/lib1'},
                                                    'lib2': {'depends': {'libs': []}, 'repo': '/gc/lib2'}}}))

        self.assertEquals(set(spec_assembler.get_same_container_repos('app1')),
                          set([Repo('/gc/lib1'), Repo('/gc/lib2')]))

    @patch('dusty.compiler.spec_assembler.get_specs')
    def test_get_same_container_repos_lib(self, fake_get_specs):
        fake_get_specs.return_value = self.make_test_specs(apply_required_keys({
                                        'apps': {'app1':
                                                    {'depends': {'apps': ['app2', 'app3'],
                                                                 'libs': ['lib1']},
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                    'repo': '/gc/app1'},
                                                'app2':
                                                    {'depends': {'apps': ['app4'],
                                                     'libs': []},
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                     'repo': '/gc/app2'},
                                                'app3': {
                                                    'depends': {'apps': [], 'libs': []},
                                                    'repo': '/gc/app3',
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                },
                                                'app4': {
                                                    'depends': {'apps': [], 'libs': []},
                                                    'repo': '/gc/app4',
                                                    'commands': {
                                                        'always': ['sleep 10']
                                                    },
                                                }
                                        },
                                       'libs': {'lib1': {'depends': {'libs': ['lib2']}, 'repo': '/gc/lib1'},
                                                'lib2': {'depends': {'libs': []}, 'repo': '/gc/lib2'}}}))

        self.assertEquals(set(spec_assembler.get_same_container_repos('lib1')),
                          set([Repo('/gc/lib1'), Repo('/gc/lib2')]))
