from mock import patch, call
from copy import copy

from dusty import constants
from dusty.compiler.compose import (get_compose_dict, _composed_app_dict,
                                    _get_ports_list, _compile_docker_command, _get_compose_volumes,
                                    _lib_install_command, _lib_install_commands_for_app, _conditional_links,
                                    get_app_volume_mounts, get_lib_volume_mounts)
from ..test_test_cases import all_test_configs
from ....testcases import DustyTestCase

basic_specs = {
    'apps': {
        'app1': {
            'repo': '/app1',
            'depends': {
                'libs': ['lib1', 'lib2'],
                'services': ['service1', 'service2'],
                'apps': ['app2']
            },
            'commands': {
                'once': "one_time.sh",
                'always': "always.sh"
            },
            'image': 'awesomeGCimage',
            'mount': '/gc/app1'
        },
        'app2': {
            'repo': '/app2',
            'depends': {},
            'mount': '/gc/app2'
        }
    },
    'libs': {
        'lib1': {
            'repo': '/lib1',
            'mount': '/gc/lib1',
            'install': './install.sh',
            'depends': {
                'libs': ['lib2']
            }
        },
        'lib2': {
            'repo': '/lib2',
            'mount': '/gc/lib2',
            'install': 'python setup.py develop'
        }
    },
    'services':{
        'service1': {

        },
        'service2': {

        }
    }
}

basic_port_specs = {
    'docker_compose': {
        'app1': [
            { 'mapped_host_port': 8000, 'in_container_port': 1},
            { 'mapped_host_port': 8005, 'in_container_port': 90}
        ],
        'app2': []
    }
}

