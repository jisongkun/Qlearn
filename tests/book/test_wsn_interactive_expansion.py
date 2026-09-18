from __future__ import annotations

from deeptutor.agents.visualize.utils import has_interactive_html_behavior
from scripts.expand_wsn_interactives import LABS, PLACEMENTS, split_section, widget


def test_every_theory_chapter_has_five_anchored_expansion_labs() -> None:
    assert len(LABS) == 12
    assert set(LABS) == set(PLACEMENTS)
    assert sum(len(labs) for labs in LABS.values()) == 60
    for title, labs in LABS.items():
        slugs = [lab.slug for lab in labs]
        assert len(slugs) == 5
        assert len(set(slugs)) == 5
        assert set(slugs) == set(PLACEMENTS[title])
        assert len(set(PLACEMENTS[title].values())) == 5


def test_every_expansion_widget_is_self_contained_and_operable() -> None:
    for labs in LABS.values():
        for lab in labs:
            source = widget(lab)
            assert has_interactive_html_behavior(source)
            assert "window.__QLEARN_INTERACTIVE_READY__=true" in source
            assert "<script src=" not in source
            assert "<link rel=" not in source
            assert source.count('type="range"') == 2
            assert "addEventListener('input',update)" in source


def test_section_split_preserves_prose_order_and_framing() -> None:
    block = {
        "id": "blk_section",
        "type": "section",
        "params": {"focus": "original", "role": "core", "target_words": 600},
        "payload": {
            "intro": "intro",
            "subsections": [
                {"heading": "A", "body": "body A", "target_words": 200},
                {"heading": "B", "body": "body B", "target_words": 300},
            ],
            "key_takeaway": "takeaway",
        },
        "metadata": {},
    }
    fragments = split_section(block)
    assert [item["payload"]["subsections"][0]["body"] for item in fragments] == [
        "body A",
        "body B",
    ]
    assert fragments[0]["payload"]["intro"] == "intro"
    assert fragments[1]["payload"]["intro"] == ""
    assert fragments[0]["payload"]["key_takeaway"] == ""
    assert fragments[1]["payload"]["key_takeaway"] == "takeaway"
    assert fragments[0]["id"] == "blk_section"
    assert fragments[1]["id"] == "blk_section_wsnpart_02"
