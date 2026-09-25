"""Permission-gated local plugin/event infrastructure for IBC Expert."""
from .manager import EventBus, PluginManager, PluginManifest

__all__ = ["EventBus", "PluginManager", "PluginManifest"]