class TestComposeCompiler(DustyTestCase):
    def setUp(self):
        super(TestComposeCompiler, self).setUp()
        self.old_vm_repos_dir = constants.VM_REPOS_DIR
        constants.VM_REPOS_DIR = '/Users/gc'

    def tearDown(self):
        super(TestComposeCompiler, self).tearDown()
        constants.VM_REPOS_DIR = self.old_vm_repos_dir

    def test_composed_volumes(self, *args):
        expected_volumes = [
            '/cp/app1:/cp',
            '/Users/gc/app1:/gc/app1',
            '/Users/gc/lib1:/gc/lib1',
            '/Users/gc/lib2:/gc/lib2'
        ]
        returned_volumes = _get_compose_volumes('app1', basic_specs)
        self.assertEqual(expected_volumes, returned_volumes)

    def testget_app_volume_mounts_1(self, *args):
        expected_volumes = [
            '/Users/gc/app1:/gc/app1',
            '/Users/gc/lib1:/gc/lib1',
            '/Users/gc/lib2:/gc/lib2'
        ]
        returned_volumes = get_app_volume_mounts('app1', basic_specs)
        self.assertEqual(expected_volumes, returned_volumes)

    def testget_app_volume_mounts_2(self, *args):
        expected_volumes = ['/Users/gc/app2:/gc/app2']
        returned_volumes = get_app_volume_mounts('app2', basic_specs)
        self.assertEqual(expected_volumes, returned_volumes)

    def testget_lib_volume_mounts_1(self, *args):
        expected_volumes = [
            '/Users/gc/lib1:/gc/lib1',
            '/Users/gc/lib2:/gc/lib2'
        ]
        returned_volumes = get_lib_volume_mounts('lib1', basic_specs)
        self.assertEqual(expected_volumes, returned_volumes)

    def testget_lib_volume_mounts_2(self, *args):
        expected_volumes = ['/Users/gc/lib2:/gc/lib2']
        returned_volumes = get_lib_volume_mounts('lib2', basic_specs)
        self.assertEqual(expected_volumes, returned_volumes)

    def test_compile_command_with_once(self, *args):
        expected_command_list = ["sh -c \"cd /gc/lib1 && ./install.sh",
                                 " cd /gc/lib2 && python setup.py develop",
                                 " cd /gc/app1",
                                 " export PATH=$PATH:/gc/app1",
                                 " if [ ! -f /var/run/dusty/docker_first_time_started ]",
                                 " then mkdir -p /var/run/dusty",
                                 " touch /var/run/dusty/docker_first_time_started",
                                 " one_time.sh",
                                 " fi",
                                 " always.sh\""]
        returned_command = _compile_docker_command('app1', basic_specs).split(";")
        self.assertEqual(expected_command_list, returned_command)

    def test_compile_command_without_once(self, *args):
        new_specs = copy(basic_specs)
        del new_specs['apps']['app1']['commands']['once']
        expected_command_list = ["sh -c \"cd /gc/lib1 && ./install.sh",
                                 " cd /gc/lib2 && python setup.py develop",
                                 " cd /gc/app1",
                                 " export PATH=$PATH:/gc/app1",
                                 " if [ ! -f /var/run/dusty/docker_first_time_started ]",
                                 " then mkdir -p /var/run/dusty",
                                 " touch /var/run/dusty/docker_first_time_started",
                                 " fi",
                                 " always.sh\""]
        returned_command = _compile_docker_command('app1', new_specs).split(";")
        self.assertEqual(expected_command_list, returned_command)

    def test_ports_list(self, *args):
        expected_port_lists = {
            'app1': [
                '8000:1',
                '8005:90'
            ],
            'app2': []
        }
        for app in ['app1', 'app2']:
            self.assertEqual(expected_port_lists[app], _get_ports_list(app, basic_port_specs))

    @patch('dusty.compiler.compose._compile_docker_command', return_value="what command?")
    def test_composed_app(self, *args):
        expected_app_config = {
            'image': 'awesomeGCimage',
            'command': 'what command?',
            'links': [
                'service1',
                'service2',
                'app2'
            ],
            'volumes': [
                '/cp/app1:/cp',
                '/Users/gc/app1:/gc/app1',
                '/Users/gc/lib1:/gc/lib1',
                '/Users/gc/lib2:/gc/lib2'
            ],
            'ports': [
                '8000:1',
                '8005:90'
            ]
        }
        retured_config = _composed_app_dict('app1', basic_specs, basic_port_specs)
        self.assertEqual(expected_app_config, retured_config)

    def test_lib_install_command(self, *args):
        lib_spec = {
            'repo': 'some repo',
            'mount': '/mount/point',
            'install': 'python install.py some args'
        }
        expected_command = "cd /mount/point && python install.py some args"
        actual_command = _lib_install_command(lib_spec)
        self.assertEqual(expected_command, actual_command)

    def test_lib_install_command_with_no_install_spec(self, *args):
        lib_spec = {
            'repo': 'some repo',
            'mount': '/mount/point'
        }
        expected_command = ""
        actual_command = _lib_install_command(lib_spec)
        self.assertEqual(expected_command, actual_command)

    @patch('dusty.compiler.compose._lib_install_command')
    def test_lib_installs_for_app(self, fake_lib_install, *args):
        _lib_install_commands_for_app('app1', basic_specs)
        # Mock is weird, it picks up on the truthiness calls we do
        # on the result after we call the function
        fake_lib_install.assert_has_calls([call(basic_specs['libs']['lib1']),
                                           call().__nonzero__(),
                                           call(basic_specs['libs']['lib2']),
                                           call().__nonzero__()])

    def test_get_available_app_links_no_services_1(self, *args):
        assembled_specs = {'apps': {
                                'app-a': {
                                    'depends': {
                                        'apps': ['app-b']
                                    },
                                    'conditional_links': {
                                        'apps':['app-c']
                                    }
                                },
                                'app-b': {
                                    'depends': {}
                                }
                            }}
        self.assertEqual(_conditional_links(assembled_specs, 'app-a'), [])

    def test_get_available_app_links_no_services_2(self, *args):
        assembled_specs = {'apps': {
                                'app-a': {
                                    'depends': {
                                        'apps': ['app-b']
                                    },
                                    'conditional_links':{
                                        'apps': ['app-c']
                                    }
                                },
                                'app-b': {
                                    'depends': {}
                                },
                                'app-c': {
                                    'depends': {}
                                }
                            }}
        self.assertEqual(_conditional_links(assembled_specs, 'app-a'), ['app-c'])

    def test_get_available_app_links_only_services_1(self, *args):
        assembled_specs = {'apps': {
                                'app-a': {
                                    'depends': {
                                        'apps': ['app-b']
                                    },
                                    'conditional_links': {
                                        'services': ['ser-b']
                                    }
                                },
                                'app-b': {
                                    'depends': {}
                                }
                            },
                            'services': {
                                'ser-a': {
                                    'depends': {}
                                }
                            }}
        self.assertEqual(_conditional_links(assembled_specs, 'app-a'), [])

    def test_get_available_app_links_only_services_2(self, *args):
        assembled_specs = {'apps': {
                                'app-a': {
                                    'depends': {
                                        'apps': ['app-b']
                                    },
                                    'conditional_links': {
                                        'services': ['ser-b']
                                    }
                                },
                                'app-b': {
                                    'depends': {}
                                }
                            },
                            'services': {
                                'ser-b': {
                                    'depends': {}
                                }
                            }}
        self.assertEqual(_conditional_links(assembled_specs, 'app-a'), ['ser-b'])

    def test_get_available_app_links_both(self, *args):
        assembled_specs = {'apps': {
                                'app-a': {
                                    'depends': {},
                                    'conditional_links': {
                                        'services': ['ser-b'],
                                        'apps': ['app-b']
                                    }
                                },
                                'app-b': {
                                    'depends': {}
                                }
                            },
                            'services': {
                                'ser-b': {
                                    'depends': {}
                                }
                            }}
        self.assertEqual(_conditional_links(assembled_specs, 'app-a'), ['app-b', 'ser-b'])
