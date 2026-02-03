"""
Subtitle Effects Module

Provides animation and visual effects utilities for styled subtitles.
"""

from typing import Tuple
import re


def hex_to_ass_color(hex_color: str) -> str:
    """
    Convert hex color to ASS color format.
    
    ASS uses BGR format with alpha: &HAABBGGRR
    Hex input: #RRGGBB or #RRGGBBAA
    """
    hex_color = hex_color.lstrip('#')
    
    if len(hex_color) == 6:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = 0
    elif len(hex_color) == 8:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        a = 255 - int(hex_color[6:8], 16)  # ASS alpha is inverted (0 = opaque, 255 = transparent)
    else:
        raise ValueError(f"Invalid hex color: {hex_color}")
    
    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16)
    )


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color."""
    return f"#{r:02X}{g:02X}{b:02X}"


def get_alignment_code(position: str, align: str) -> int:
    """
    Get ASS alignment numpad code.
    
    ASS uses numpad-style positioning:
    7 8 9 (top)
    4 5 6 (middle)
    1 2 3 (bottom)
    """
    align_map = {
        "left": 0,
        "center": 1,
        "right": 2,
    }
    
    pos_base = {
        "bottom": 1,
        "center": 4,
        "top": 7,
        "custom": 1,  # Default to bottom for custom
    }
    
    return pos_base.get(position, 1) + align_map.get(align, 1)


def get_fade_effect(entry_ms: int = 200, exit_ms: int = 200) -> str:
    """Generate ASS fade effect tag."""
    return f"\\fad({entry_ms},{exit_ms})"


def get_move_effect(x1: int, y1: int, x2: int, y2: int, t1: int = 0, t2: int = 200) -> str:
    """Generate ASS move effect tag."""
    return f"\\move({x1},{y1},{x2},{y2},{t1},{t2})"


def get_scale_effect(start_scale: int = 50, end_scale: int = 100, t1: int = 0, t2: int = 200) -> str:
    """Generate ASS transform with scale effect."""
    return f"\\t({t1},{t2},\\fscx{end_scale}\\fscy{end_scale})\\fscx{start_scale}\\fscy{start_scale}"


def get_pop_in_effect(duration: int = 200) -> str:
    """Generate pop-in animation effect (scale from small to normal)."""
    return f"\\fscx50\\fscy50\\t(0,{duration},\\fscx100\\fscy100)"


def get_pop_out_effect(start_time: int, duration: int = 200) -> str:
    """Generate pop-out animation effect (scale from normal to small)."""
    return f"\\t({start_time},{start_time + duration},\\fscx50\\fscy50\\alpha&HFF&)"


def get_slide_up_effect(offset: int = 50, duration: int = 200) -> str:
    """Generate slide-up entry effect."""
    return f"\\move({{x}},{{y+{offset}}},{{x}},{{y}},0,{duration})"


def get_slide_down_effect(offset: int = 50, duration: int = 200) -> str:
    """Generate slide-down entry effect."""
    return f"\\move({{x}},{{y-{offset}}},{{x}},{{y}},0,{duration})"


def get_bounce_effect(duration: int = 300) -> str:
    """Generate bounce animation effect."""
    # Bounce is approximated with scale transforms
    t1 = duration // 3
    t2 = (duration * 2) // 3
    return (
        f"\\fscx80\\fscy80"
        f"\\t(0,{t1},\\fscx110\\fscy110)"
        f"\\t({t1},{t2},\\fscx95\\fscy95)"
        f"\\t({t2},{duration},\\fscx100\\fscy100)"
    )


def get_entry_effect(effect_name: str, duration: int = 200) -> str:
    """Get entry animation effect by name."""
    effects = {
        "none": "",
        "fade": get_fade_effect(duration, 0),
        "pop": get_pop_in_effect(duration),
        "slide_up": f"\\fad({duration},0)",  # Simplified, actual slide needs position
        "slide_down": f"\\fad({duration},0)",  # Simplified
        "bounce": get_bounce_effect(duration),
    }
    return effects.get(effect_name, "")


def get_exit_effect(effect_name: str, duration: int = 200, total_duration: int = 1000) -> str:
    """Get exit animation effect by name."""
    start = total_duration - duration
    
    effects = {
        "none": "",
        "fade": get_fade_effect(0, duration),
        "pop": get_pop_out_effect(start, duration),
        "slide_up": f"\\fad(0,{duration})",
        "slide_down": f"\\fad(0,{duration})",
        "bounce": f"\\fad(0,{duration})",
    }
    return effects.get(effect_name, "")


def get_karaoke_tag(word_duration_cs: int) -> str:
    """
    Generate ASS karaoke tag for word timing.
    
    Args:
        word_duration_cs: Word duration in centiseconds (1/100 second)
    """
    return f"\\k{word_duration_cs}"


def get_karaoke_fill_tag(word_duration_cs: int) -> str:
    """
    Generate ASS karaoke fill tag (smooth fill effect).
    
    Args:
        word_duration_cs: Word duration in centiseconds
    """
    return f"\\kf{word_duration_cs}"


def get_highlight_style(style: str, highlight_color: str) -> str:
    """
    Generate ASS override tags for word highlight style.
    
    Args:
        style: Highlight style (color, background, scale, underline, glow)
        highlight_color: Hex color for highlight
    """
    ass_color = hex_to_ass_color(highlight_color)
    
    styles = {
        "color": f"\\c{ass_color}",
        "background": f"\\3c{ass_color}\\bord4",
        "scale": f"\\c{ass_color}\\fscx110\\fscy110",
        "underline": f"\\c{ass_color}\\u1",
        "glow": f"\\c{ass_color}\\blur2",
    }
    
    return styles.get(style, f"\\c{ass_color}")


def get_reset_style() -> str:
    """Get ASS tag to reset style overrides."""
    return "\\r"


def format_time_ass(seconds: float) -> str:
    """
    Format time in ASS format: H:MM:SS.cc (centiseconds).
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def calculate_word_timings(segment: dict) -> list:
    """
    Calculate word-level timings from a Whisper segment.
    
    If word-level timestamps are available, use them.
    Otherwise, estimate based on character count.
    
    Returns list of dicts with 'word', 'start', 'end' keys.
    """
    # Check if word-level timestamps are available (Whisper large-v2+)
    if "words" in segment:
        return [
            {
                "word": w.get("word", "").strip(),
                "start": w.get("start", 0),
                "end": w.get("end", 0),
            }
            for w in segment["words"]
            if w.get("word", "").strip()
        ]
    
    # Estimate word timings based on text
    text = segment.get("text", "").strip()
    words = text.split()
    
    if not words:
        return []
    
    segment_start = segment.get("start", 0)
    segment_end = segment.get("end", 0)
    segment_duration = segment_end - segment_start
    
    # Calculate total character count (weighted by word length)
    total_chars = sum(len(w) for w in words)
    
    word_timings = []
    current_time = segment_start
    
    for word in words:
        # Estimate duration based on word length proportion
        word_duration = (len(word) / total_chars) * segment_duration if total_chars > 0 else segment_duration / len(words)
        
        word_timings.append({
            "word": word,
            "start": current_time,
            "end": current_time + word_duration,
        })
        
        current_time += word_duration
    
    return word_timings


def chunk_words(words: list, max_words: int = 5) -> list:
    """
    Split words into chunks based on max words per line.
    
    Returns list of word groups, each group is a list of word dicts.
    """
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        
        if len(current_chunk) >= max_words:
            chunks.append(current_chunk)
            current_chunk = []
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
