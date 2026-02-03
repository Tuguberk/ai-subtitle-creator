"""
Whisper model management for Auto Subtitle Editor.
Handles model downloading, checking, and loading.
"""

import os
import whisper
from typing import Optional, Callable
from .config import get_config, Config


class ModelManager:
    """Manage Whisper model downloads and selection."""
    
    def __init__(self):
        self.config = get_config()
        self._loaded_model = None
        self._loaded_model_name = None
    
    @staticmethod
    def get_available_models() -> dict:
        """Get all available Whisper models with info."""
        return Config.WHISPER_MODELS
    
    def get_downloaded_models(self) -> list:
        """Get list of downloaded model names."""
        return self.config.downloaded_models
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """Check if a model has been downloaded."""
        # Check config first
        if model_name in self.config.downloaded_models:
            return True
        
        # Try to verify by checking if whisper can load it from cache
        try:
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
            model_file = f"{model_name}.pt"
            return os.path.exists(os.path.join(cache_dir, model_file))
        except Exception:
            return False
    
    def download_model(
        self, 
        model_name: str, 
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Download a Whisper model.
        
        Args:
            model_name: Name of model to download (tiny, base, small, medium, large)
            progress_callback: Optional callback for status updates
        
        Returns:
            True if successful, False otherwise
        """
        if model_name not in Config.WHISPER_MODELS:
            return False
        
        try:
            if progress_callback:
                progress_callback(f"{model_name} modeli indiriliyor...")
            
            # This will download the model if not cached
            whisper.load_model(model_name)
            
            # Mark as downloaded in config
            self.config.add_downloaded_model(model_name)
            
            if progress_callback:
                progress_callback(f"{model_name} modeli başarıyla indirildi!")
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Hata: {str(e)}")
            return False
    
    def get_model(self, model_name: Optional[str] = None):
        """
        Get a loaded Whisper model.
        
        Args:
            model_name: Model to load. If None, uses selected model from config.
        
        Returns:
            Loaded whisper model
        """
        if model_name is None:
            model_name = self.config.selected_model
        
        if model_name is None:
            raise ValueError("No model selected. Please select a model first.")
        
        # Return cached model if already loaded
        if self._loaded_model is not None and self._loaded_model_name == model_name:
            return self._loaded_model
        
        # Load and cache the model
        self._loaded_model = whisper.load_model(model_name)
        self._loaded_model_name = model_name
        
        return self._loaded_model
    
    def select_model(self, model_name: str):
        """Select a model as the active model."""
        self.config.selected_model = model_name
    
    def get_selected_model(self) -> Optional[str]:
        """Get currently selected model name."""
        return self.config.selected_model
    
    def check_and_update_downloaded_models(self):
        """Scan for downloaded models and update config."""
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
        
        if not os.path.exists(cache_dir):
            return
        
        for model_name in Config.WHISPER_MODELS.keys():
            model_file = f"{model_name}.pt"
            if os.path.exists(os.path.join(cache_dir, model_file)):
                self.config.add_downloaded_model(model_name)


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
