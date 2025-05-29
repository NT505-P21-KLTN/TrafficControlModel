"""
Material Design Theme for PyQt5 Application
Implements Google's Material Design 3 color system and styling
"""

from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QColor, QPalette, QFont


class MaterialColors:
    """Material Design 3 Color Tokens"""

    # Primary colors
    PRIMARY = "#388E3C"  # Green
    ON_PRIMARY = "#FFFFFF"
    PRIMARY_CONTAINER = "#C8E6C9"
    ON_PRIMARY_CONTAINER = "#1B5E20"

    # Secondary colors
    SECONDARY = "#4CAF50"  # Green variant
    ON_SECONDARY = "#FFFFFF"
    SECONDARY_CONTAINER = "#A5D6A7"
    ON_SECONDARY_CONTAINER = "#2E7D32"

    # Tertiary colors
    TERTIARY = "#81C784"  # Light green
    ON_TERTIARY = "#FFFFFF"
    TERTIARY_CONTAINER = "#E8F5E9"
    ON_TERTIARY_CONTAINER = "#33691E"

    # Error colors
    ERROR = "#BA1A1A"
    ON_ERROR = "#FFFFFF"
    ERROR_CONTAINER = "#FFDAD6"
    ON_ERROR_CONTAINER = "#410002"

    # Neutral colors
    BACKGROUND = "#F1F8E9"  # Light green background
    ON_BACKGROUND = "#1C1B1F"
    SURFACE = "#F1F8E9"
    ON_SURFACE = "#1C1B1F"
    SURFACE_VARIANT = "#DCEDC8"
    ON_SURFACE_VARIANT = "#33691E"

    # Outline colors
    OUTLINE = "#8BC34A"
    OUTLINE_VARIANT = "#C5E1A5"

    # Surface containers
    SURFACE_CONTAINER_LOWEST = "#FFFFFF"
    SURFACE_CONTAINER_LOW = "#F9FBE7"
    SURFACE_CONTAINER = "#F0F4C3"
    SURFACE_CONTAINER_HIGH = "#E6EE9C"
    SURFACE_CONTAINER_HIGHEST = "#FCFCFA"

    # State layers (for hover, focus, etc.)
    STATE_HOVER_OPACITY = "0.08"
    STATE_FOCUS_OPACITY = "0.12"
    STATE_PRESSED_OPACITY = "0.12"
    STATE_DISABLED_OPACITY = "0.12"


class MaterialTypography:
    """Material Design Typography Scale"""
    
    @staticmethod
    def get_font(style="body_medium"):
        """Get font for specific typography style"""
        fonts = {
            "display_large": ("Roboto", 57, QFont.Light),
            "display_medium": ("Roboto", 45, QFont.Normal),
            "display_small": ("Roboto", 36, QFont.Normal),
            "headline_large": ("Roboto", 32, QFont.Normal),
            "headline_medium": ("Roboto", 28, QFont.Normal),
            "headline_small": ("Roboto", 24, QFont.Normal),
            "title_large": ("Roboto", 22, QFont.Normal),
            "title_medium": ("Roboto", 16, QFont.DemiBold),
            "title_small": ("Roboto", 14, QFont.DemiBold),
            "body_large": ("Roboto", 16, QFont.Normal),
            "body_medium": ("Roboto", 14, QFont.Normal),
            "body_small": ("Roboto", 12, QFont.Normal),
            "label_large": ("Roboto", 14, QFont.DemiBold),
            "label_medium": ("Roboto", 12, QFont.DemiBold),
            "label_small": ("Roboto", 11, QFont.DemiBold),
        }
        
        font_family, size, weight = fonts.get(style, fonts["body_medium"])
        font = QFont(font_family, size)
        font.setWeight(weight)
        return font


