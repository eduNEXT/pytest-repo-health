"""
pytest plugin to test if specific repo follows standards
"""
import os
from collections import defaultdict

import pytest

import yaml


session_data_holder_dict = defaultdict(dict)

@pytest.fixture(scope="session")
def all_results():
    return session_data_holder_dict

def pytest_configure(config):
    """
    pytest hook used to add plugin install dir as place for pytest to find tests
    """

    if config.getoption("repo_health"):

        # Add path to pytest-repo-health dir so pytest knows where to look for checks
        file_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        config.args.append(file_dir)

        # add repo path so a repo can design their own checks inside a repo_state_checks dir
        repo_path = config.getoption("repo_path")  # pylint: disable=redefined-outer-name
        if repo_path is None:
            repo_path = os.getcwd()
        config.args.append(os.path.abspath(repo_path))

        # in case repo_health checks are in seperate repo
        repo_health_path = config.getoption("repo_health_path")
        if repo_health_path is not None:
            config.args.append(os.path.abspath(repo_health_path))

        # Change test prefix to check
        config._inicache['python_files'] = ['check_*.py']  # pylint: disable=protected-access
        config._inicache['python_functions'] = ['check_*']  # pylint: disable=protected-access
    return config


def pytest_addoption(parser):
    """
    pytest hook used to add command line options used by this plugin
    """
    group = parser.getgroup('repo_health')
    group.addoption(
        "--repo-path",
        action="store",
        dest='repo_path',
        default=None,
        help="path of repository on which to perform checks"
    )

    group.addoption(
        "--repo-health-path",
        action="store",
        dest='repo_health_path',
        default=None,
        help="path to repository where the checks are located. Even with this set, plugin will check in current dir"
    )

    # Since pytest repo_health modifies many pytest settings, this flag is necessary
    # to make sure pytest settings are only changed when health checks run
    group.addoption(
        "--repo-health",
        action="store_true",
        dest='repo_health',
        default=False,
        help="if true, only repository health checks will be run"
    )

    group.addoption(
        "--output-path",
        action="store",
        dest='output_path',
        default="repo_health.yaml",
        help="path to where yaml file should be stored"
    )

    group.addoption(
        "--repo-health-metadata",
        action="store_true",
        dest='repo_health_metadata',
        default=False,
        help="if true, plugin will collect repo health metadata from each check"
    )


@pytest.fixture
def repo_path(request):
    """
    pytest fixture to be used to get path to repo being tested
    """
    path = request.config.option.repo_path
    if path is None:
        path = os.getcwd()
    path = os.path.abspath(path)
    return path

@pytest.fixture
def repo_health(request):
    """
    pytest fixture used to see if repo health check is being run
    if repo_health is set to true:
        only repo health checks will be run
    else:
        no repo_health checks will be run, other tests may or may not be run
    """
    return request.config.option.repo_health

def pytest_ignore_collect(path, config):
    """
    pytest hook that determines if pytest looks at specific file to collect tests
    if repo_health is set to true:
        only tests in test files with "repo_state_checks" in their path will be collected
    """
    if config.getoption("repo_health"):
        if "/repo_health" not in str(path):
            return True
    return False

# Unused argument "session", but pylint complains if it is renamed "_session"
# pylint: disable=unused-argument
def pytest_collection_modifyitems(session, config, items):
    """
    pytest hook, post-collection: Read output key metadata from checks
    and dump to metadata.yaml in current working directory.
    """
    if config.getoption("repo_health") and config.getoption("repo_health_metadata"):
        checks_metadata = {}
        for item in items:
            item_meta = item.function.__dict__.get('pytest_repo_health')
            if item_meta is not None:
                module_name = item.parent.name
                if item.parent.name not in checks_metadata.keys():
                    checks_metadata[module_name] = {'module_doc_string':item.parent.module.__doc__.strip()}
                checks_metadata[module_name][item.name] = item_meta
                checks_metadata[module_name][item.name]["doc_string"] = item.function.__doc__.strip()
        with open("metadata.yaml", "w") as write_file:
            yaml.dump(checks_metadata, write_file, indent=4)


def pytest_sessionfinish(session):
    """
    pytest hook used to collect results for tests and put into output file
    """
    if session.config.getoption("repo_health"):
        with open(session.config.getoption("output_path"), "w") as write_file:
            yaml.dump(dict(session_data_holder_dict), write_file, indent=4)
