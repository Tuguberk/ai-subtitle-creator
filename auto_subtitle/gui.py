"""
PyQt6 Subtitle Editor GUI

A modern video editing-style interface for auto-subtitle with:
- Video preview with subtitle overlay
- Timeline for subtitle navigation
- Subtitle text editing
- Theme selection
- Export options
"""

import os
import sys
import tempfile
from typing import List, Optional, Dict
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QComboBox, QGroupBox, QSplitter,
    QFileDialog, QProgressBar, QSpinBox, QCheckBox, QFrame,
    QScrollArea, QSizePolicy, QDialog, QDialogButtonBox,
    QFormLayout, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import (
    Qt, QTimer, QUrl, QThread, pyqtSignal, QSize, QRectF
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPixmap, QImage,
    QPainterPath, QAction, QKeySequence, QIcon
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from .styles import DARK_THEME, COLORS
from .theme_config import SubtitleThemeConfig, load_theme, get_theme_path
from .config import get_config, Config
from .model_manager import get_model_manager

def normalize_path(path: str) -> str:
    """
    Normalize a file path for the current operating system.
    Ensures consistent path separators and resolves relative paths.
    Works on Windows, macOS, and Linux.
    """
    import os
    # Normalize the path to use OS-appropriate separators and resolve ../ etc
    normalized = os.path.normpath(path)
    # On Windows, also handle any forward slashes that might be mixed in
    if sys.platform == "win32":
        normalized = normalized.replace("/", os.sep)
    return normalized


def format_ffmpeg_path(path: str) -> str:
    """
    Format a file path for use in FFmpeg filter expressions.
    FFmpeg filters (like 'ass') require special path escaping on Windows:
    - Normalize the path first
    - Convert backslashes to forward slashes
    - Escape the colon after drive letter (C: -> C\\:)
    
    Works on Windows, macOS, and Linux.
    """
    import os
    
    # First normalize the path to resolve any inconsistencies
    path = os.path.normpath(path)
    
    if sys.platform == "win32":
        # On Windows, convert ALL backslashes to forward slashes for FFmpeg
        path = path.replace("\\", "/")
        # Escape the colon after drive letter: C:/... -> C\:/...
        # FFmpeg filter requires the colon to be escaped
        if len(path) >= 2 and path[1] == ":":
            path = path[0] + "\\:" + path[2:]
    
    return path


def get_ffmpeg_path() -> str:
    """
    Get the path to the FFmpeg executable.
    First checks for bundled ffmpeg in the bin folder, then falls back to system PATH.
    Works on Windows, macOS, and Linux.
    """
    import shutil
    
    # Get the directory where the module is located
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check for bundled ffmpeg in bin folder
    if sys.platform == "win32":
        bundled_ffmpeg = os.path.join(module_dir, "bin", "ffmpeg.exe")
    else:
        bundled_ffmpeg = os.path.join(module_dir, "bin", "ffmpeg")
    
    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg
    
    # Fallback to system ffmpeg
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    
    # Last resort - just return "ffmpeg" and hope it's in PATH
    return "ffmpeg"


def get_ffprobe_path() -> str:
    """
    Get the path to the FFprobe executable.
    First checks for bundled ffprobe in the bin folder, then falls back to system PATH.
    Works on Windows, macOS, and Linux.
    """
    import shutil
    
    # Get the directory where the module is located
    module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check for bundled ffprobe in bin folder
    if sys.platform == "win32":
        bundled_ffprobe = os.path.join(module_dir, "bin", "ffprobe.exe")
    else:
        bundled_ffprobe = os.path.join(module_dir, "bin", "ffprobe")
    
    if os.path.exists(bundled_ffprobe):
        return bundled_ffprobe
    
    # Fallback to system ffprobe
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe
    
    # Last resort - just return "ffprobe" and hope it's in PATH
    return "ffprobe"


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    if hasattr(sys, 'frozen'):
        # PyInstaller - in onedir mode resources are next to the executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Development - resources are in the project root
        # this file is in auto_subtitle/, so project root is one level up
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


def probe_video(video_path: str) -> dict:
    """
    Probe a video file to get its metadata using ffprobe.
    Returns a dictionary with video stream information.
    """
    import subprocess
    import json
    
    cmd = [
        get_ffprobe_path(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path
    ]
    
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
        
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise Exception(f"ffprobe failed: {result.stderr}")
    
    return json.loads(result.stdout)


# Cache for hardware encoder detection
_hw_encoder_cache = None

def get_hw_encoder() -> tuple:
    """
    Detect available hardware encoder for FFmpeg.
    Returns a tuple of (encoder_name, extra_args) where:
    - encoder_name: The codec name (e.g., 'h264_nvenc', 'libx264')
    - extra_args: Additional FFmpeg arguments for the encoder
    
    Supports:
    - Windows: NVIDIA NVENC, AMD AMF, Intel QuickSync
    - macOS: Apple VideoToolbox
    - Linux: NVIDIA NVENC, VAAPI, Intel QuickSync
    
    Falls back to libx264 (CPU) if no hardware encoder is available.
    """
    global _hw_encoder_cache
    
    if _hw_encoder_cache is not None:
        return _hw_encoder_cache
    
    import subprocess
    
    # Define encoders to try in order of preference
    if sys.platform == "darwin":
        # macOS - VideoToolbox
        encoders = [
            ("h264_videotoolbox", []),
        ]
    elif sys.platform == "win32":
        # Windows - NVENC, AMF, QuickSync
        encoders = [
            ("h264_nvenc", ["-preset", "p4"]),  # NVIDIA
            ("h264_amf", []),                    # AMD
            ("h264_qsv", []),                    # Intel
        ]
    else:
        # Linux - NVENC, VAAPI, QuickSync
        encoders = [
            ("h264_nvenc", ["-preset", "p4"]),  # NVIDIA
            ("h264_vaapi", ["-vaapi_device", "/dev/dri/renderD128"]),  # AMD/Intel VAAPI
            ("h264_qsv", []),                    # Intel QuickSync
        ]
    
    ffmpeg_path = get_ffmpeg_path()
    
    # Test each encoder
    for encoder, extra_args in encoders:
        try:
            # Try to initialize the encoder with a null input
            cmd = [
                ffmpeg_path,
                "-hide_banner",
                "-f", "lavfi",
                "-i", "nullsrc=s=256x256:d=1",
                "-c:v", encoder,
                "-f", "null",
                "-t", "0.1",
                "-"
            ]
            
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                **kwargs
            )
            
            if result.returncode == 0:
                print(f"GPU encoder detected: {encoder}")
                _hw_encoder_cache = (encoder, extra_args)
                return _hw_encoder_cache
                
        except (subprocess.TimeoutExpired, Exception) as e:
            continue
    
    # Fallback to CPU encoder
    print("No GPU encoder available, using libx264 (CPU)")
    _hw_encoder_cache = ("libx264", ["-preset", "ultrafast"])
    return _hw_encoder_cache


@dataclass
class SubtitleSegment:
    """Represents a single subtitle segment."""
    index: int
    start: float
    end: float
    text: str
    words: Optional[List[Dict]] = None


class TranscriptionWorker(QThread):
    """Worker thread for Whisper transcription."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, video_path: str, model_name: str = "small", language: str = "auto"):
        super().__init__()
        self.video_path = video_path
        self.model_name = model_name
        self.language = language

    def run(self):
        try:
            import whisper
            import subprocess
            
            self.status.emit("Ses çıkarılıyor...")
            self.progress.emit(10)
            
            # Extract audio using subprocess with bundled FFmpeg
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, "temp_audio.wav")
            
            # Build FFmpeg command for audio extraction
            cmd = [
                get_ffmpeg_path(),
                "-y",  # Overwrite output
                "-i", self.video_path,
                "-acodec", "pcm_s16le",
                "-ac", "1",
                "-ar", "16000",
                audio_path
            ]
            
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000
            
            result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
            if result.returncode != 0:
                raise Exception(f"FFmpeg audio extraction failed: {result.stderr}")
            
            self.status.emit("Model yükleniyor...")
            self.progress.emit(20)
            
            # Load model
            model = whisper.load_model(self.model_name)
            
            self.status.emit("Transkripsiyon yapılıyor...")
            self.progress.emit(40)
            
            # Transcribe with word timestamps
            options = {"word_timestamps": True}
            if self.language != "auto":
                options["language"] = self.language
            
            # Load audio to numpy to avoid Whisper calling FFmpeg again (which would open console)
            import wave
            import numpy as np
            
            with wave.open(audio_path, "rb") as wf:
                raw_data = wf.readframes(wf.getnframes())
                # Convert buffer to float32 array normalized to [-1, 1]
                audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            result = model.transcribe(audio_np, **options)
            
            self.progress.emit(90)
            self.status.emit("İşleniyor...")
            
            # Convert to SubtitleSegment list
            segments = []
            for i, seg in enumerate(result["segments"]):
                words = seg.get("words", [])
                segment = SubtitleSegment(
                    index=i,
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                    words=words
                )
                segments.append(segment)
            
            self.progress.emit(100)
            self.finished.emit(segments)
            
        except Exception as e:
            import traceback
            print(f"=== TranscriptionWorker HATA ===")
            print(f"Hata: {str(e)}")
            traceback.print_exc()
            self.error.emit(str(e))


class PreviewRenderWorker(QThread):
    """Worker thread for rendering preview video with subtitles."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)  # Path to rendered preview
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    
    # Class-level counter for unique filenames
    _render_counter = 0

    def __init__(self, video_path: str, segments: List[SubtitleSegment], theme: SubtitleThemeConfig):
        super().__init__()
        self.video_path = video_path
        self.segments = segments
        self.theme = theme
        # Generate unique render ID
        PreviewRenderWorker._render_counter += 1
        self.render_id = PreviewRenderWorker._render_counter

    def run(self):
        try:
            from .subtitle_renderer import SubtitleRenderer
            import subprocess
            
            temp_dir = tempfile.gettempdir()
            ass_path = os.path.join(temp_dir, f"preview_subtitles_{self.render_id}.ass")
            preview_path = os.path.join(temp_dir, f"preview_with_subs_{self.render_id}.mp4")
            
            # 1. Altyazı dosyasını oluştur
            self.status.emit("Altyazılar oluşturuluyor...")
            segments_dict = [{"start": s.start, "end": s.end, "text": s.text, "words": s.words or []} for s in self.segments]
            
            # Get video dimensions using bundled ffprobe
            probe = probe_video(self.video_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            orig_width, orig_height = int(video_info['width']), int(video_info['height'])
            
            # Check for rotation in side_data_list or tags
            rotation = 0
            if 'side_data_list' in video_info:
                for side_data in video_info['side_data_list']:
                    if 'rotation' in side_data:
                        rotation = int(side_data['rotation'])
                        break
            if 'tags' in video_info and 'rotate' in video_info['tags']:
                rotation = int(video_info['tags']['rotate'])
            
            # Swap dimensions if video is rotated 90 or 270 degrees
            if abs(rotation) in [90, 270]:
                orig_width, orig_height = orig_height, orig_width
            
            # Calculate preview dimensions (half size, maintain aspect ratio)
            p_width = (orig_width // 2) & ~1  # Ensure even number
            p_height = (orig_height // 2) & ~1
            
            renderer = SubtitleRenderer(self.theme, p_width, p_height)
            renderer.render_to_file(segments_dict, ass_path)
            
            self.status.emit("Önizleme render ediliyor...")
            
            # 2. Build FFmpeg command manually (bypass ffmpeg-python's over-escaping)
            # Format the ASS path for FFmpeg filter on Windows
            if sys.platform == "win32":
                # On Windows, the ass filter needs the path with forward slashes
                # and the colon after drive letter escaped
                filter_ass_path = ass_path.replace("\\", "/")
                if len(filter_ass_path) >= 2 and filter_ass_path[1] == ":":
                    filter_ass_path = filter_ass_path[0] + "\\:" + filter_ass_path[2:]
            else:
                filter_ass_path = ass_path
            
            # Build base filter string (without format conversion)
            base_filter = f"scale={p_width}:{p_height}:force_original_aspect_ratio=decrease,pad={p_width}:{p_height}:(ow-iw)/2:(oh-ih)/2"
            filter_10bit = f"{base_filter},ass='{filter_ass_path}'"
            
            # For 8-bit conversion, add proper HDR to SDR tone mapping
            # This prevents overexposure and color issues when converting from 10-bit HDR
            hdr_to_sdr = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
            filter_8bit_hdr = f"{base_filter},{hdr_to_sdr},ass='{filter_ass_path}'"
            # Simple 8-bit conversion (for non-HDR content)
            filter_8bit_simple = f"{base_filter},format=yuv420p,ass='{filter_ass_path}'"
            
            # Get hardware encoder if available
            encoder, encoder_args = get_hw_encoder()
            
            def run_ffmpeg(vf_filter, video_encoder, extra_args, desc):
                """Helper to run FFmpeg with given settings"""
                cmd = [
                    get_ffmpeg_path(),
                    "-y",
                    "-i", self.video_path,
                    "-vf", vf_filter,
                    "-c:v", video_encoder,
                ]
                cmd.extend(extra_args)
                cmd.extend(["-r", "24", "-c:a", "aac", preview_path])
                print(f"Trying {desc}: {' '.join(cmd)}")
                kwargs = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = 0x08000000
                    
                return subprocess.run(cmd, capture_output=True, text=True, **kwargs)
            
            result = None
            
            # Encoding fallback chain:
            # 1. GPU 10-bit (original quality)
            # 2. GPU 8-bit with HDR tone mapping
            # 3. GPU 8-bit simple (if zscale not available)
            # 4. CPU with HDR tone mapping
            # 5. CPU simple (last resort)
            
            if encoder != "libx264":
                # Step 1: Try GPU encoder with 10-bit (original quality)
                result = run_ffmpeg(filter_10bit, encoder, encoder_args, f"GPU ({encoder}) 10-bit")
                
                # Step 2: If GPU 10-bit fails, try GPU with 8-bit HDR tone mapping
                if result.returncode != 0:
                    print(f"GPU 10-bit failed, trying GPU 8-bit with HDR tone mapping...")
                    result = run_ffmpeg(filter_8bit_hdr, encoder, encoder_args, f"GPU ({encoder}) 8-bit HDR")
                
                # Step 3: If HDR tone mapping fails (zscale not available), try simple conversion
                if result.returncode != 0:
                    print(f"GPU 8-bit HDR failed, trying GPU 8-bit simple...")
                    result = run_ffmpeg(filter_8bit_simple, encoder, encoder_args, f"GPU ({encoder}) 8-bit simple")
                
                # Step 4: If GPU still fails, try CPU with HDR
                if result.returncode != 0:
                    print(f"GPU failed, trying CPU with HDR tone mapping...")
                    result = run_ffmpeg(filter_8bit_hdr, "libx264", ["-preset", "ultrafast", "-crf", "28"], "CPU HDR")
                
                # Step 5: Last resort - CPU simple
                if result.returncode != 0:
                    print(f"CPU HDR failed, trying CPU simple...")
                    result = run_ffmpeg(filter_8bit_simple, "libx264", ["-preset", "ultrafast", "-crf", "28"], "CPU simple")
            else:
                # CPU only - try HDR first, then simple
                result = run_ffmpeg(filter_8bit_hdr, "libx264", ["-preset", "ultrafast", "-crf", "28"], "CPU HDR")
                if result.returncode != 0:
                    result = run_ffmpeg(filter_8bit_simple, "libx264", ["-preset", "ultrafast", "-crf", "28"], "CPU simple")
            
            if result.returncode != 0:
                print(f"FFmpeg stderr: {result.stderr}")
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            self.status.emit("Önizleme hazır!")
            self.finished.emit(preview_path)
            
        except Exception as e:
            import traceback
            print(f"=== PreviewRenderWorker HATA ===")
            print(f"Hata: {str(e)}")
            traceback.print_exc()
            self.error.emit(str(e))


class VideoPreviewWidget(QWidget):
    """Video player with subtitle overlay."""
    
    position_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_subtitle = ""
        self.theme = SubtitleThemeConfig()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget - main video display with modern styling
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #0a0e1a, stop:1 #050810);
            border-radius: 12px;
        """)
        self.video_widget.setMinimumSize(320, 180)
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        
        # Subtitle overlay label - MUST be child of video_widget to overlay
        self.subtitle_label = QLabel(self.video_widget)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 0.75);
                padding: 12px 24px;
                border-radius: 8px;
            }
        """)
        self.subtitle_label.hide()
        
        layout.addWidget(self.video_widget, stretch=1)
        
        # Media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        # Position tracking
        self.player.positionChanged.connect(self._on_position_changed)
        
        # Install event filter on video widget to handle resize
        self.video_widget.installEventFilter(self)
        
        # Playback controls - modern style
        controls_widget = QWidget()
        controls_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 rgba(17, 22, 49, 0.9), stop:1 rgba(10, 14, 39, 0.95));
            border-top: 1px solid rgba(59, 130, 246, 0.15);
        """)
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setSpacing(12)
        
        # Play/Pause button
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.clicked.connect(self.toggle_play)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setMinimum(0)
        self.seek_slider.sliderMoved.connect(self._on_seek)
        self.player.durationChanged.connect(lambda d: self.seek_slider.setMaximum(d))
        self.player.positionChanged.connect(self._update_slider)
        
        # Auto-update play button based on playback state
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        
        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)
        
        # Volume control
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(
            lambda v: self.audio_output.setVolume(v / 100)
        )
        self.audio_output.setVolume(0.7)
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.seek_slider, stretch=1)
        controls_layout.addWidget(self.time_label)
        controls_layout.addWidget(QLabel("🔊"))
        controls_layout.addWidget(self.volume_slider)
        
        layout.addWidget(controls_widget)
    
    def load_video(self, path: str):
        """Load a video file."""
        self.player.setSource(QUrl.fromLocalFile(path))
        self.play_btn.setText("▶")
    
    def toggle_play(self):
        """Toggle play/pause."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def _on_playback_state_changed(self, state):
        """Update play button based on playback state."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")
    
    def seek_to(self, position_ms: int):
        """Seek to position in milliseconds."""
        self.player.setPosition(position_ms)
    
    def set_subtitle(self, text: str):
        """Update displayed subtitle."""
        self.current_subtitle = text
        if text:
            self.subtitle_label.setText(text)
            self.subtitle_label.adjustSize()
            
            # Position at bottom center of video widget
            widget_width = self.video_widget.width()
            widget_height = self.video_widget.height()
            label_width = min(self.subtitle_label.width(), widget_width - 40)
            label_height = self.subtitle_label.height()
            
            # Ensure label doesn't exceed video width
            if label_width < self.subtitle_label.width():
                self.subtitle_label.setFixedWidth(label_width)
                self.subtitle_label.adjustSize()
                label_height = self.subtitle_label.height()
            
            x = max(20, (widget_width - label_width) // 2)
            y = max(20, widget_height - label_height - 60)
            
            self.subtitle_label.move(x, y)
            self.subtitle_label.raise_()  # Bring to front
            self.subtitle_label.show()
        else:
            self.subtitle_label.hide()
    
    def set_theme(self, theme: SubtitleThemeConfig):
        """Update subtitle styling based on theme."""
        self.theme = theme
        
        # Calculate font size for preview (smaller than export)
        preview_font_size = max(18, theme.font.size // 4)
        
        # Update subtitle label style
        self.subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.primary};
                font-size: {preview_font_size}px;
                font-weight: {'bold' if theme.font.weight == 'bold' else 'normal'};
                font-style: {'italic' if theme.font.style == 'italic' else 'normal'};
                font-family: '{theme.font.family}', Arial, sans-serif;
                background-color: rgba(0, 0, 0, 0.75);
                padding: 12px 24px;
                border-radius: 8px;
            }}
        """)
    
    def _on_position_changed(self, position):
        """Handle position change."""
        self.position_changed.emit(position / 1000.0)
    
    def _on_seek(self, position):
        """Handle seek slider movement."""
        self.player.setPosition(position)
    
    def _update_slider(self, position):
        """Update slider and time label."""
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        
        # Update time label
        current = self._format_time(position)
        total = self._format_time(self.player.duration())
        self.time_label.setText(f"{current} / {total}")
    
    def _format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS."""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def eventFilter(self, obj, event):
        """Handle events from video widget."""
        from PyQt6.QtCore import QEvent
        if obj == self.video_widget and event.type() == QEvent.Type.Resize:
            # Reposition subtitle when video widget resizes
            if self.current_subtitle:
                QTimer.singleShot(10, lambda: self.set_subtitle(self.current_subtitle))
        return super().eventFilter(obj, event)
    
    def resizeEvent(self, event):
        """Handle resize to reposition subtitle."""
        super().resizeEvent(event)
        if self.current_subtitle:
            QTimer.singleShot(10, lambda: self.set_subtitle(self.current_subtitle))


class SubtitleTimelineWidget(QWidget):
    """Timeline widget showing subtitle segments."""
    
    segment_selected = pyqtSignal(int)
    segment_double_clicked = pyqtSignal(int)
    seek_requested = pyqtSignal(float)  # Position in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments: List[SubtitleSegment] = []
        self.duration = 0.0
        self.current_position = 0.0
        self.selected_index = -1
        self.setMinimumHeight(70)
        self.setMaximumHeight(90)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #0d1224, stop:1 #080c18);
            border: 1px solid rgba(59, 130, 246, 0.15);
            border-radius: 8px;
        """)
    
    def set_segments(self, segments: List[SubtitleSegment], duration: float):
        """Set subtitle segments and total duration."""
        self.segments = segments
        self.duration = duration
        self.update()
    
    def set_position(self, position: float):
        """Update current playhead position."""
        self.current_position = position
        self.update()
    
    def select_segment(self, index: int):
        """Select a segment by index."""
        self.selected_index = index
        self.update()
    
    def paintEvent(self, event):
        """Paint the timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Don't fill background - let stylesheet handle it
        
        if self.duration <= 0:
            painter.setPen(QColor(COLORS["text_secondary"]))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Video yükleyin...")
            return
        
        # Timeline track area
        track_y = 30
        track_height = height - 40
        
        # Draw track background - subtle dark
        painter.fillRect(4, track_y, width - 8, track_height, QColor("#060910"))
        
        # Draw segments (no text to avoid overlap)
        for i, seg in enumerate(self.segments):
            x1 = int((seg.start / self.duration) * width)
            x2 = int((seg.end / self.duration) * width)
            seg_width = max(x2 - x1, 4)
            
            # Segment color
            if i == self.selected_index:
                color = QColor(COLORS["accent"])
            else:
                color = QColor(COLORS["background_light"])
            
            # Draw segment rect (no text)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x1, track_y + 5, seg_width, track_height - 10, 3, 3)
        
        # Draw time markers on top
        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(QFont("Arial", 9))
        
        # Start time (0:00)
        painter.drawText(5, 18, "0:00")
        
        # End time (duration)
        end_mins = int(self.duration // 60)
        end_secs = int(self.duration % 60)
        end_str = f"{end_mins}:{end_secs:02d}"
        painter.drawText(width - 35, 18, end_str)
        
        # Draw playhead
        playhead_x = int((self.current_position / self.duration) * width)
        painter.setPen(QPen(QColor(COLORS["accent"]), 2))
        painter.drawLine(playhead_x, 0, playhead_x, height)
        
        # Playhead triangle
        painter.setBrush(QBrush(QColor(COLORS["accent"])))
        path = QPainterPath()
        path.moveTo(playhead_x - 8, 0)
        path.lineTo(playhead_x + 8, 0)
        path.lineTo(playhead_x, 12)
        path.closeSubpath()
        painter.drawPath(path)
    
    def mousePressEvent(self, event):
        """Handle mouse click to seek and select segment."""
        if self.duration <= 0:
            return
        
        click_time = (event.position().x() / self.width()) * self.duration
        
        # Always seek to clicked position
        self.seek_requested.emit(click_time)
        
        # Check if clicking on a segment
        for i, seg in enumerate(self.segments):
            if seg.start <= click_time <= seg.end:
                self.selected_index = i
                self.segment_selected.emit(i)
                self.update()
                return
        
        self.update()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click to seek to segment start."""
        if self.selected_index >= 0 and self.selected_index < len(self.segments):
            seg = self.segments[self.selected_index]
            self.seek_requested.emit(seg.start)


