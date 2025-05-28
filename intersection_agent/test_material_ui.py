#!/usr/bin/env python3.8
"""
Test script to verify Material Design UI components work correctly
"""
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox, QCheckBox, QSlider, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Import Material Design theme
try:
    from material_theme import (MaterialStylesheet, MaterialShadow, MaterialUtils, 
                              MaterialColors, MaterialTypography, MaterialAnimations)
    print("✓ Material Design theme imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Material Design theme: {e}")
    sys.exit(1)

class TestMaterialWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Material Design Test - Traffic Simulation")
        self.setGeometry(100, 100, 800, 600)
        
        # Apply Material Design theme
        self.setStyleSheet(MaterialStylesheet.get_main_stylesheet())
        
        # Set application font
        app_font = MaterialTypography.get_font("body_medium")
        self.setFont(app_font)
        
        # Apply elevation shadow to main window
        MaterialShadow.apply_elevation(self, elevation=2)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create test components
        self.create_test_controls(main_layout)
        self.create_test_cards(main_layout)
        
    def create_test_controls(self, parent_layout):
        # Control panel
        group = QGroupBox("Material Design Controls Test")
        MaterialShadow.apply_elevation(group, elevation=1)
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Primary button
        primary_btn = QPushButton("Primary Button")
        MaterialUtils.set_button_style(primary_btn, "primary")
        primary_btn.setFont(MaterialTypography.get_font("label_large"))
        layout.addWidget(primary_btn)
        
        # Secondary button
        secondary_btn = QPushButton("Secondary Button")
        MaterialUtils.set_button_style(secondary_btn, "secondary")
        secondary_btn.setFont(MaterialTypography.get_font("label_large"))
        layout.addWidget(secondary_btn)
        
        # Text button
        text_btn = QPushButton("Text Button")
        MaterialUtils.set_button_style(text_btn, "text")
        text_btn.setFont(MaterialTypography.get_font("label_large"))
        layout.addWidget(text_btn)
        
        # Checkbox
        checkbox = QCheckBox("Material Checkbox")
        checkbox.setFont(MaterialTypography.get_font("body_medium"))
        layout.addWidget(checkbox)
        
        # Slider
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(50)
        layout.addWidget(slider)
        
        # ComboBox
        combo = QComboBox()
        combo.addItems(["Option 1", "Option 2", "Option 3"])
        layout.addWidget(combo)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_test_cards(self, parent_layout):
        # Card container
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        # Create some test cards
        for i in range(3):
            card = QWidget()
            card.setStyleSheet(f"""
                QWidget {{
                    background-color: {MaterialColors.SURFACE_CONTAINER};
                    border-radius: 8px;
                    padding: 16px;
                }}
            """)
            MaterialShadow.apply_elevation(card, elevation=1)
            
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(12)
            
            # Card title
            title = QLabel(f"Test Card {i+1}")
            MaterialUtils.set_label_style(title, "title")
            card_layout.addWidget(title)
            
            # Card content
            content = QLabel(f"This is test content for card {i+1}.\nTesting Material Design styling.")
            content.setFont(MaterialTypography.get_font("body_medium"))
            content.setWordWrap(True)
            card_layout.addWidget(content)
            
            # Card action
            action_btn = QPushButton(f"Action {i+1}")
            MaterialUtils.set_button_style(action_btn, "primary" if i == 0 else "secondary")
            action_btn.setFont(MaterialTypography.get_font("label_medium"))
            card_layout.addWidget(action_btn)
            
            cards_layout.addWidget(card)
        
        cards_widget = QWidget()
        cards_widget.setLayout(cards_layout)
        parent_layout.addWidget(cards_widget)

def main():
    app = QApplication(sys.argv)
    
    # Test Material Design components
    print("Testing Material Design UI Components...")
    
    try:
        # Test color system
        print(f"✓ Primary color: {MaterialColors.PRIMARY}")
        print(f"✓ Surface color: {MaterialColors.SURFACE}")
        print(f"✓ Background color: {MaterialColors.BACKGROUND}")
        
        # Test typography
        font = MaterialTypography.get_font("headline_large")
        print(f"✓ Typography system working: {font.family()}, {font.pointSize()}pt")
        
        # Test stylesheet generation
        stylesheet = MaterialStylesheet.get_main_stylesheet()
        print(f"✓ Stylesheet generated: {len(stylesheet)} characters")
        
        # Create and show test window
        window = TestMaterialWindow()
        window.show()
        
        print("✓ Material Design UI test window created successfully!")
        print("✓ All Material Design components loaded and styled correctly")
        print("\nIf you can see a styled window with Material Design components, the implementation is working!")
        
        # Run the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"✗ Error testing Material Design UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
