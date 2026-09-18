"""Interactive block – self-contained interactive HTML widget.

Wraps :class:`deeptutor.agents.visualize.pipeline.VisualizePipeline` with
``render_mode="html"``. The payload carries an HTML document the frontend
renders in an isolated iframe.

The draft is checked by the deterministic local ``validate_visualization``.
HTML has no repair pass (full single-file documents are too large for a
useful targeted fix), so an unrenderable document raises
``GenerationFailure`` and lets the book engine retry — better than baking a
placeholder page into the book.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from deeptutor.services.keypool import primary_api_key

from ..models import BlockType, SourceAnchor
from ._prompts import get_book_prompt, load_book_prompts
from .base import BlockContext, BlockGenerator, GenerationFailure

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InteractivePrompt:
    """Native prompt inputs used by the visualisation pipeline.

    Keeping this construction pure lets authenticated authoring tools preview
    the exact prompt before generation and lets deterministic curation jobs
    record the same prompt alongside hand-authored HTML.
    """

    user_input: str
    history_context: str


def build_interactive_prompt(
    *,
    language: str,
    chapter_title: str,
    chapter_summary: str = "",
    objectives: list[str] | None = None,
    focus: str = "",
    interaction: str = "interactive",
) -> InteractivePrompt:
    """Render the same native prompt consumed by ``InteractiveGenerator``."""

    prompts = load_book_prompts("interactive", language)
    history_lines: list[str] = []
    if chapter_summary:
        history_lines.append(
            get_book_prompt(prompts, "context_summary")
            .strip()
            .format(chapter_summary=chapter_summary)
        )
    if objectives:
        history_lines.append(get_book_prompt(prompts, "context_objectives").strip())
        history_lines.extend(f"- {objective}" for objective in objectives)
    focus_clause = (
        get_book_prompt(prompts, "focus_clause").rstrip().format(focus=focus) if focus else ""
    )
    user_input = (
        get_book_prompt(prompts, "brief")
        .strip()
        .format(
            interaction=interaction,
            chapter_title=chapter_title,
            focus_clause=focus_clause,
        )
    )
    return InteractivePrompt(user_input=user_input, history_context="\n".join(history_lines))


class InteractiveGenerator(BlockGenerator):
    block_type = BlockType.INTERACTIVE

    async def _generate(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        params = ctx.block.params
        chapter_title = params.get("chapter_title", ctx.chapter.title)
        chapter_summary = params.get("chapter_summary", ctx.chapter.summary)
        objectives = params.get("objectives") or ctx.chapter.learning_objectives
        focus = str(params.get("focus") or "")
        interaction = str(params.get("interaction") or "interactive")
        prompt = build_interactive_prompt(
            language=ctx.language,
            chapter_title=str(chapter_title),
            chapter_summary=str(chapter_summary or ""),
            objectives=[str(objective) for objective in objectives],
            focus=focus,
            interaction=interaction,
        )
        user_input = prompt.user_input
        history_context = prompt.history_context

        try:
            from deeptutor.agents.visualize.pipeline import VisualizePipeline
            from deeptutor.agents.visualize.utils import (
                has_interactive_html_behavior,
                normalize_html_document,
                validate_visualization,
            )
            from deeptutor.services.llm.config import get_llm_config

            llm_config = get_llm_config()
            pipeline = VisualizePipeline(
                api_key=primary_api_key(llm_config.api_key),
                base_url=llm_config.base_url,
                api_version=llm_config.api_version,
                language=ctx.language,
            )
            analysis = await pipeline.run_analysis(
                user_input=user_input,
                history_context=history_context,
                render_mode="html",
            )
            code = await pipeline.run_code_generation(
                user_input=user_input,
                history_context=history_context,
                analysis=analysis,
            )
        except Exception as exc:
            logger.warning(f"InteractiveGenerator failed: {exc}", exc_info=True)
            raise GenerationFailure(f"interactive generation failed: {exc}") from exc

        code = normalize_html_document(code)
        ok, validation_error = validate_visualization(code, "html")
        if not ok:
            raise GenerationFailure(f"interactive html failed validation: {validation_error}")
        if not has_interactive_html_behavior(code):
            raise GenerationFailure(
                "interactive html has no usable controls or event wiring; "
                "a static page cannot be stored as an interactive block"
            )

        return (
            {
                "render_type": "html",
                "code": {"language": "html", "content": code},
                "description": analysis.description,
                "chart_type": analysis.chart_type,
            },
            [],
            {
                "review_changed": False,
                "review_notes": "Passed local validation.",
            },
        )


__all__ = ["InteractiveGenerator", "InteractivePrompt", "build_interactive_prompt"]