class SubtitleEditorPanel(QWidget):
    """Panel for editing subtitle text and timing."""
    
    subtitle_updated = pyqtSignal(int, str, float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_segment: Optional[SubtitleSegment] = None
        self.current_index = -1
        self.setup_ui()
    
    def setup_ui(self):
        # Set panel background style
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(17, 22, 49, 0.9), stop:1 rgba(10, 14, 39, 0.95));
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Altyazı Düzenleme")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Timing row - compact
        timing_layout = QHBoxLayout()
        timing_layout.setSpacing(8)
        
        timing_layout.addWidget(QLabel("Başlangıç:"))
        self.start_edit = QLineEdit("0:00.000")
        self.start_edit.setFixedWidth(100)
        timing_layout.addWidget(self.start_edit)
        
        timing_layout.addWidget(QLabel("Bitiş:"))
        self.end_edit = QLineEdit("0:00.000")
        self.end_edit.setFixedWidth(100)
        timing_layout.addWidget(self.end_edit)
        
        timing_layout.addStretch()
        layout.addLayout(timing_layout)
        
        # Text editor - shorter
        layout.addWidget(QLabel("Metin:"))
        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(50)
        self.text_edit.setMaximumHeight(80)
        self.text_edit.setPlaceholderText("Altyazı metni...")
        layout.addWidget(self.text_edit)
        
        # Save button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        
        # Connect change signals for all editable fields
        self.text_edit.textChanged.connect(lambda: self.save_btn.setEnabled(True))
        self.start_edit.textChanged.connect(lambda: self.save_btn.setEnabled(True))
        self.end_edit.textChanged.connect(lambda: self.save_btn.setEnabled(True))
    
    def load_segment(self, segment: SubtitleSegment, index: int):
        """Load a segment for editing."""
        self.current_segment = segment
        self.current_index = index
        
        self.start_edit.setText(self._format_time(segment.start))
        self.end_edit.setText(self._format_time(segment.end))
        self.text_edit.setPlainText(segment.text)
        self.save_btn.setEnabled(False)
    
    def clear(self):
        """Clear the editor."""
        self.current_segment = None
        self.current_index = -1
        self.start_edit.setText("00:00.000")
        self.end_edit.setText("00:00.000")
        self.text_edit.clear()
        self.save_btn.setEnabled(False)
    
    def _save_changes(self):
        """Save changes to current segment."""
        if self.current_segment is None:
            return
        
        new_text = self.text_edit.toPlainText()
        new_start = self._parse_time(self.start_edit.text())
        new_end = self._parse_time(self.end_edit.text())
        
        self.subtitle_updated.emit(self.current_index, new_text, new_start, new_end)
        self.save_btn.setEnabled(False)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS.mmm."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{mins:02d}:{secs:02d}.{ms:03d}"
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time string to seconds."""
        try:
            parts = time_str.split(":")
            mins = int(parts[0])
            sec_parts = parts[1].split(".")
            secs = int(sec_parts[0])
            ms = int(sec_parts[1]) if len(sec_parts) > 1 else 0
            return mins * 60 + secs + ms / 1000
        except:
            return 0.0


class ThemePanel(QWidget):
    """Panel for theme selection and settings."""
    
    theme_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.themes = {}
        self.current_theme = None
        self.setup_ui()
        self.load_themes()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Title
        title = QLabel("Tema")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Theme list - show more themes
        self.theme_list = QListWidget()
        self.theme_list.setMinimumHeight(100)
        self.theme_list.setMaximumHeight(150)
        self.theme_list.currentRowChanged.connect(self._on_theme_selected)
        layout.addWidget(self.theme_list)
        
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 4, 0, 4)
        settings_layout.setSpacing(4)
        
        # --- Layout Settings ---
        layout_group = QGroupBox("Düzen")
        layout_group_layout = QVBoxLayout(layout_group)
        layout_group_layout.setSpacing(4)
        layout_group_layout.setContentsMargins(6, 10, 6, 6)
        
        # Max words per line
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Kelime/satır:"))
        self.max_words_spin = QSpinBox()
        self.max_words_spin.setRange(1, 10)
        self.max_words_spin.setValue(3)
        self.max_words_spin.valueChanged.connect(self._update_theme_setting)
        row1.addWidget(self.max_words_spin)
        layout_group_layout.addLayout(row1)
        
        # Position
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Konum:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["bottom", "center", "top"])
        self.position_combo.currentTextChanged.connect(self._update_theme_setting)
        row2.addWidget(self.position_combo)
        layout_group_layout.addLayout(row2)
        
        settings_layout.addWidget(layout_group)
        
        # --- Font Settings ---
        font_group = QGroupBox("Yazı Tipi")
        font_group_layout = QVBoxLayout(font_group)
        font_group_layout.setSpacing(4)
        font_group_layout.setContentsMargins(6, 10, 6, 6)
        
        # Font size
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Boyut:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(20, 150)
        self.font_size_spin.setValue(72)
        self.font_size_spin.valueChanged.connect(self._update_theme_setting)
        row3.addWidget(self.font_size_spin)
        font_group_layout.addLayout(row3)
        
        settings_layout.addWidget(font_group)
        
        # --- Color Settings ---
        colors_group = QGroupBox("Renkler")
        colors_group_layout = QVBoxLayout(colors_group)
        colors_group_layout.setSpacing(4)
        colors_group_layout.setContentsMargins(6, 10, 6, 6)
        
        # Primary color
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Ana:"))
        self.primary_color_btn = QPushButton()
        self.primary_color_btn.setFixedSize(60, 24)
        self.primary_color_btn.setStyleSheet("background-color: #FFFFFF; border: 1px solid #333;")
        self.primary_color_btn.clicked.connect(lambda: self._pick_color("primary"))
        row4.addWidget(self.primary_color_btn)
        row4.addStretch()
        colors_group_layout.addLayout(row4)
        
        # Highlight color
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("Vurgu:"))
        self.highlight_color_btn = QPushButton()
        self.highlight_color_btn.setFixedSize(60, 24)
        self.highlight_color_btn.setStyleSheet("background-color: #FFD700; border: 1px solid #333;")
        self.highlight_color_btn.clicked.connect(lambda: self._pick_color("highlight"))
        row5.addWidget(self.highlight_color_btn)
        row5.addStretch()
        colors_group_layout.addLayout(row5)
        
        settings_layout.addWidget(colors_group)
        
        # --- Effects Settings ---
        effects_group = QGroupBox("Efektler")
        effects_group_layout = QVBoxLayout(effects_group)
        effects_group_layout.setSpacing(8)
        effects_group_layout.setContentsMargins(8, 14, 8, 8)
        
        # Highlight enabled
        self.highlight_check = QCheckBox("Kelime Vurgulama")
        self.highlight_check.setChecked(True)
        self.highlight_check.stateChanged.connect(self._update_theme_setting)
        effects_group_layout.addWidget(self.highlight_check)
        
        # Outline enabled
        self.outline_check = QCheckBox("Dış Çizgi")
        self.outline_check.setChecked(True)
        self.outline_check.stateChanged.connect(self._update_theme_setting)
        effects_group_layout.addWidget(self.outline_check)
        
        # Shadow enabled
        self.shadow_check = QCheckBox("Gölge")
        self.shadow_check.setChecked(True)
        self.shadow_check.stateChanged.connect(self._update_theme_setting)
        effects_group_layout.addWidget(self.shadow_check)
        
        settings_layout.addWidget(effects_group)
        
        # --- Animation Settings ---
        anim_group = QGroupBox("Animasyon")
        anim_group_layout = QVBoxLayout(anim_group)
        anim_group_layout.setSpacing(4)
        anim_group_layout.setContentsMargins(6, 10, 6, 6)
        
        # Entry animation
        row6 = QHBoxLayout()
        row6.addWidget(QLabel("Giriş:"))
        self.entry_combo = QComboBox()
        self.entry_combo.addItems(["none", "fade", "slide_up", "bounce", "scale"])
        self.entry_combo.currentTextChanged.connect(self._update_theme_setting)
        row6.addWidget(self.entry_combo)
        anim_group_layout.addLayout(row6)
        
        # Exit animation
        row7 = QHBoxLayout()
        row7.addWidget(QLabel("Çıkış:"))
        self.exit_combo = QComboBox()
        self.exit_combo.addItems(["none", "fade", "slide_down", "pop", "scale"])
        self.exit_combo.currentTextChanged.connect(self._update_theme_setting)
        row7.addWidget(self.exit_combo)
        anim_group_layout.addLayout(row7)
        
        settings_layout.addWidget(anim_group)
        settings_layout.addStretch()
        
        scroll.setWidget(settings_widget)
        layout.addWidget(scroll, stretch=1)
        
        # Save theme button
        self.save_theme_btn = QPushButton("💾 Temayı Kaydet")
        self.save_theme_btn.clicked.connect(self._save_theme)
        layout.addWidget(self.save_theme_btn)
    
    def _pick_color(self, color_type: str):
        """Open color picker dialog."""
        from PyQt6.QtWidgets import QColorDialog
        
        current_color = QColor("#FFFFFF")
        if self.current_theme:
            if color_type == "primary":
                current_color = QColor(self.current_theme.colors.primary)
            elif color_type == "highlight":
                current_color = QColor(self.current_theme.colors.highlight)
        
        color = QColorDialog.getColor(current_color, self, "Renk Seç")
        if color.isValid():
            hex_color = color.name().upper()
            if color_type == "primary":
                self.primary_color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #333;")
                if self.current_theme:
                    self.current_theme.colors.primary = hex_color
            elif color_type == "highlight":
                self.highlight_color_btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #333;")
                if self.current_theme:
                    self.current_theme.colors.highlight = hex_color
            
            self._update_theme_setting()
    
    def _save_theme(self):
        """Save current theme as new theme file."""
        from PyQt6.QtWidgets import QInputDialog
        import yaml
        
        if not self.current_theme:
            return
        
        name, ok = QInputDialog.getText(self, "Tema Kaydet", "Yeni tema adı:")
        if ok and name:
            # Clean name for filename
            filename = name.lower().replace(" ", "_")
            themes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "themes")
            filepath = os.path.join(themes_dir, f"{filename}.yaml")
            
            # Build theme dict
            theme_dict = {
                "name": name,
                "version": "1.0",
                "font": {
                    "family": self.current_theme.font.family,
                    "size": self.current_theme.font.size,
                    "weight": self.current_theme.font.weight,
                    "style": self.current_theme.font.style
                },
                "colors": {
                    "primary": self.current_theme.colors.primary,
                    "highlight": self.current_theme.colors.highlight,
                    "background": self.current_theme.colors.background,
                    "outline": self.current_theme.colors.outline,
                    "shadow": self.current_theme.colors.shadow
                },
                "highlight": {
                    "enabled": self.current_theme.highlight.enabled,
                    "mode": self.current_theme.highlight.mode,
                    "style": self.current_theme.highlight.style,
                    "transition": self.current_theme.highlight.transition
                },
                "layout": {
                    "position": self.current_theme.layout.position,
                    "max_words_per_line": self.current_theme.layout.max_words_per_line,
                    "alignment": self.current_theme.layout.alignment,
                    "margin_x": self.current_theme.layout.margin_x,
                    "margin_y": self.current_theme.layout.margin_y
                },
                "effects": {
                    "outline": {
                        "enabled": self.current_theme.effects.outline.enabled,
                        "width": self.current_theme.effects.outline.width
                    },
                    "shadow": {
                        "enabled": self.current_theme.effects.shadow.enabled,
                        "offset_x": self.current_theme.effects.shadow.offset_x,
                        "offset_y": self.current_theme.effects.shadow.offset_y,
                        "blur": self.current_theme.effects.shadow.blur
                    }
                },
                "animation": {
                    "entry": self.current_theme.animation.entry,
                    "exit": self.current_theme.animation.exit,
                    "duration": self.current_theme.animation.duration,
                    "word_stagger": self.current_theme.animation.word_stagger
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(theme_dict, f, allow_unicode=True, default_flow_style=False)
            
            # Reload themes
            self.themes[filename] = load_theme(filepath)
            self.theme_list.addItem(filename)
            
            QMessageBox.information(self, "Başarılı", f"Tema '{name}' kaydedildi!")
    
    def load_themes(self):
        """Load available themes."""
        themes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "themes")
        
        if os.path.exists(themes_dir):
            for filename in os.listdir(themes_dir):
                if filename.endswith(".yaml"):
                    theme_name = filename[:-5]
                    theme_path = os.path.join(themes_dir, filename)
                    self.themes[theme_name] = load_theme(theme_path)
                    self.theme_list.addItem(theme_name)
        
        # Select first theme
        if self.theme_list.count() > 0:
            self.theme_list.setCurrentRow(0)
    
    def _on_theme_selected(self, row: int):
        """Handle theme selection."""
        if row < 0:
            return
        
        theme_name = self.theme_list.item(row).text()
        self.current_theme = self.themes.get(theme_name)
        
        if self.current_theme:
            # Block signals while updating UI
            for widget in [self.max_words_spin, self.position_combo, self.highlight_check,
                          self.font_size_spin, self.outline_check, self.shadow_check,
                          self.entry_combo, self.exit_combo]:
                widget.blockSignals(True)
            
            # Update UI to match theme settings
            self.max_words_spin.setValue(self.current_theme.layout.max_words_per_line)
            self.position_combo.setCurrentText(self.current_theme.layout.position)
            self.highlight_check.setChecked(self.current_theme.highlight.enabled)
            self.font_size_spin.setValue(self.current_theme.font.size)
            self.outline_check.setChecked(self.current_theme.effects.outline.enabled)
            self.shadow_check.setChecked(self.current_theme.effects.shadow.enabled)
            self.entry_combo.setCurrentText(self.current_theme.animation.entry)
            self.exit_combo.setCurrentText(self.current_theme.animation.exit)
            
            # Update color buttons
            self.primary_color_btn.setStyleSheet(
                f"background-color: {self.current_theme.colors.primary}; border: 1px solid #333;")
            self.highlight_color_btn.setStyleSheet(
                f"background-color: {self.current_theme.colors.highlight}; border: 1px solid #333;")
            
            # Unblock signals
            for widget in [self.max_words_spin, self.position_combo, self.highlight_check,
                          self.font_size_spin, self.outline_check, self.shadow_check,
                          self.entry_combo, self.exit_combo]:
                widget.blockSignals(False)
            
            self.theme_changed.emit(self.current_theme)
    
    def _update_theme_setting(self):
        """Update theme settings from UI."""
        if self.current_theme is None:
            return
        
        self.current_theme.layout.max_words_per_line = self.max_words_spin.value()
        self.current_theme.layout.position = self.position_combo.currentText()
        self.current_theme.highlight.enabled = self.highlight_check.isChecked()
        self.current_theme.font.size = self.font_size_spin.value()
        self.current_theme.effects.outline.enabled = self.outline_check.isChecked()
        self.current_theme.effects.shadow.enabled = self.shadow_check.isChecked()
        self.current_theme.animation.entry = self.entry_combo.currentText()
        self.current_theme.animation.exit = self.exit_combo.currentText()
        
        self.theme_changed.emit(self.current_theme)


class ExportDialog(QDialog):
    """Export settings dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Ayarları")
        self.setMinimumWidth(400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Format selection
        format_group = QGroupBox("Çıktı Formatı")
        format_layout = QVBoxLayout(format_group)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Video + Altyazı (MP4)",
            "Sadece SRT",
            "Sadece ASS"
        ])
        format_layout.addWidget(self.format_combo)
        layout.addWidget(format_group)
        
        # Output path
        path_group = QGroupBox("Kayıt Yeri")
        path_layout = QHBoxLayout(path_group)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Kayıt yolunu seçin...")
        path_layout.addWidget(self.path_edit)
        
        browse_btn = QPushButton("Gözat")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        
        layout.addWidget(path_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _browse_path(self):
        """Browse for output path."""
        format_idx = self.format_combo.currentIndex()
        
        if format_idx == 0:
            filter_str = "Video Files (*.mp4)"
            ext = ".mp4"
        elif format_idx == 1:
            filter_str = "SRT Files (*.srt)"
            ext = ".srt"
        else:
            filter_str = "ASS Files (*.ass)"
            ext = ".ass"
        
        path, _ = QFileDialog.getSaveFileName(self, "Kaydet", "", filter_str)
        if path:
            if not path.endswith(ext):
                path += ext
            self.path_edit.setText(path)
    
    def get_settings(self) -> dict:
        """Get export settings."""
        format_map = {0: "mp4", 1: "srt", 2: "ass"}
        return {
            "format": format_map[self.format_combo.currentIndex()],
            "path": self.path_edit.text()
        }


class ModelDownloadWorker(QThread):
    """Worker thread for downloading Whisper models."""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)
    
    def __init__(self, model_name: str, parent=None):
        super().__init__(parent)
        self.model_name = model_name
    
    def run(self):
        try:
            manager = get_model_manager()
            success = manager.download_model(
                self.model_name,
                progress_callback=lambda msg: self.progress.emit(msg)
            )
            self.finished.emit(success)
        except Exception as e:
            self.progress.emit(f"Hata: {str(e)}")
            self.finished.emit(False)


