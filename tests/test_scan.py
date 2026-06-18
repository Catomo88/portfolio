import json
from pathlib import Path
import scan

def _make_sources(tmp_path):
    cc = tmp_path / "cc"; cw = tmp_path / "cw"
    (cc / "Alpha").mkdir(parents=True); (cc / "Portfolio").mkdir()
    (cw / "Beta").mkdir(parents=True)
    (cc / "notafolder.txt").write_text("x", encoding="utf-8")
    return {
        "sources": [
            {"path": str(cc), "tool": "Claude Code"},
            {"path": str(cw), "tool": "Cowork"},
        ],
        "exclude": ["Portfolio"],
        "overrides": {"Beta": {"display_name": "베타"}},
    }

def test_discover_projects_lists_dirs_applies_exclude_and_tool(tmp_path):
    config = _make_sources(tmp_path)
    found = scan.discover_projects(config)
    names = {p["name"]: p for p in found}
    assert set(names) == {"Alpha", "Beta"}          # Portfolio excluded, txt ignored
    assert names["Alpha"]["tool"] == "Claude Code"
    assert names["Beta"]["tool"] == "Cowork"
    assert names["Beta"]["override"] == {"display_name": "베타"}
