from __future__ import annotations

import json
from pathlib import Path

from scripts.add_wsn_mixed_activities import (
    PACKS,
    Classify,
    Flash,
    Match,
    Quiz,
    Sequence,
    apply,
    classification_widget,
    matching_widget,
    sequence_widget,
)
from scripts.expand_wsn_interactives import PLACEMENTS


def _section(index: int, heading: str) -> dict:
    return {
        "id": f"section_{index}",
        "type": "section",
        "status": "ready",
        "title": heading,
        "params": {},
        "payload": {
            "intro": "",
            "subsections": [{"heading": heading, "body": f"正文 {heading}"}],
            "key_takeaway": "",
        },
        "source_anchors": [],
        "metadata": {},
        "error": "",
    }


def _book(tmp_path: Path) -> Path:
    root = tmp_path / "book"
    pages = root / "pages"
    pages.mkdir(parents=True)
    chapters = []
    for order, (title, placements) in enumerate(PLACEMENTS.items(), 1):
        page_id = f"page_{order:02d}"
        chapters.append(
            {
                "id": f"chapter_{order:02d}",
                "title": title,
                "summary": f"{title}摘要",
                "learning_objectives": ["理解关键概念"],
                "page_ids": [page_id],
                "order": order,
            }
        )
        blocks = [_section(index, heading) for index, heading in enumerate(placements.values(), 1)]
        (pages / f"{page_id}.json").write_text(
            json.dumps(
                {
                    "id": page_id,
                    "title": title,
                    "order": order,
                    "blocks": blocks,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    (root / "spine.json").write_text(
        json.dumps({"chapters": chapters}, ensure_ascii=False), encoding="utf-8"
    )
    return root


def test_every_chapter_has_five_distinct_reviewed_formats() -> None:
    assert set(PACKS) == set(PLACEMENTS)
    expected = {Quiz, Flash, Classify, Sequence, Match}
    for title, activities in PACKS.items():
        assert len(activities) == 5
        assert {type(activity) for activity in activities} == expected
        assert {activity.slug for activity in activities} == set(PLACEMENTS[title])


def test_html_activities_are_dependency_free_and_offer_click_fallbacks() -> None:
    builders = {
        Classify: classification_widget,
        Sequence: sequence_widget,
        Match: matching_widget,
    }
    for activities in PACKS.values():
        for activity in activities:
            if type(activity) not in builders:
                continue
            source = builders[type(activity)](activity)
            assert 'data-qlearn-interactive="curated-v1"' in source
            assert "addEventListener" in source
            assert 'draggable="true"' in source or isinstance(activity, Match)
            assert 'type="range"' not in source
            assert "<script src=" not in source.lower()
            assert "<link rel=" not in source.lower()
            assert "window.__QLEARN_INTERACTIVE_READY__=true" in source


def test_apply_distributes_exactly_five_activities_per_chapter(tmp_path: Path) -> None:
    root = _book(tmp_path)
    before = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in (root / "pages").glob("*.json")
    }
    actions = apply(root, backup_dir=None, dry_run=True)
    assert len(actions) == 12

    backup = tmp_path / "backup"
    apply(root, backup_dir=backup, dry_run=False)
    for page_path in (root / "pages").glob("*.json"):
        page = json.loads(page_path.read_text(encoding="utf-8"))
        additions = [block for block in page["blocks"] if block["id"].startswith("blk_wsnmix_")]
        assert len(additions) == 5
        assert [block["type"] for block in additions].count("quiz") == 1
        assert [block["type"] for block in additions].count("flash_cards") == 1
        assert [block["type"] for block in additions].count("interactive") == 3
        assert {block["metadata"]["activity_type"] for block in additions} == {
            "quiz",
            "flash",
            "classify",
            "sequence",
            "match",
        }
        quiz = next(block for block in additions if block["type"] == "quiz")
        assert quiz["payload"]["questions"][0]["question_type"] == "multiple_choice"
        original_sections = [
            block for block in before[page_path.name]["blocks"] if block["type"] == "section"
        ]
        current_sections = [block for block in page["blocks"] if block["type"] == "section"]
        assert current_sections == original_sections

    second_backup = tmp_path / "backup2"
    apply(root, backup_dir=second_backup, dry_run=False)
    for page_path in (root / "pages").glob("*.json"):
        page = json.loads(page_path.read_text(encoding="utf-8"))
        assert sum(block["id"].startswith("blk_wsnmix_") for block in page["blocks"]) == 5
