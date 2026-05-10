"""Generic typed registry for managing singleton instances across the application."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Generic, TypeVar

# Internal
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.services.sessions.database import DatabaseSession

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry for managing singleton instances of a given type.

    Designed to store stateless instances that are created once at startup
    and reused across the application lifecycle.

    Args:
        name (str): Display name for this registry (e.g., "Database", "LLMs").

    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._items: Dict[str, T] = {}

    def register(self, item: T, name: str | None = None) -> None:
        """Register an item instance.

        Args:
            item (T): Item instance to register.
            name (str | None): Optional name override. If not provided,
                attempts to use item.name attribute.

        Raises:
            ValueError: If name is empty or item has no name attribute.

        """
        if name is None:
            if not hasattr(item, "name"):
                raise ValueError(
                    f"Item {item.__class__.__name__} must have a 'name' attribute "
                    "or provide the name parameter."
                )
            name = getattr(item, "name")

        if not name:
            raise ValueError(f"Item {item.__class__.__name__} must have a non-empty name.")

        if name in self._items:
            log.warning("registry.overwrite", registry=self.name, key=name)

        self._items[name] = item
        log.info("registry.registered", registry=self.name, key=name)

    def register_many(self, items: list[T]) -> None:
        """Register multiple items at once.

        Args:
            items (list[T]): List of item instances to register.

        """
        for item in items:
            self.register(item)

    def get(self, name: str) -> T:
        """Get an item by name.

        Args:
            name (str): Name of the registered item.

        Returns:
            T: The registered item instance.

        Raises:
            KeyError: If item not found in registry.

        """
        if name not in self._items:
            available = list(self._items.keys())
            raise KeyError(
                f"[{self.name}] '{name}' not found. Available: {available}"
            )
        return self._items[name]

    def has(self, name: str) -> bool:
        """Check if an item is registered without raising.

        Args:
            name (str): Name to check.

        Returns:
            bool: True if registered, False otherwise.

        """
        return name in self._items

    def list(self) -> list[str]:
        """List all registered item names.

        Returns:
            list[str]: List of registered names.

        """
        return list(self._items.keys())

    def get_all(self) -> Dict[str, T]:
        """Get all registered items.

        Returns:
            Dict[str, T]: Dictionary mapping names to item instances.

        """
        return self._items.copy()

    def clear(self) -> None:
        """Clear all registered items (mainly for testing)."""
        self._items.clear()
        log.info("registry.cleared", registry=self.name)

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"<Registry({self.name}): {len(self)} items>"


# Module-level typed registry instances — registered once in lifespan, resolved in dependencies.
db_registry: Registry[DatabaseSession] = Registry("Database")