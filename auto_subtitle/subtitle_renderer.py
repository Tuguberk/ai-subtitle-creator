"""
Subtitle Renderer Module

Generates styled ASS (Advanced SubStation Alpha) subtitles with
word-level karaoke highlighting and animations.
"""

import os
from typing import List, Optional
from .theme_config import SubtitleThemeConfig
from .effects import (
    hex_to_ass_color,
    get_alignment_code,
    get_entry_effect,
    get_exit_effect,
    get_karaoke_tag,
    get_highlight_style,
    get_reset_style,
    format_time_ass,
    calculate_word_timings,
    chunk_words,
)


class SubtitleRenderer:
    """
    Renders styled subtitles in ASS format with advanced features.
    """
    
    def __init__(self, theme: SubtitleThemeConfig, video_width: int = 1080, video_height: int = 1920):
        """
        Initialize the subtitle renderer.
        
        Args:
            theme: Subtitle theme configuration
            video_width: Video width in pixels (default 1080 for vertical reels)
            video_height: Video height in pixels (default 1920 for vertical reels)
        """
        self.theme = theme
        self.video_width = video_width
        self.video_height = video_height
    
    def generate_ass_header(self) -> str:
        """Generate ASS file header with script info and styles."""
        # Calculate position based on layout
        margin_v = self.theme.layout.margin_y
        if self.theme.layout.position == "top":
            margin_v = self.theme.layout.margin_y
        elif self.theme.layout.position == "center":
            margin_v = (self.video_height // 2) - 100
        elif self.theme.layout.custom_y is not None:
            margin_v = int(self.video_height * self.theme.layout.custom_y / 100)
        
        alignment = get_alignment_code(
            self.theme.layout.position, 
            self.theme.layout.alignment
        )
        
        # Convert colors
        primary_color = hex_to_ass_color(self.theme.colors.primary)
        secondary_color = hex_to_ass_color(self.theme.colors.highlight)
        outline_color = hex_to_ass_color(self.theme.colors.outline)
        back_color = hex_to_ass_color(self.theme.colors.background)
        
        # Font styling
        bold = -1 if self.theme.font.weight == "bold" else 0
        italic = -1 if self.theme.font.style == "italic" else 0
        
        # Outline and shadow
        outline_width = self.theme.effects.outline.width if self.theme.effects.outline.enabled else 0
        shadow_depth = self.theme.effects.shadow.offset_x if self.theme.effects.shadow.enabled else 0
        
        # Border style: 1 = outline + shadow, 3 = opaque box, 4 = special
        border_style = 3 if self.theme.background.enabled and self.theme.background.style == "single" else 1
        
        header = f"""[Script Info]
Title: {self.theme.name}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {self.video_width}
PlayResY: {self.video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.theme.font.family},{self.theme.font.size},{primary_color},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,{border_style},{outline_width},{shadow_depth},{alignment},{self.theme.layout.margin_x},{self.theme.layout.margin_x},{margin_v},1
Style: Highlight,{self.theme.font.family},{self.theme.font.size},{hex_to_ass_color(self.theme.colors.highlight)},{secondary_color},{outline_color},{back_color},{bold},{italic},0,0,100,100,0,0,{border_style},{outline_width},{shadow_depth},{alignment},{self.theme.layout.margin_x},{self.theme.layout.margin_x},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        return header
    
    def render_segment_simple(self, segment: dict) -> str:
        """
        Render a simple subtitle segment without word-level highlighting.
        """
        start = format_time_ass(segment.get("start", 0))
        end = format_time_ass(segment.get("end", 0))
        text = segment.get("text", "").strip()
        
        # Add animation effects
        effects = ""
        duration_ms = int((segment.get("end", 0) - segment.get("start", 0)) * 1000)
        
        if self.theme.animation.entry != "none":
            effects += get_entry_effect(self.theme.animation.entry, self.theme.animation.duration)
        
        if self.theme.animation.exit != "none":
            effects += get_exit_effect(self.theme.animation.exit, self.theme.animation.duration, duration_ms)
        
        if effects:
            text = "{" + effects + "}" + text
        
        return f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"
    
    def render_segment_karaoke(self, segment: dict) -> str:
        """
        Render a subtitle segment with word-level karaoke highlighting.
        """
        word_timings = calculate_word_timings(segment)
        
        if not word_timings:
            return self.render_segment_simple(segment)
        
        # Chunk words based on max words per line
        chunks = chunk_words(word_timings, self.theme.layout.max_words_per_line)
        
        lines = []
        
        for chunk in chunks:
            if not chunk:
                continue
            
            chunk_start = chunk[0]["start"]
            chunk_end = chunk[-1]["end"]
            
            start_ass = format_time_ass(chunk_start)
            end_ass = format_time_ass(chunk_end)
            
            # Build karaoke text with timing tags
            text_parts = []
            duration_ms = int((chunk_end - chunk_start) * 1000)
            
            # Add entry animation
            entry_effect = ""
            if self.theme.animation.entry != "none":
                entry_effect = get_entry_effect(self.theme.animation.entry, self.theme.animation.duration)
            
            exit_effect = ""
            if self.theme.animation.exit != "none":
                exit_effect = get_exit_effect(self.theme.animation.exit, self.theme.animation.duration, duration_ms)
            
            preamble = ""
            if entry_effect or exit_effect:
                preamble = "{" + entry_effect + exit_effect + "}"
            
            for i, word_info in enumerate(chunk):
                word = word_info["word"]
                
                if self.theme.highlight.enabled:
                    # Calculate relative timing within the chunk (in milliseconds)
                    word_start_rel = int((word_info["start"] - chunk_start) * 1000)
                    word_end_rel = int((word_info["end"] - chunk_start) * 1000)
                    
                    # Get colors
                    primary_color = hex_to_ass_color(self.theme.colors.primary)
                    highlight_color = hex_to_ass_color(self.theme.colors.highlight)
                    
                    # Color transitions:
                    # - Start with primary color (white) - word hasn't been spoken yet
                    # - At word start: instantly transition to highlight (gold) - currently speaking
                    # - At word end: instantly transition back to primary (white) - already spoken
                    color_tags = f"\\c{primary_color}\\t({word_start_rel},{word_start_rel},\\c{highlight_color})\\t({word_end_rel},{word_end_rel},\\c{primary_color})"
                    text_parts.append("{" + color_tags + "}" + word)
                else:
                    text_parts.append(word)
            
            text = preamble + " ".join(text_parts)
            lines.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}\n")
        
        return "".join(lines)
    
    def render_segment_per_word_background(self, segment: dict) -> str:
        """
        Render subtitle with per-word background boxes.
        Each word gets its own dialogue line with individual styling.
        """
        word_timings = calculate_word_timings(segment)
        
        if not word_timings:
            return self.render_segment_simple(segment)
        
        chunks = chunk_words(word_timings, self.theme.layout.max_words_per_line)
        lines = []
        
        for chunk in chunks:
            if not chunk:
                continue
            
            chunk_start = chunk[0]["start"]
            chunk_end = chunk[-1]["end"]
            
            start_ass = format_time_ass(chunk_start)
            end_ass = format_time_ass(chunk_end)
            
            # Build combined text with per-word color transitions
            text_parts = []
            
            for i, word_info in enumerate(chunk):
                word = word_info["word"]
                word_start = word_info["start"]
                word_end = word_info["end"]
                
                # Determine if this word is currently being spoken
                highlight_color = hex_to_ass_color(self.theme.colors.highlight)
                primary_color = hex_to_ass_color(self.theme.colors.primary)
                
                duration_ms = int((chunk_end - chunk_start) * 1000)
                word_start_rel = int((word_start - chunk_start) * 1000)
                word_end_rel = int((word_end - chunk_start) * 1000)
                
                # Animate color change when word is spoken (single inline tag set)
                # Start primary -> transition to highlight when spoken -> back to primary after
                color_tags = f"\\c{primary_color}\\t({word_start_rel},{word_start_rel + 50},\\c{highlight_color})\\t({word_end_rel},{word_end_rel + 50},\\c{primary_color})"
                
                text_parts.append("{" + color_tags + "}" + word)
            
            # Entry/exit animation for entire chunk
            preamble = ""
            if self.theme.animation.entry != "none":
                preamble += f"\\fad({self.theme.animation.duration},0)"
            if self.theme.animation.exit != "none":
                preamble += f"\\fad(0,{self.theme.animation.duration})"
            
            if preamble:
                preamble = "{" + preamble + "}"
            
            # Combine all words into single dialogue line
            text = preamble + " ".join(text_parts)
            lines.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}\n")
        
        return "".join(lines)
    
    def render_segments(self, segments: List[dict]) -> str:
        """
        Render all segments into a complete ASS subtitle file.
        
        Args:
            segments: List of Whisper transcription segments
            
        Returns:
            Complete ASS file content as string
        """
        ass_content = self.generate_ass_header()
        
        for segment in segments:
            if self.theme.background.style == "per_word":
                ass_content += self.render_segment_per_word_background(segment)
            elif self.theme.highlight.enabled:
                ass_content += self.render_segment_karaoke(segment)
            else:
                ass_content += self.render_segment_simple(segment)
        
        return ass_content
    
    def render_to_file(self, segments: List[dict], output_path: str) -> str:
        """
        Render segments and save to an ASS file.
        
        Args:
            segments: List of Whisper transcription segments
            output_path: Path to save the ASS file
            
        Returns:
            Path to the saved file
        """
        ass_content = self.render_segments(segments)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        return output_path


def create_styled_subtitles(
    segments: List[dict],
    output_path: str,
    theme: Optional[SubtitleThemeConfig] = None,
    video_width: int = 1080,
    video_height: int = 1920,
) -> str:
    """
    Convenience function to create styled subtitles from segments.
    
    Args:
        segments: Whisper transcription segments
        output_path: Path for output ASS file
        theme: Optional theme config (uses default if not provided)
        video_width: Video width in pixels
        video_height: Video height in pixels
        
    Returns:
        Path to the created subtitle file
    """
    if theme is None:
        theme = SubtitleThemeConfig()
    
    renderer = SubtitleRenderer(theme, video_width, video_height)
    return renderer.render_to_file(segments, output_path)