class MaterialStylesheet:
    """Material Design Stylesheet Generator"""
    
    @staticmethod
    def get_main_stylesheet():
        """Get main application stylesheet"""
        return f"""
        /* Main Window */
        QMainWindow {{
            background-color: {MaterialColors.BACKGROUND};
            color: {MaterialColors.ON_BACKGROUND};
            font-family: 'Roboto', sans-serif;
        }}
        
        /* Group Boxes */
        QGroupBox {{
            background-color: {MaterialColors.SURFACE_CONTAINER_LOW};
            border: 1px solid {MaterialColors.OUTLINE_VARIANT};
            border-radius: 12px;
            margin-top: 8px;
            padding-top: 16px;
            font-weight: 500;
            font-size: 14px;
            color: {MaterialColors.ON_SURFACE};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: {MaterialColors.SURFACE_CONTAINER_LOW};
            color: {MaterialColors.PRIMARY};
            font-weight: 600;
        }}
        
        /* Primary Buttons */
        QPushButton {{
            background-color: {MaterialColors.PRIMARY};
            color: {MaterialColors.ON_PRIMARY};
            border: none;
            border-radius: 20px;
            padding: 10px 24px;
            font-size: 14px;
            font-weight: 500;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {MaterialColors.PRIMARY}, 
                stop:1 {MaterialColors.SECONDARY});
        }}
        
        QPushButton:pressed {{
            background-color: rgba(103, 80, 164, 0.88);
        }}
        
        QPushButton:disabled {{
            background-color: {MaterialColors.ON_SURFACE};
            color: rgba(28, 27, 31, 0.38);
        }}
        
        /* Secondary Buttons */
        QPushButton[class="secondary"] {{
            background-color: {MaterialColors.SECONDARY_CONTAINER};
            color: {MaterialColors.ON_SECONDARY_CONTAINER};
        }}
        
        QPushButton[class="secondary"]:hover {{
            background-color: rgba(232, 222, 248, 0.92);
        }}
        
        /* Text Buttons */
        QPushButton[class="text"] {{
            background-color: transparent;
            color: {MaterialColors.PRIMARY};
            padding: 8px 12px;
        }}
        
        QPushButton[class="text"]:hover {{
            background-color: rgba(103, 80, 164, 0.08);
        }}
        
        /* Labels */
        QLabel {{
            color: {MaterialColors.ON_SURFACE};
            font-size: 14px;
        }}
        
        QLabel[class="headline"] {{
            font-size: 24px;
            font-weight: 500;
            color: {MaterialColors.ON_SURFACE};
        }}
        
        QLabel[class="title"] {{
            font-size: 16px;
            font-weight: 600;
            color: {MaterialColors.ON_SURFACE};
        }}
        
        /* Text Inputs */
        QLineEdit {{
            background-color: {MaterialColors.SURFACE_CONTAINER_HIGHEST};
            border: 1px solid {MaterialColors.OUTLINE};
            border-radius: 4px;
            padding: 12px 16px;
            font-size: 16px;
            color: {MaterialColors.ON_SURFACE};
        }}
        
        QLineEdit:focus {{
            border: 2px solid {MaterialColors.PRIMARY};
            background-color: {MaterialColors.SURFACE};
        }}
        
        /* Combo Boxes */
        QComboBox {{
            background-color: {MaterialColors.SURFACE_CONTAINER_HIGHEST};
            border: 1px solid {MaterialColors.OUTLINE};
            border-radius: 4px;
            padding: 12px 16px;
            font-size: 14px;
            color: {MaterialColors.ON_SURFACE};
        }}
        
        QComboBox:focus {{
            border: 2px solid {MaterialColors.PRIMARY};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iIzQ5NDU0RiIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
        }}
        
        /* Check Boxes */
        QCheckBox {{
            color: {MaterialColors.ON_SURFACE};
            font-size: 14px;
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 2px;
        }}
        
        QCheckBox::indicator:unchecked {{
            border: 2px solid {MaterialColors.OUTLINE};
            background-color: transparent;
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {MaterialColors.PRIMARY};
            border: 2px solid {MaterialColors.PRIMARY};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHZpZXdCb3g9IjAgMCAxOCAxOCIgZmlsbD0ibm9uZSIgeG1zbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMuNzUgOS4yNUw3LjUgMTNMMTQuMjUgNi4yNSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
        }}
        
        /* Radio Buttons */
        QRadioButton {{
            color: {MaterialColors.ON_SURFACE};
            font-size: 14px;
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border-radius: 10px;
        }}
        
        QRadioButton::indicator:unchecked {{
            border: 2px solid {MaterialColors.OUTLINE};
            background-color: transparent;
        }}
        
        QRadioButton::indicator:checked {{
            border: 6px solid {MaterialColors.PRIMARY};
            background-color: {MaterialColors.ON_PRIMARY};
        }}
        
        /* Sliders */
        QSlider::groove:horizontal {{
            background: {MaterialColors.OUTLINE_VARIANT};
            height: 4px;
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            background: {MaterialColors.PRIMARY};
            border: none;
            width: 20px;
            height: 20px;
            margin: -8px 0;
            border-radius: 10px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {MaterialColors.PRIMARY};
            width: 24px;
            height: 24px;
            margin: -10px 0;
        }}
        
        QSlider::sub-page:horizontal {{
            background: {MaterialColors.PRIMARY};
            border-radius: 2px;
        }}
        
        /* Spin Boxes */
        QSpinBox {{
            background-color: {MaterialColors.SURFACE_CONTAINER_HIGHEST};
            border: 1px solid {MaterialColors.OUTLINE};
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 14px;
            color: {MaterialColors.ON_SURFACE};
        }}
        
        QSpinBox:focus {{
            border: 2px solid {MaterialColors.PRIMARY};
        }}
        
        /* Tables */
        QTableWidget {{
            background-color: {MaterialColors.SURFACE};
            border: 1px solid {MaterialColors.OUTLINE_VARIANT};
            border-radius: 8px;
            gridline-color: {MaterialColors.OUTLINE_VARIANT};
            selection-background-color: {MaterialColors.PRIMARY_CONTAINER};
            font-size: 14px;
        }}
        
        QTableWidget::item {{
            padding: 8px;
            border: none;
        }}
        
        QTableWidget::item:selected {{
            background-color: {MaterialColors.PRIMARY_CONTAINER};
            color: {MaterialColors.ON_PRIMARY_CONTAINER};
        }}
        
        QHeaderView::section {{
            background-color: {MaterialColors.SURFACE_CONTAINER_HIGH};
            color: {MaterialColors.ON_SURFACE_VARIANT};
            padding: 12px 8px;
            border: none;
            border-bottom: 1px solid {MaterialColors.OUTLINE_VARIANT};
            font-weight: 600;
            font-size: 12px;
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            background: {MaterialColors.SURFACE_CONTAINER};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {MaterialColors.OUTLINE};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {MaterialColors.ON_SURFACE_VARIANT};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: {MaterialColors.OUTLINE_VARIANT};
            width: 1px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {MaterialColors.PRIMARY};
        }}
        """


