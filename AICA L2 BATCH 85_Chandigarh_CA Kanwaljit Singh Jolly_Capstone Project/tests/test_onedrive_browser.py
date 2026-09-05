from pathlib import Path

from api.checker import normalize_onedrive_path, onedrive_path_within_base
from services import onedrive


def test_nested_browser_paths_stay_inside_configured_base():
    assert normalize_onedrive_path(r"Documents\Clients\Acme") == "/Documents/Clients/Acme"
    assert onedrive_path_within_base("/Documents/Clients/Acme/2026", "/Documents/Clients")
    assert onedrive_path_within_base("/documents/clients/acme", "/Documents/Clients")
    assert not onedrive_path_within_base("/Documents/Other", "/Documents/Clients")
    assert not onedrive_path_within_base("/Documents/Clients/../../Secrets", "/Documents/Clients")


def test_graph_child_listing_encodes_paths_and_follows_pagination(monkeypatch):
    pages = iter([
        {"value": [{"name": "First"}], "@odata.nextLink": "https://graph.microsoft.com/page-2"},
        {"value": [{"name": "Second"}]},
    ])
    requested_urls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return next(pages)

    def fake_get(url, headers):
        requested_urls.append(url)
        assert headers["Authorization"] == "Bearer token"
        return Response()

    monkeypatch.setattr(onedrive.requests, "get", fake_get)

    children = onedrive._list_children("token", "/Client Files/A&B")

    assert [item["name"] for item in children] == ["First", "Second"]
    assert requested_urls == [
        "https://graph.microsoft.com/v1.0/me/drive/root:/Client%20Files/A%26B:/children",
        "https://graph.microsoft.com/page-2",
    ]


def test_immediate_folder_items_include_explorer_metadata(monkeypatch):
    monkeypatch.setattr(onedrive, "_list_children", lambda token, path: [
        {
            "name": "Nested",
            "size": 0,
            "folder": {"childCount": 3},
            "lastModifiedDateTime": "2026-08-22T10:00:00Z",
        },
        {
            "name": "input.csv",
            "size": 2048,
            "file": {"mimeType": "text/csv"},
            "lastModifiedDateTime": "2026-08-22T11:00:00Z",
        },
    ])

    items = onedrive.list_onedrive_files("token", "/", recursive=False)

    assert items[0] == {
        "name": "Nested",
        "path": "/Nested",
        "size": 0,
        "isFolder": True,
        "childCount": 3,
        "lastModified": "2026-08-22T10:00:00Z",
    }
    assert items[1]["path"] == "/input.csv"
    assert items[1]["lastModified"] == "2026-08-22T11:00:00Z"


def test_shared_picker_uses_inline_nested_explorer():
    project = Path(__file__).parents[1]
    selector = (project / "static" / "js" / "file-selector.js").read_text(encoding="utf-8")

    assert "drive-explorer-breadcrumbs" in selector
    assert "loadDirectory(button.dataset.openPath)" in selector
    assert "addEventListener('dblclick'" in selector
    assert "-folder-section" not in selector
