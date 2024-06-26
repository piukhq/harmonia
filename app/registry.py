import importlib
import typing as t


class RegistryError(Exception):
    pass


class NoSuchAgent(RegistryError):
    pass


class RegistryConfigurationError(RegistryError):
    pass


class InstantiationError(RegistryError):
    pass


T = t.TypeVar("T")


class Registry(t.Generic[T]):
    def __init__(self) -> None:
        self._entries: t.Dict[str, str] = {}

    def __contains__(self, item: str) -> bool:
        return item in self._entries

    def add(self, key: str, import_path: str) -> None:
        self._entries[key] = import_path

    def remove(self, key: str) -> None:
        del self._entries[key]

    def registered_entries(self, key: str) -> t.List[str]:
        try:
            return self._entries[key].rsplit(".", 1)
        except KeyError as ex:
            raise NoSuchAgent(f"Invalid registry key: {key}") from ex
        except ValueError as ex:
            raise RegistryConfigurationError(f"Invalid import path: {self._entries[key]}") from ex

    def instantiate(self, key: str, *args, **kwargs) -> T:
        mod_path, class_name = self.registered_entries(key)

        try:
            mod = importlib.import_module(mod_path)
        except ImportError as ex:
            raise RegistryConfigurationError(f"Failed to import module {mod_path}: {ex}") from ex

        try:
            object_class = getattr(mod, class_name)
        except AttributeError as ex:
            raise RegistryConfigurationError(f"Class {class_name} was not found in module {mod}") from ex

        try:
            return object_class(*args, **kwargs)
        except Exception as ex:
            raise InstantiationError(f"Failed to instantiate {key} agent") from ex
