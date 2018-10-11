from click.testing import CliRunner
import pytest

from app.imports.agents import registry
from app.imports.cli import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestAgent:
    def help(self):
        return ''


@pytest.fixture
def agent():
    key = 'test-agent-12345'
    registry.AGENTS[key] = f"{TestAgent.__module__}.{TestAgent.__qualname__}"
    yield key
    del registry.AGENTS[key]


def test_cli_no_args(cli_runner):
    result = cli_runner.invoke(cli)
    assert result.exit_code != 0
    assert 'Missing option' in result.output


def test_cli_with_invalid_agent(cli_runner):
    result = cli_runner.invoke(cli, ['-a', 'badagent12345'])
    assert result.exit_code != 0
    assert 'invalid choice' in result.output


def test_cli_with_real_agent(cli_runner, agent):
    result = cli_runner.invoke(cli, ['-a', agent])
    assert result.exit_code == 0, result.output
    assert 'Loaded TestAgent agent from' in result.output


def test_cli_invalid_registry_path(cli_runner, mocker):
    pass


def test_cli_invalid_import_module(cli_runner):
    pass


def test_cli_invalid_agent_class(cli_runner):
    pass
