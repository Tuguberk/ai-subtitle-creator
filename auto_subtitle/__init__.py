"""
Auto Subtitle - Automatic subtitle generation with advanced theming

This package provides tools for automatically transcribing video audio
using OpenAI's Whisper and generating styled subtitles with customizable
themes, word-level highlighting, and animations.
"""

from .theme_config import SubtitleThemeConfig, load_theme
from .subtitle_renderer import SubtitleRenderer, create_styled_subtitles
from .effects import (
    hex_to_ass_color,
    calculate_word_timings,
    chunk_words,
    get_entry_effect,
    get_exit_effect,
)

__all__ = [
    "SubtitleThemeConfig",
    "load_theme",
    "SubtitleRenderer",
    "create_styled_subtitles",
    "hex_to_ass_color",
    "calculate_word_timings",
    "chunk_words",
    "get_entry_effect",
    "get_exit_effect",
]
