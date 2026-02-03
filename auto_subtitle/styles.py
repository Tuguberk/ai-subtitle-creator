"""
Modern Premium Dark Theme Styles for PyQt6 Subtitle Editor
Inspired by glassmorphism and modern UI trends
"""

DARK_THEME = """
/* === MAIN WINDOW === */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #0a0e27, stop:1 #111631);
    color: #e8eaf6;
}

/* === GENERAL WIDGET === */
QWidget {
    background-color: transparent;
    color: #e8eaf6;
    font-family: 'SF Pro Display', 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* === GLASSMORPHISM GROUP BOX === */
QGroupBox {
    background-color: rgba(26, 33, 66, 0.7);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 12px;
    margin-top: 16px;
    padding: 16px;
    padding-top: 24px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: #3b82f6;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* === BUTTONS === */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2a3a6d, stop:1 #1e2952);
    color: #e8eaf6;
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 500;
    min-width: 80px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #3b4f8a, stop:1 #2a3a6d);
    border: 1px solid rgba(59, 130, 246, 0.5);
}

QPushButton:pressed {
    background: #1a2952;
}

QPushButton:disabled {
    background-color: rgba(35, 42, 77, 0.5);
    color: #5c6a94;
    border: 1px solid rgba(59, 130, 246, 0.1);
}

/* Primary Button - Cyan Accent */
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3b82f6, stop:1 #06b6d4);
    border: none;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #5b9bf7, stop:1 #22d3ee);
}

QPushButton#primaryButton:pressed {
    background: #2563eb;
}

/* === TEXT INPUTS === */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: rgba(17, 22, 49, 0.8);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 8px;
    padding: 10px 14px;
    color: #e8eaf6;
    selection-background-color: #3b82f6;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
    background-color: rgba(17, 22, 49, 0.95);
}

/* === COMBO BOX === */
QComboBox {
    background-color: rgba(17, 22, 49, 0.8);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 8px;
    padding: 8px 14px;
    color: #e8eaf6;
    min-width: 100px;
}

QComboBox:hover {
    border: 1px solid rgba(59, 130, 246, 0.4);
}

QComboBox:focus {
    border: 1px solid #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #111631;
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    selection-background-color: #3b82f6;
    color: #e8eaf6;
    padding: 4px;
}

/* === SPIN BOX === */
QSpinBox, QDoubleSpinBox {
    background-color: rgba(17, 22, 49, 0.8);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 6px;
    padding: 6px 8px;
    color: #e8eaf6;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #3b82f6;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid rgba(59, 130, 246, 0.15);
    background: transparent;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: padding;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid rgba(59, 130, 246, 0.15);
    background: transparent;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background: rgba(59, 130, 246, 0.2);
}

/* === SLIDERS === */
QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: rgba(26, 33, 66, 0.8);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3b82f6, stop:1 #06b6d4);
    border: none;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #5b9bf7, stop:1 #22d3ee);
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3b82f6, stop:1 #06b6d4);
    border-radius: 3px;
}

/* === PROGRESS BAR === */
QProgressBar {
    background-color: rgba(17, 22, 49, 0.8);
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3b82f6, stop:1 #06b6d4);
    border-radius: 6px;
}

/* === SCROLL BARS === */
QScrollBar:vertical {
    background: rgba(17, 22, 49, 0.5);
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: rgba(59, 130, 246, 0.4);
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(59, 130, 246, 0.6);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: rgba(17, 22, 49, 0.5);
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: rgba(59, 130, 246, 0.4);
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(59, 130, 246, 0.6);
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === LIST WIDGET === */
QListWidget {
    background-color: rgba(17, 22, 49, 0.6);
    border: 1px solid rgba(59, 130, 246, 0.15);
    border-radius: 10px;
    padding: 6px;
    outline: none;
}

QListWidget::item {
    background-color: transparent;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 2px 0;
}

QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(59, 130, 246, 0.6), stop:1 rgba(6, 182, 212, 0.4));
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: rgba(59, 130, 246, 0.15);
}

/* === SCROLL AREA === */
QScrollArea {
    background-color: transparent;
    border: none;
}

/* === SPLITTER === */
QSplitter::handle {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 transparent, stop:0.5 rgba(59, 130, 246, 0.3), stop:1 transparent);
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

/* === LABELS === */
QLabel {
    color: #e8eaf6;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: 700;
    color: #3b82f6;
    letter-spacing: 0.5px;
}

QLabel#subtitleLabel {
    font-size: 11px;
    color: #8b9cc7;
}

/* === CHECK BOX === */
QCheckBox {
    color: #e8eaf6;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid rgba(59, 130, 246, 0.3);
    background-color: rgba(17, 22, 49, 0.6);
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #3b82f6, stop:1 #06b6d4);
    border-color: #3b82f6;
}

QCheckBox::indicator:hover {
    border-color: rgba(59, 130, 246, 0.6);
}

/* === TOOLTIP === */
QToolTip {
    background-color: rgba(17, 22, 49, 0.95);
    color: #e8eaf6;
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 6px;
    padding: 8px 12px;
}

/* === MENU === */
QMenu {
    background-color: rgba(17, 22, 49, 0.95);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 10px;
    padding: 6px;
}

QMenu::item {
    padding: 10px 24px;
    border-radius: 6px;
}

QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(59, 130, 246, 0.5), stop:1 rgba(6, 182, 212, 0.3));
}

QMenu::separator {
    height: 1px;
    background: rgba(59, 130, 246, 0.2);
    margin: 6px 12px;
}

/* === DIALOG === */
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #0a0e27, stop:1 #111631);
}

QDialogButtonBox QPushButton {
    min-width: 100px;
}

/* === FRAME === */
QFrame {
    background-color: transparent;
}
"""

# Modern color palette for programmatic access
COLORS = {
    "background_dark": "#0a0e27",
    "background_medium": "#111631",
    "background_light": "#1a2142",
    "surface": "#232a4d",
    "accent": "#3b82f6",
    "accent_cyan": "#06b6d4",
    "accent_glow": "rgba(59, 130, 246, 0.4)",
    "text_primary": "#e8eaf6",
    "text_secondary": "#8b9cc7",
    "border": "rgba(59, 130, 246, 0.2)",
    "border_hover": "rgba(59, 130, 246, 0.4)",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
}
