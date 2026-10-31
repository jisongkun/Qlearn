"""Interactive blocks must be real widgets, not fenced prose or static HTML."""

from deeptutor.agents.visualize.utils import (
    has_interactive_html_behavior,
    normalize_html_document,
)
from deeptutor.book.blocks.interactive import build_interactive_prompt


def test_normalize_html_extracts_fenced_document_after_model_preamble() -> None:
    raw = "Here is the widget.\n```html\n<!doctype html><button id='go'>Go</button>\n```"
    assert normalize_html_document(raw) == "<!doctype html><button id='go'>Go</button>"


def test_normalize_html_trims_unfenced_preamble() -> None:
    raw = "下面是结果：\n<!doctype html><html><body>ok</body></html>"
    assert normalize_html_document(raw).startswith("<!doctype html>")


def test_static_html_is_not_claimed_as_interactive() -> None:
    assert not has_interactive_html_behavior("<html><body><p>read only</p></body></html>")
    assert not has_interactive_html_behavior("<html><button>unwired</button></html>")


def test_control_with_event_wiring_is_interactive() -> None:
    source = """<html><body><input id="x"><script>
    document.getElementById('x').addEventListener('input', function () {});
    </script></body></html>"""
    assert has_interactive_html_behavior(source)


def test_native_interactive_prompt_can_be_previewed_without_generation() -> None:
    prompt = build_interactive_prompt(
        language="zh",
        chapter_title="第五章 无线通信基础",
        chapter_summary="理解链路预算。",
        objectives=["解释路径损耗", "计算接收功率"],
        focus="发射功率、路径损耗与链路余量",
        interaction="参数探索",
    )
    assert "第五章 无线通信基础" in prompt.user_input
    assert "发射功率、路径损耗与链路余量" in prompt.user_input
    assert "理解链路预算" in prompt.history_context
    assert "计算接收功率" in prompt.history_context
