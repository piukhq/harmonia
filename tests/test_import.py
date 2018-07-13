import pytest

from app.imports.agents import registry
from app.imports.agents.active_api_agent import ActiveAPIAgent
from app.imports.agents.passive_api_agent import PassiveAPIAgent
from app.imports.agents.directory_watch_agent import DirectoryWatchAgent
from app.imports.agent_base import Agent


def test_get_valid_agents():
    assert isinstance(registry.get_agent('active'), ActiveAPIAgent)
    assert isinstance(registry.get_agent('passive'), PassiveAPIAgent)
    assert isinstance(registry.get_agent('dirwatch'), DirectoryWatchAgent)


def test_get_invalid_agent_key():
    with pytest.raises(registry.InvalidAgentKeyError):
        registry.get_agent('badbad')


def test_get_agent_with_invalid_registry_path():
    k = 'test-invalid-registry-path'
    registry.AGENTS[k] = 'no-dots'

    with pytest.raises(registry.InvalidRegistryPathError):
        registry.get_agent(k)

    del registry.AGENTS[k]


def test_get_agent_with_invalid_import_module():
    k = 'test-invalid-import-module'
    registry.AGENTS[k] = 'app.notarealmodule12345.NotARealAgent12345'

    with pytest.raises(registry.InvalidImportModuleError):
        registry.get_agent(k)

    del registry.AGENTS[k]


def test_get_agent_with_invalid_class_name():
    k = 'test-invalid-class-name'
    registry.AGENTS[k] = 'app.imports.agents.registry.NotARealAgent12345'

    with pytest.raises(registry.InvalidAgentClassError):
        registry.get_agent(k)

    del registry.AGENTS[k]


def test_base_agent():
    a = Agent()
    assert 'override' in a.help()
    with pytest.raises(NotImplementedError):
        a.run()