class FirstRunDialog(QDialog):
    """Dialog shown on first run to select Whisper model."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hoş Geldiniz - Model Seçimi")
        self.setMinimumSize(500, 450)
        self.selected_model = None
        self.download_worker = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Welcome message
        welcome = QLabel("🎬 Ai Subtitle Creator'a Hoş Geldiniz!")
        welcome.setObjectName("titleLabel")
        welcome.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)
        
        desc = QLabel(
            "Transkripsiyon için bir Whisper modeli seçin.\n"
            "Daha büyük modeller daha doğru sonuç verir ama daha yavaştır."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Model selection list
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(200)
        
        models = Config.WHISPER_MODELS
        for model_id, info in models.items():
            item = QListWidgetItem(
                f"  {info['name']}  •  {info['size']}  •  {info['speed']}\n"
                f"     {info['description']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, model_id)
            self.model_list.addItem(item)
        
        # Select "small" by default (good balance)
        self.model_list.setCurrentRow(2)
        layout.addWidget(self.model_list)
        
        # Progress area
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #06b6d4;")
        layout.addWidget(self.progress_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.download_btn = QPushButton("📥 İndir ve Başla")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.setFixedWidth(160)
        self.download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self.download_btn)
        
        layout.addLayout(btn_layout)
    
    def _start_download(self):
        item = self.model_list.currentItem()
        if not item:
            return
        
        model_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_model = model_id
        
        self.download_btn.setEnabled(False)
        self.model_list.setEnabled(False)
        self.progress_label.setText(f"{model_id} modeli indiriliyor...")
        
        self.download_worker = ModelDownloadWorker(model_id, self)
        self.download_worker.progress.connect(self._on_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()
    
    def _on_progress(self, message: str):
        self.progress_label.setText(message)
    
    def _on_download_finished(self, success: bool):
        if success:
            config = get_config()
            config.selected_model = self.selected_model
            config.set_first_run_complete()
            self.accept()
        else:
            self.download_btn.setEnabled(True)
            self.model_list.setEnabled(True)
            self.progress_label.setText("İndirme başarısız. Tekrar deneyin.")


class SettingsDialog(QDialog):
    """Settings dialog for managing Whisper models."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setMinimumSize(550, 500)
        self.download_worker = None
        self.config = get_config()
        self.manager = get_model_manager()
        self.setup_ui()
        self.refresh_model_list()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚙️ Ayarlar")
        title.setObjectName("titleLabel")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Model management section
        model_group = QGroupBox("Whisper Modelleri")
        model_layout = QVBoxLayout(model_group)
        
        # Model list
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(180)
        model_layout.addWidget(self.model_list)
        
        # Model action buttons
        btn_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("📥 İndir")
        self.download_btn.clicked.connect(self._download_selected)
        btn_layout.addWidget(self.download_btn)
        
        self.select_btn = QPushButton("✓ Seç")
        self.select_btn.setObjectName("primaryButton")
        self.select_btn.clicked.connect(self._select_model)
        btn_layout.addWidget(self.select_btn)
        
        btn_layout.addStretch()
        model_layout.addLayout(btn_layout)
        
        # Progress
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #06b6d4;")
        model_layout.addWidget(self.progress_label)
        
        layout.addWidget(model_group)
        
        # Language section
        lang_group = QGroupBox("Transkripsiyon Dili")
        lang_layout = QFormLayout(lang_group)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "Otomatik Algıla", "Türkçe", "İngilizce", "Almanca", 
            "Fransızca", "İspanyolca", "İtalyanca", "Portekizce",
            "Rusça", "Japonca", "Korece", "Çince"
        ])
        lang_layout.addRow("Dil:", self.lang_combo)
        
        layout.addWidget(lang_group)
        
        
        # Credit
        credit_label = QLabel('Yapımcı: <a href="https://tuguberk.dev" style="color: #3b82f6;">tuguberk</a>')
        credit_label.setOpenExternalLinks(True)
        credit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit_label.setStyleSheet("margin-top: 10px;")
        layout.addWidget(credit_label)
        
        layout.addStretch()
        
        # Close button
        btn_layout2 = QHBoxLayout()
        btn_layout2.addStretch()
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        btn_layout2.addWidget(close_btn)
        layout.addLayout(btn_layout2)
    
    def refresh_model_list(self):
        """Refresh the model list with download status."""
        self.model_list.clear()
        self.manager.check_and_update_downloaded_models()
        
        models = Config.WHISPER_MODELS
        selected = self.config.selected_model
        
        for model_id, info in models.items():
            is_downloaded = self.manager.is_model_downloaded(model_id)
            is_selected = model_id == selected
            
            status = ""
            if is_selected:
                status = " ✓ [AKTİF]"
            elif is_downloaded:
                status = " ✓ [İNDİRİLDİ]"
            
            item = QListWidgetItem(
                f"  {info['name']}  •  {info['size']}  •  {info['speed']}{status}"
            )
            item.setData(Qt.ItemDataRole.UserRole, model_id)
            
            if is_selected:
                item.setForeground(QColor("#06b6d4"))
            elif is_downloaded:
                item.setForeground(QColor("#22c55e"))
            
            self.model_list.addItem(item)
    
    def _download_selected(self):
        item = self.model_list.currentItem()
        if not item:
            return
        
        model_id = item.data(Qt.ItemDataRole.UserRole)
        
        if self.manager.is_model_downloaded(model_id):
            self.progress_label.setText(f"{model_id} zaten indirilmiş.")
            return
        
        self.download_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.progress_label.setText(f"{model_id} indiriliyor...")
        
        self.download_worker = ModelDownloadWorker(model_id, self)
        self.download_worker.progress.connect(self._on_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.start()
    
    def _on_progress(self, message: str):
        self.progress_label.setText(message)
    
    def _on_download_finished(self, success: bool):
        self.download_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        
        if success:
            self.refresh_model_list()
        else:
            self.progress_label.setText("İndirme başarısız oldu.")
    
    def _select_model(self):
        item = self.model_list.currentItem()
        if not item:
            return
        
        model_id = item.data(Qt.ItemDataRole.UserRole)
        
        if not self.manager.is_model_downloaded(model_id):
            self.progress_label.setText("Önce modeli indirmeniz gerekiyor.")
            return
        
        self.manager.select_model(model_id)
        self.progress_label.setText(f"{model_id} modeli seçildi.")
        self.refresh_model_list()


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ai Subtitle Creator")
        self.setWindowIcon(QIcon(get_resource_path("logo.ico")))
        self.setMinimumSize(1000, 700)
        self.resize(1400, 900)  # Larger default for better layout
        
        self.video_path = None
        self.segments: List[SubtitleSegment] = []
        self.current_theme = SubtitleThemeConfig()
        self.saved_position = 0  # Saved video position for re-renders
        
        self.setup_ui()
        self.setup_menu()
        self.apply_theme()
    
    def setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top toolbar - modern glassmorphism style
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 rgba(26, 33, 66, 0.95), stop:1 rgba(17, 22, 49, 0.95));
            border-bottom: 1px solid rgba(59, 130, 246, 0.2);
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 10, 16, 10)
        toolbar_layout.setSpacing(12)
        
        # Logo/Title
        title_label = QLabel("🎬 Ai Subtitle Creator")
        title_label.setObjectName("titleLabel")
        toolbar_layout.addWidget(title_label)
        
        toolbar_layout.addStretch()
        
        # Action buttons
        self.open_btn = QPushButton("📁 Video Aç")
        self.open_btn.clicked.connect(self.open_video)
        toolbar_layout.addWidget(self.open_btn)
        
        self.transcribe_btn = QPushButton("🎤 Transkribe Et")
        self.transcribe_btn.clicked.connect(self.start_transcription)
        self.transcribe_btn.setEnabled(False)
        toolbar_layout.addWidget(self.transcribe_btn)
        
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.setObjectName("primaryButton")
        self.export_btn.clicked.connect(self.show_export_dialog)
        self.export_btn.setEnabled(False)
        toolbar_layout.addWidget(self.export_btn)
        
        # Settings button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.setToolTip("Ayarlar")
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        toolbar_layout.addWidget(self.settings_btn)
        
        main_layout.addWidget(toolbar)
        
        # Main content area with splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Video + Timeline
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #0a0e27, stop:1 #080c1a);
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 10, 6, 10)
        left_layout.setSpacing(8)
        
        # Video preview
        self.video_preview = VideoPreviewWidget()
        self.video_preview.position_changed.connect(self._on_video_position_changed)
        left_layout.addWidget(self.video_preview, stretch=1)
        
        # Timeline
        self.timeline = SubtitleTimelineWidget()
        self.timeline.segment_selected.connect(self._on_segment_selected)
        self.timeline.segment_double_clicked.connect(self._on_segment_double_clicked)
        self.timeline.seek_requested.connect(self._on_timeline_seek)
        left_layout.addWidget(self.timeline)
        
        # Subtitle editor
        self.subtitle_editor = SubtitleEditorPanel()
        self.subtitle_editor.subtitle_updated.connect(self._on_subtitle_updated)
        left_layout.addWidget(self.subtitle_editor)
        
        content_splitter.addWidget(left_widget)
        
        # Right side: Theme panel - wider for better visibility
        right_widget = QWidget()
        right_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #0a0e27, stop:1 #080c1a);
        """)
        right_widget.setMinimumWidth(280)
        right_widget.setMaximumWidth(400)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.theme_panel = ThemePanel()
        self.theme_panel.theme_changed.connect(self._on_theme_changed)
        right_layout.addWidget(self.theme_panel)
        
        content_splitter.addWidget(right_widget)
        content_splitter.setSizes([1000, 400])
        
        main_layout.addWidget(content_splitter, stretch=1)
        
        # Status bar / Progress - modern style
        self.status_bar = QWidget()
        self.status_bar.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 rgba(17, 22, 49, 0.95), stop:1 rgba(10, 14, 39, 0.98));
            border-top: 1px solid rgba(59, 130, 246, 0.15);
        """)
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(16, 8, 16, 8)
        
        self.status_label = QLabel("Hazır")
        self.status_label.setObjectName("subtitleLabel")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.status_bar)
    
    def setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("Dosya")
        
        open_action = QAction("Video Aç", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_video)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("Export...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.show_export_dialog)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("Çıkış", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Düzenle")
        
        transcribe_action = QAction("Transkribe Et", self)
        transcribe_action.setShortcut(QKeySequence("Ctrl+T"))
        transcribe_action.triggered.connect(self.start_transcription)
        edit_menu.addAction(transcribe_action)
    
    def apply_theme(self):
        """Apply dark theme stylesheet."""
        self.setStyleSheet(DARK_THEME)
    
    def open_video(self):
        """Open video file dialog."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Video Seç",
            "",
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)"
        )
        
        if path:
            self.video_path = path
            self.video_preview.load_video(path)
            self.transcribe_btn.setEnabled(True)
            self.status_label.setText(f"Video yüklendi: {os.path.basename(path)}")
            
            # Get video duration for timeline
            # Will be updated when player reports duration
            self.video_preview.player.durationChanged.connect(
                lambda d: self.timeline.set_segments(self.segments, d / 1000)
            )
    
    def start_transcription(self):
        """Start Whisper transcription."""
        if not self.video_path:
            return
        
        self.transcribe_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = TranscriptionWorker(self.video_path)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_transcription_finished)
        self.worker.error.connect(self._on_transcription_error)
        self.worker.start()
    
    def _on_transcription_finished(self, segments: List[SubtitleSegment]):
        """Handle transcription completion."""
        self.segments = segments
        self.transcribe_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        
        # Update timeline
        duration = self.video_preview.player.duration() / 1000
        self.timeline.set_segments(self.segments, duration)
        
        self.status_label.setText(f"{len(segments)} altyazı segmenti oluşturuldu. Önizleme hazırlanıyor...")
        
        # Start preview render
        self._render_preview()
    
    def _render_preview(self):
        """Render preview video with current theme."""
        if not self.segments or not self.video_path:
            return
        
        # Save current position before re-render
        self.saved_position = self.video_preview.player.position()
        
        # Stop and unload current video to release file handle
        self.video_preview.player.stop()
        self.video_preview.player.setSource(QUrl())  # Unload current video
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.preview_worker = PreviewRenderWorker(
            self.video_path,
            self.segments,
            self.current_theme
        )
        self.preview_worker.progress.connect(self.progress_bar.setValue)
        self.preview_worker.status.connect(self.status_label.setText)
        self.preview_worker.finished.connect(self._on_preview_ready)
        self.preview_worker.error.connect(self._on_preview_error)
        self.preview_worker.start()
    
    def _on_preview_ready(self, preview_path: str):
        """Handle preview render completion."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Önizleme hazır!")
        
        # Load the preview video
        self.video_preview.load_video(preview_path)
        
        # Restore previous position if we have one
        if self.saved_position > 0:
            # Need to wait for video to be ready before seeking
            QTimer.singleShot(100, lambda: self._restore_position())
        else:
            self.video_preview.player.play()
    
    def _restore_position(self):
        """Restore saved video position after preview load."""
        if self.saved_position > 0:
            self.video_preview.seek_to(self.saved_position)
        self.video_preview.player.play()
    
    def _on_preview_error(self, error: str):
        """Handle preview render error."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Önizleme hatası: {error}")
    
    def _on_transcription_error(self, error: str):
        """Handle transcription error."""
        self.progress_bar.setVisible(False)
        self.transcribe_btn.setEnabled(True)
        self.status_label.setText(f"Hata: {error}")
        QMessageBox.critical(self, "Hata", f"Transkripsiyon hatası:\n{error}")
    
    def _on_video_position_changed(self, position: float):
        """Handle video position change for timeline sync."""
        self.timeline.set_position(position)
    
    def _on_segment_selected(self, index: int):
        """Handle segment selection in timeline."""
        if 0 <= index < len(self.segments):
            segment = self.segments[index]
            self.subtitle_editor.load_segment(segment, index)
    
    def _on_segment_double_clicked(self, index: int):
        """Handle segment double click - seek to segment."""
        if 0 <= index < len(self.segments):
            segment = self.segments[index]
            self.video_preview.seek_to(int(segment.start * 1000))
    
    def _on_timeline_seek(self, position: float):
        """Handle timeline click to seek."""
        self.video_preview.seek_to(int(position * 1000))
    
    def _on_subtitle_updated(self, index: int, text: str, start: float, end: float):
        """Handle subtitle text update."""
        if 0 <= index < len(self.segments):
            # Check if text was actually changed
            old_text = self.segments[index].text
            
            self.segments[index].text = text
            self.segments[index].start = start
            self.segments[index].end = end
            
            # If text changed, clear words (karaoke timings no longer valid)
            if text != old_text:
                self.segments[index].words = None
            
            # Refresh timeline
            duration = self.video_preview.player.duration() / 1000
            self.timeline.set_segments(self.segments, duration)
            
            # Re-render preview with updated subtitles
            self.status_label.setText("Altyazı güncellendi, önizleme yenileniyor...")
            self._render_preview()
    
    def _on_theme_changed(self, theme: SubtitleThemeConfig):
        """Handle theme change."""
        self.current_theme = theme
        
        # Re-render preview if we have segments
        if self.segments:
            self._render_preview()
    
    def show_export_dialog(self):
        """Show export settings dialog."""
        if not self.segments:
            QMessageBox.warning(self, "Uyarı", "Önce transkripsiyon yapın!")
            return
        
        dialog = ExportDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            self.export_subtitles(settings)
    
    def show_settings_dialog(self):
        """Show settings dialog for model management."""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def export_subtitles(self, settings: dict):
        """Export subtitles with given settings."""
        output_path = settings["path"]
        format_type = settings["format"]
        
        if not output_path:
            QMessageBox.warning(self, "Uyarı", "Kayıt yolu seçin!")
            return
        
        self.status_label.setText("Export yapılıyor...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        
        try:
            if format_type == "srt":
                self._export_srt(output_path)
            elif format_type == "ass":
                self._export_ass(output_path)
            else:
                self._export_video(output_path)
            
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Export tamamlandı: {output_path}")
            QMessageBox.information(self, "Başarılı", f"Dosya kaydedildi:\n{output_path}")
            
        except Exception as e:
            self.status_label.setText(f"Export hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Export hatası:\n{e}")
        
        finally:
            self.progress_bar.setVisible(False)
    
    def _export_srt(self, path: str):
        """Export as SRT file."""
        with open(path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(self.segments):
                f.write(f"{i + 1}\n")
                f.write(f"{self._format_srt_time(seg.start)} --> {self._format_srt_time(seg.end)}\n")
                f.write(f"{seg.text}\n\n")
    
    def _export_ass(self, path: str):
        """Export as ASS file."""
        from .subtitle_renderer import SubtitleRenderer
        
        # Convert segments to dict format
        segments_dict = [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "words": seg.words or []
            }
            for seg in self.segments
        ]
        
        renderer = SubtitleRenderer(self.current_theme, 1080, 1920)
        renderer.render_to_file(segments_dict, path)
    
    def _export_video(self, path: str):
        """Export video with burned-in subtitles."""
        import tempfile
        import subprocess
        
        # First export ASS
        temp_ass = os.path.join(tempfile.gettempdir(), "temp_subtitles.ass")
        self._export_ass(temp_ass)
        
        # Format path for FFmpeg filter (cross-platform compatible)
        if sys.platform == "win32":
            # On Windows, the ass filter needs the path with forward slashes
            # and the colon after drive letter escaped
            filter_ass_path = temp_ass.replace("\\", "/")
            if len(filter_ass_path) >= 2 and filter_ass_path[1] == ":":
                filter_ass_path = filter_ass_path[0] + "\\:" + filter_ass_path[2:]
        else:
            filter_ass_path = temp_ass
        
        # Build filter strings
        filter_10bit = f"ass='{filter_ass_path}'"
        # HDR to SDR tone mapping for proper color conversion
        hdr_to_sdr = "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
        filter_8bit_hdr = f"{hdr_to_sdr},ass='{filter_ass_path}'"
        filter_8bit_simple = f"format=yuv420p,ass='{filter_ass_path}'"
        
        # Get hardware encoder if available
        encoder, encoder_args = get_hw_encoder()
        
        def run_ffmpeg(vf_filter, video_encoder, extra_args, desc):
            """Helper to run FFmpeg with given settings"""
            cmd = [
                get_ffmpeg_path(),
                "-y",
                "-i", self.video_path,
                "-vf", vf_filter,
                "-c:v", video_encoder,
            ]
            cmd.extend(extra_args)
            cmd.extend(["-c:a", "aac", path])
            print(f"Trying {desc}: {' '.join(cmd)}")
            print(f"Trying {desc}: {' '.join(cmd)}")
            
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000
                
            return subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        
        result = None
        
        # Encoding fallback chain (same as preview but with better quality for export)
        if encoder != "libx264":
            result = run_ffmpeg(filter_10bit, encoder, encoder_args, f"GPU ({encoder}) 10-bit")
            
            if result.returncode != 0:
                print(f"GPU 10-bit failed, trying GPU 8-bit with HDR tone mapping...")
                result = run_ffmpeg(filter_8bit_hdr, encoder, encoder_args, f"GPU ({encoder}) 8-bit HDR")
            
            if result.returncode != 0:
                print(f"GPU 8-bit HDR failed, trying GPU 8-bit simple...")
                result = run_ffmpeg(filter_8bit_simple, encoder, encoder_args, f"GPU ({encoder}) 8-bit simple")
            
            if result.returncode != 0:
                print(f"GPU failed, trying CPU with HDR tone mapping...")
                result = run_ffmpeg(filter_8bit_hdr, "libx264", ["-crf", "23", "-preset", "medium"], "CPU HDR")
            
            if result.returncode != 0:
                print(f"CPU HDR failed, trying CPU simple...")
                result = run_ffmpeg(filter_8bit_simple, "libx264", ["-crf", "23", "-preset", "medium"], "CPU simple")
        else:
            result = run_ffmpeg(filter_8bit_hdr, "libx264", ["-crf", "23", "-preset", "medium"], "CPU HDR")
            if result.returncode != 0:
                result = run_ffmpeg(filter_8bit_simple, "libx264", ["-crf", "23", "-preset", "medium"], "CPU simple")
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr}")
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT time (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{hours:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def main():
    """Main entry point for GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("Ai Subtitle Creator")
    app.setWindowIcon(QIcon(get_resource_path("logo.ico")))
    
    # Apply theme
    app.setStyleSheet(DARK_THEME)
    
    # Check for first run
    config = get_config()
    
    if config.is_first_run:
        # Show first run dialog for model selection
        first_run = FirstRunDialog()
        if first_run.exec() != QDialog.DialogCode.Accepted:
            # User cancelled, exit
            sys.exit(0)
    
    # Check and update downloaded models
    manager = get_model_manager()
    manager.check_and_update_downloaded_models()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
