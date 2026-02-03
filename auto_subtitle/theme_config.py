"""
Subtitle Theme Configuration Module

Provides theme loading, validation, and management for styled subtitles.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import os
import yaml


@dataclass
class FontConfig:
    """Font configuration for subtitle text."""
    family: str = "Arial"
    size: int = 72
    weight: Literal["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"] = "bold"
    style: Literal["normal", "italic", "oblique"] = "normal"


@dataclass
class ColorConfig:
    """Color configuration for subtitle elements."""
    primary: str = "#FFFFFF"
    highlight: str = "#00FF88"
    background: str = "#000000CC"
    outline: str = "#000000"
    shadow: str = "#00000080"


@dataclass
class HighlightConfig:
    """Word highlighting (karaoke) configuration."""
    enabled: bool = True
    mode: Literal["word", "character", "none"] = "word"
    style: Literal["color", "background", "scale", "underline", "glow"] = "color"
    transition: Literal["instant", "fade", "slide"] = "instant"


@dataclass
class LayoutConfig:
    """Layout and positioning configuration."""
    position: Literal["top", "center", "bottom", "custom"] = "bottom"
    custom_y: Optional[float] = None
    max_words_per_line: int = 5
    alignment: Literal["left", "center", "right"] = "center"
    margin_x: int = 50
    margin_y: int = 100


@dataclass
class BackgroundConfig:
    """Background box styling configuration."""
    enabled: bool = True
    style: Literal["single", "per_word", "none"] = "single"
    padding: int = 20
    border_radius: int = 15
    opacity: float = 0.8


@dataclass
class OutlineEffect:
    """Text outline effect configuration."""
    enabled: bool = True
    width: int = 3


@dataclass
class ShadowEffect:
    """Text shadow effect configuration."""
    enabled: bool = False
    offset_x: int = 4
    offset_y: int = 4
    blur: int = 2


@dataclass
class EffectsConfig:
    """Text effects configuration."""
    outline: OutlineEffect = field(default_factory=OutlineEffect)
    shadow: ShadowEffect = field(default_factory=ShadowEffect)


@dataclass
class AnimationConfig:
    """Animation configuration for subtitle entry/exit."""
    entry: Literal["none", "fade", "pop", "slide_up", "slide_down", "bounce"] = "pop"
    exit: Literal["none", "fade", "pop", "slide_up", "slide_down", "bounce"] = "fade"
    duration: int = 200  # milliseconds
    word_stagger: int = 50  # milliseconds between word animations


@dataclass
class SubtitleThemeConfig:
    """Complete subtitle theme configuration."""
    name: str = "default"
    version: str = "1.0"
    font: FontConfig = field(default_factory=FontConfig)
    colors: ColorConfig = field(default_factory=ColorConfig)
    highlight: HighlightConfig = field(default_factory=HighlightConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    effects: EffectsConfig = field(default_factory=EffectsConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "SubtitleThemeConfig":
        """Load theme configuration from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "SubtitleThemeConfig":
        """Create theme configuration from a dictionary."""
        config = cls()
        
        if data is None:
            return config
            
        config.name = data.get("name", config.name)
        config.version = data.get("version", config.version)
        
        # Parse font config
        if "font" in data:
            font_data = data["font"]
            config.font = FontConfig(
                family=font_data.get("family", config.font.family),
                size=font_data.get("size", config.font.size),
                weight=font_data.get("weight", config.font.weight),
                style=font_data.get("style", config.font.style),
            )
        
        # Parse colors config
        if "colors" in data:
            colors_data = data["colors"]
            config.colors = ColorConfig(
                primary=colors_data.get("primary", config.colors.primary),
                highlight=colors_data.get("highlight", config.colors.highlight),
                background=colors_data.get("background", config.colors.background),
                outline=colors_data.get("outline", config.colors.outline),
                shadow=colors_data.get("shadow", config.colors.shadow),
            )
        
        # Parse highlight config
        if "highlight" in data:
            hl_data = data["highlight"]
            config.highlight = HighlightConfig(
                enabled=hl_data.get("enabled", config.highlight.enabled),
                mode=hl_data.get("mode", config.highlight.mode),
                style=hl_data.get("style", config.highlight.style),
                transition=hl_data.get("transition", config.highlight.transition),
            )
        
        # Parse layout config
        if "layout" in data:
            layout_data = data["layout"]
            config.layout = LayoutConfig(
                position=layout_data.get("position", config.layout.position),
                custom_y=layout_data.get("custom_y", config.layout.custom_y),
                max_words_per_line=layout_data.get("max_words_per_line", config.layout.max_words_per_line),
                alignment=layout_data.get("alignment", config.layout.alignment),
                margin_x=layout_data.get("margin_x", config.layout.margin_x),
                margin_y=layout_data.get("margin_y", config.layout.margin_y),
            )
        
        # Parse background config
        if "background" in data:
            bg_data = data["background"]
            config.background = BackgroundConfig(
                enabled=bg_data.get("enabled", config.background.enabled),
                style=bg_data.get("style", config.background.style),
                padding=bg_data.get("padding", config.background.padding),
                border_radius=bg_data.get("border_radius", config.background.border_radius),
                opacity=bg_data.get("opacity", config.background.opacity),
            )
        
        # Parse effects config
        if "effects" in data:
            effects_data = data["effects"]
            outline_data = effects_data.get("outline", {})
            shadow_data = effects_data.get("shadow", {})
            
            config.effects = EffectsConfig(
                outline=OutlineEffect(
                    enabled=outline_data.get("enabled", config.effects.outline.enabled),
                    width=outline_data.get("width", config.effects.outline.width),
                ),
                shadow=ShadowEffect(
                    enabled=shadow_data.get("enabled", config.effects.shadow.enabled),
                    offset_x=shadow_data.get("offset_x", config.effects.shadow.offset_x),
                    offset_y=shadow_data.get("offset_y", config.effects.shadow.offset_y),
                    blur=shadow_data.get("blur", config.effects.shadow.blur),
                ),
            )
        
        # Parse animation config
        if "animation" in data:
            anim_data = data["animation"]
            config.animation = AnimationConfig(
                entry=anim_data.get("entry", config.animation.entry),
                exit=anim_data.get("exit", config.animation.exit),
                duration=anim_data.get("duration", config.animation.duration),
                word_stagger=anim_data.get("word_stagger", config.animation.word_stagger),
            )
        
        return config

    def to_dict(self) -> dict:
        """Convert theme configuration to a dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "font": {
                "family": self.font.family,
                "size": self.font.size,
                "weight": self.font.weight,
                "style": self.font.style,
            },
            "colors": {
                "primary": self.colors.primary,
                "highlight": self.colors.highlight,
                "background": self.colors.background,
                "outline": self.colors.outline,
                "shadow": self.colors.shadow,
            },
            "highlight": {
                "enabled": self.highlight.enabled,
                "mode": self.highlight.mode,
                "style": self.highlight.style,
                "transition": self.highlight.transition,
            },
            "layout": {
                "position": self.layout.position,
                "custom_y": self.layout.custom_y,
                "max_words_per_line": self.layout.max_words_per_line,
                "alignment": self.layout.alignment,
                "margin_x": self.layout.margin_x,
                "margin_y": self.layout.margin_y,
            },
            "background": {
                "enabled": self.background.enabled,
                "style": self.background.style,
                "padding": self.background.padding,
                "border_radius": self.background.border_radius,
                "opacity": self.background.opacity,
            },
            "effects": {
                "outline": {
                    "enabled": self.effects.outline.enabled,
                    "width": self.effects.outline.width,
                },
                "shadow": {
                    "enabled": self.effects.shadow.enabled,
                    "offset_x": self.effects.shadow.offset_x,
                    "offset_y": self.effects.shadow.offset_y,
                    "blur": self.effects.shadow.blur,
                },
            },
            "animation": {
                "entry": self.animation.entry,
                "exit": self.animation.exit,
                "duration": self.animation.duration,
                "word_stagger": self.animation.word_stagger,
            },
        }

    def to_yaml(self, path: str) -> None:
        """Save theme configuration to a YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def get_theme_path(theme_name: str) -> Optional[str]:
    """Get the path to a built-in theme by name."""
    themes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "themes")
    theme_path = os.path.join(themes_dir, f"{theme_name}.yaml")
    
    if os.path.exists(theme_path):
        return theme_path
    return None


def load_theme(theme_name_or_path: str) -> SubtitleThemeConfig:
    """
    Load a theme by name or path.
    
    Args:
        theme_name_or_path: Either a built-in theme name (e.g., 'karaoke') 
                           or a path to a YAML file.
    
    Returns:
        SubtitleThemeConfig instance.
    """
    # Check if it's a file path
    if os.path.exists(theme_name_or_path):
        return SubtitleThemeConfig.from_yaml(theme_name_or_path)
    
    # Check if it's a built-in theme
    theme_path = get_theme_path(theme_name_or_path)
    if theme_path:
        return SubtitleThemeConfig.from_yaml(theme_path)
    
    # Return default theme
    print(f"Warning: Theme '{theme_name_or_path}' not found. Using default theme.")
    return SubtitleThemeConfig()
