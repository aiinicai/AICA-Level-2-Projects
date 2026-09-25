"""Harmless sample plugin. It is registered disabled and only observes local event metadata."""
from .manager import PluginManifest

SAMPLE_PLUGIN = PluginManifest(
    key="sample-local-event-viewer",
    display_name="Sample Local Event Viewer",
    version="1.0",
    permissions=("events.read",),
    description="Harmless sample demonstrating the future plugin boundary. Disabled by default and has no network access.",
)
