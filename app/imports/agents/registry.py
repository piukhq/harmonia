import importlib

AGENTS = {
    'fake-active': 'app.imports.agents.fakescheme.FakeSchemeAPIAgent',
    'fake-passive': 'app.imports.agents.passive_test.PassiveTestAgent',
    'fake-file': 'app.imports.agents.testdir.TestDirAgent',
}


class InvalidAgentKeyError(Exception):
    pass


class InvalidRegistryPathError(Exception):
    pass


class InvalidImportModuleError(Exception):
    pass


class InvalidAgentClassError(Exception):
    pass


def get_agent(key):
    try:
        mod_path, agent_class_name = AGENTS[key].rsplit('.', 1)
    except KeyError as ex:
        raise InvalidAgentKeyError from ex
    except ValueError as ex:
        raise InvalidRegistryPathError from ex

    try:
        mod = importlib.import_module(mod_path)
    except ImportError as ex:
        raise InvalidImportModuleError from ex

    try:
        agent_class = getattr(mod, agent_class_name)
    except AttributeError as ex:
        raise InvalidAgentClassError from ex

    return agent_class()