class MaterialShadow:
    """Material Design Shadow Effects"""
    
    @staticmethod
    def apply_elevation(widget: QWidget, elevation: int = 1):
        """Apply Material Design elevation shadow to widget"""
        shadow = QGraphicsDropShadowEffect()
        
        # Shadow parameters based on Material Design elevation levels
        elevation_configs = {
            1: {"blur": 4, "offset": 1, "opacity": 0.15},
            2: {"blur": 8, "offset": 2, "opacity": 0.15},
            3: {"blur": 12, "offset": 4, "opacity": 0.15},
            4: {"blur": 16, "offset": 6, "opacity": 0.15},
            6: {"blur": 20, "offset": 8, "opacity": 0.15},
            8: {"blur": 24, "offset": 10, "opacity": 0.15},
            12: {"blur": 32, "offset": 14, "opacity": 0.15},
            16: {"blur": 40, "offset": 18, "opacity": 0.15},
            24: {"blur": 48, "offset": 24, "opacity": 0.15},
        }
        
        config = elevation_configs.get(elevation, elevation_configs[1])
        
        shadow.setBlurRadius(config["blur"])
        shadow.setOffset(0, config["offset"])
        shadow.setColor(QColor(0, 0, 0, int(config["opacity"] * 255)))
        
        widget.setGraphicsEffect(shadow)


class MaterialAnimations:
    """Material Design Animations"""
    
    @staticmethod
    def create_fade_animation(widget: QWidget, start_opacity: float = 0.0, end_opacity: float = 1.0, duration: int = 200):
        """Create a fade animation for a widget"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(start_opacity)
        animation.setEndValue(end_opacity)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        return animation
    
    @staticmethod
    def create_slide_animation(widget: QWidget, start_pos, end_pos, duration: int = 250):
        """Create a slide animation for a widget"""
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        return animation


class MaterialUtils:
    """Material Design Utility Functions"""
    
    @staticmethod
    def set_button_style(button, style="primary"):
        """Set Material Design style for buttons"""
        styles = {
            "primary": "",
            "secondary": "class: secondary",
            "text": "class: text"
        }
        button.setProperty("class", styles.get(style, ""))
    
    @staticmethod
    def set_label_style(label, style="body"):
        """Set Material Design style for labels"""
        styles = {
            "headline": "class: headline",
            "title": "class: title",
            "body": ""
        }
        label.setProperty("class", styles.get(style, ""))
        label.setFont(MaterialTypography.get_font(f"{style}_medium"))
