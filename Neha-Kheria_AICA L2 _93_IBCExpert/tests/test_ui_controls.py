from pathlib import Path
import re

TEMPLATES = Path(__file__).resolve().parents[1] / "app" / "web" / "templates"
APPLICATION = Path(__file__).resolve().parents[1] / "app" / "web" / "application.py"


def test_no_placeholder_or_dead_visible_controls():
    text = "\n".join(p.read_text(encoding="utf-8") for p in TEMPLATES.glob("*.html"))
    lowered = text.lower()
    for forbidden in ('href="#"', 'action="#"', 'javascript:void', 'coming soon', 'not implemented'):
        assert forbidden not in lowered


def test_literal_form_actions_have_server_route():
    app_source = APPLICATION.read_text(encoding="utf-8")
    route_paths = set(re.findall(r'@app\.(?:get|post|put|delete|patch)\("([^"]+)"', app_source))
    problems = []
    for path in TEMPLATES.glob("*.html"):
        html = path.read_text(encoding="utf-8")
        for action in re.findall(r'<form[^>]+action="([^"{]+)"', html):
            if action and action not in route_paths:
                problems.append((path.name, action))
    assert not problems
