"""
Cross-platform configuration management for Auto Subtitle Editor.
Stores settings in platform-appropriate locations.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any


def get_config_dir() -> Path:
    """Get platform-appropriate config directory."""
    if sys.platform == "win32":
        # Windows: %APPDATA%/AutoSubtitle
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = Path(base) / "AutoSubtitle"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/AutoSubtitle
        config_dir = Path.home() / "Library" / "Application Support" / "AutoSubtitle"
    else:
        # Linux/Unix: ~/.config/auto-subtitle
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        config_dir = Path(xdg_config) / "auto-subtitle"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_models_dir() -> Path:
    """Get directory for storing Whisper models cache info."""
    config_dir = get_config_dir()
    models_dir = config_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


class Config:
    """Application configuration manager."""
    
    CONFIG_FILE = "config.json"
    
    # Available Whisper models with their info
    WHISPER_MODELS = {
        "tiny": {
            "name": "Tiny",
            "size": "39 MB",
            "vram": "~1 GB",
            "description": "En hızlı, düşük doğruluk",
            "speed": "Çok Hızlı"
        },
        "base": {
            "name": "Base", 
            "size": "74 MB",
            "vram": "~1 GB",
            "description": "Hızlı, orta doğruluk",
            "speed": "Hızlı"
        },
        "small": {
            "name": "Small",
            "size": "244 MB",
            "vram": "~2 GB",
            "description": "Dengeli hız ve doğruluk",
            "speed": "Orta"
        },
        "medium": {
            "name": "Medium",
            "size": "769 MB",
            "vram": "~5 GB",
            "description": "İyi doğruluk, daha yavaş",
            "speed": "Yavaş"
        },
        "large": {
            "name": "Large",
            "size": "1.5 GB",
            "vram": "~10 GB",
            "description": "En iyi doğruluk, en yavaş",
            "speed": "Çok Yavaş"
        }
    }
    
    def __init__(self):
        self.config_dir = get_config_dir()
        self.config_path = self.config_dir / self.CONFIG_FILE
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load config from file or return defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Default config
        return {
            "first_run": True,
            "selected_model": None,
            "downloaded_models": [],
            "language": "auto",
            "last_export_path": None
        }
    
    def save(self):
        """Save config to file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    @property
    def is_first_run(self) -> bool:
        """Check if this is the first run."""
        return self._config.get("first_run", True)
    
    def set_first_run_complete(self):
        """Mark first run as complete."""
        self._config["first_run"] = False
        self.save()
    
    @property
    def selected_model(self) -> Optional[str]:
        """Get currently selected Whisper model."""
        return self._config.get("selected_model")
    
    @selected_model.setter
    def selected_model(self, model: str):
        """Set selected Whisper model."""
        self._config["selected_model"] = model
        self.save()
    
    @property
    def downloaded_models(self) -> list:
        """Get list of downloaded models."""
        return self._config.get("downloaded_models", [])
    
    def add_downloaded_model(self, model: str):
        """Add model to downloaded list."""
        if model not in self._config["downloaded_models"]:
            self._config["downloaded_models"].append(model)
            self.save()
    
    def is_model_downloaded(self, model: str) -> bool:
        """Check if a model is downloaded."""
        return model in self.downloaded_models
    
    @property
    def language(self) -> str:
        """Get transcription language."""
        return self._config.get("language", "auto")
    
    @language.setter
    def language(self, lang: str):
        """Set transcription language."""
        self._config["language"] = lang
        self.save()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
