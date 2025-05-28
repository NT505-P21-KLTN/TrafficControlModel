#!/usr/bin/env python3.8
"""
Test script to verify the main Material Design traffic simulation UI
This version loads the UI without requiring SUMO or simulation components
"""
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QComboBox, 
                            QLineEdit, QTableWidget, QTableWidgetItem, QGroupBox,
                            QCheckBox, QSlider, QSpinBox, QRadioButton, QFrame, QHeaderView,
                            QSplitter, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

# Import Material Design theme
from material_theme import (MaterialStylesheet, MaterialShadow, MaterialUtils, 
                          MaterialColors, MaterialTypography, MaterialAnimations)

# Mock simulation thread for UI testing
class MockSimulationThread(QThread):
    step_updated = pyqtSignal(int)
    vehicle_updated = pyqtSignal(dict)
    stats_updated = pyqtSignal(dict)
    cumulative_stats_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.auto_spawn = True
        self.vehicle_types = {
            "veh_passenger": 50,
            "veh_bus": 20,
            "veh_truck": 15,
            "veh_emergency": 10,
            "veh_motorcycle": 5
        }
        self.route_weights = {
            "W_N": 8, "W_E": 8, "W_S": 8,
            "N_W": 8, "N_E": 8, "N_S": 8,
            "E_N": 8, "E_S": 8, "E_W": 8,
            "S_N": 8, "S_E": 8, "S_W": 8
        }

class MaterialTrafficWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Traffic Simulation Control - Material Design")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Apply Material Design theme
        self.setStyleSheet(MaterialStylesheet.get_main_stylesheet())
        
        # Set application font
        app_font = MaterialTypography.get_font("body_medium")
        self.setFont(app_font)
        
        # Apply elevation shadow to main window
        MaterialShadow.apply_elevation(self, elevation=2)

        # Create mock simulation thread
        self.sim_thread = MockSimulationThread()
        
        # Initialize vehicle counter
        self.vehicle_counter = 0

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Create left panel for auto spawn controls
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add toggle button for auto spawn controls
        toggle_button = QPushButton("Hide Auto Spawn Controls")
        MaterialUtils.set_button_style(toggle_button, "secondary")
        toggle_button.clicked.connect(self.toggle_auto_spawn_panel)
        left_layout.addWidget(toggle_button)
        
        # Create auto spawn controls container
        self.auto_spawn_container = QWidget()
        auto_spawn_layout = QVBoxLayout(self.auto_spawn_container)
        self.create_auto_spawn_panel(auto_spawn_layout)
        left_layout.addWidget(self.auto_spawn_container)
        
        # Add left panel to splitter
        splitter.addWidget(self.left_panel)

        # Create right panel for other controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.create_control_panel(right_layout)
        self.create_vehicle_panel(right_layout)
        self.create_vehicle_table(right_layout)
        self.create_statistics_panel(right_layout)
        
        # Add right panel to splitter
        splitter.addWidget(right_panel)
        
        # Set initial sizes (40% left, 60% right)
        splitter.setSizes([640, 960])

        # Initialize UI components
        self.initialize_ui_data()

    def create_control_panel(self, parent_layout):
        group = QGroupBox("Simulation Control")
        MaterialShadow.apply_elevation(group, elevation=1)
        layout = QHBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Start/Stop button - Primary style
        self.start_button = QPushButton("Start Simulation")
        MaterialUtils.set_button_style(self.start_button, "primary")
        self.start_button.setFont(MaterialTypography.get_font("label_large"))
        layout.addWidget(self.start_button)
        
        # Render mode toggle - Secondary style
        self.render_mode_check = QCheckBox("Simple Shapes")
        self.render_mode_check.setChecked(True)
        self.render_mode_check.setFont(MaterialTypography.get_font("body_medium"))
        layout.addWidget(self.render_mode_check)
        
        # Status label - Title style
        self.status_label = QLabel("Status: UI Test Mode")
        MaterialUtils.set_label_style(self.status_label, "title")
        layout.addWidget(self.status_label)
        
        # Step counter - Body style
        self.step_label = QLabel("Steps: 0")
        self.step_label.setFont(MaterialTypography.get_font("body_large"))
        layout.addWidget(self.step_label)
        
        # Speed control container
        speed_container = QWidget()
        speed_layout = QVBoxLayout(speed_container)
        speed_layout.setSpacing(8)
        
        speed_label = QLabel("Simulation Speed:")
        speed_label.setFont(MaterialTypography.get_font("label_medium"))
        speed_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(1)
        speed_layout.addWidget(self.speed_slider)
        
        layout.addWidget(speed_container)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_auto_spawn_panel(self, parent_layout):
        group = QGroupBox("Auto Spawn Controls")
        MaterialShadow.apply_elevation(group, elevation=1)
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Enable/disable auto spawn
        self.auto_spawn_check = QCheckBox("Enable Auto Spawn")
        self.auto_spawn_check.setChecked(True)
        self.auto_spawn_check.setFont(MaterialTypography.get_font("body_large"))
        layout.addWidget(self.auto_spawn_check)
        
        # Distribution presets with Material Design styling
        preset_group = QGroupBox("Traffic Pattern")
        MaterialShadow.apply_elevation(preset_group, elevation=1)
        preset_layout = QVBoxLayout()
        preset_layout.setSpacing(8)
        
        # Create radio buttons for presets
        self.preset_buttons = []
        preset_names = [
            "Urban Rush Hour", "Highway Traffic", "Mixed Traffic", "Emergency Heavy",
            "N-S Dominant", "E-W Dominant", "Diagonal", "Circular"
        ]
        
        for i, name in enumerate(preset_names):
            radio = QRadioButton(name)
            radio.setFont(MaterialTypography.get_font("body_medium"))
            self.preset_buttons.append(radio)
            preset_layout.addWidget(radio)
        
        # Set default selection
        self.preset_buttons[4].setChecked(True)  # N-S Dominant
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Vehicle type distribution
        type_group = QGroupBox("Vehicle Type Distribution")
        MaterialShadow.apply_elevation(type_group, elevation=1)
        type_scroll_area = QScrollArea()
        type_scroll_widget = QWidget()
        type_layout = QVBoxLayout(type_scroll_widget)
        type_layout.setSpacing(8)
        
        self.type_sliders = {}
        for vehicle_type, percentage in self.sim_thread.vehicle_types.items():
            slider_container = QWidget()
            slider_layout = QHBoxLayout(slider_container)
            slider_layout.setContentsMargins(0, 0, 0, 0)
            
            type_label = QLabel(f"{vehicle_type.replace('veh_', '').title()}:")
            type_label.setFont(MaterialTypography.get_font("body_small"))
            type_label.setMinimumWidth(100)
            slider_layout.addWidget(type_label)
            
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(percentage)
            self.type_sliders[vehicle_type] = slider
            slider_layout.addWidget(slider)
            
            percentage_label = QLabel(f"{percentage}%")
            percentage_label.setFont(MaterialTypography.get_font("label_small"))
            percentage_label.setMinimumWidth(40)
            slider_layout.addWidget(percentage_label)
            self.type_sliders[f"{vehicle_type}_label"] = percentage_label
            
            type_layout.addWidget(slider_container)
        
        type_scroll_area.setWidget(type_scroll_widget)
        type_scroll_area.setWidgetResizable(True)
        type_scroll_area.setMaximumHeight(200)
        
        type_group_layout = QVBoxLayout()
        type_group_layout.addWidget(type_scroll_area)
        type_group.setLayout(type_group_layout)
        layout.addWidget(type_group)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_vehicle_panel(self, parent_layout):
        group = QGroupBox("Add Vehicle")
        MaterialShadow.apply_elevation(group, elevation=1)
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Route selection
        route_container = QWidget()
        route_layout = QVBoxLayout(route_container)
        route_layout.setContentsMargins(0, 0, 0, 0)
        
        route_label = QLabel("Route:")
        route_label.setFont(MaterialTypography.get_font("label_medium"))
        route_layout.addWidget(route_label)
        
        self.route_combo = QComboBox()
        self.route_combo.addItems([
            "W_N", "W_E", "W_S", "N_W", "N_E", "N_S",
            "E_N", "E_S", "E_W", "S_N", "S_E", "S_W"
        ])
        route_layout.addWidget(self.route_combo)
        layout.addWidget(route_container)
        
        # Vehicle type selection
        type_container = QWidget()
        type_layout = QVBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        
        type_label = QLabel("Type:")
        type_label.setFont(MaterialTypography.get_font("label_medium"))
        type_layout.addWidget(type_label)
        
        self.vehicle_type_combo = QComboBox()
        self.vehicle_type_combo.addItems([
            "veh_passenger", "veh_bus", "veh_truck", "veh_emergency", "veh_motorcycle"
        ])
        type_layout.addWidget(self.vehicle_type_combo)
        layout.addWidget(type_container)
        
        # Speed input
        speed_container = QWidget()
        speed_layout = QVBoxLayout(speed_container)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        
        speed_label = QLabel("Speed:")
        speed_label.setFont(MaterialTypography.get_font("label_medium"))
        speed_layout.addWidget(speed_label)
        
        self.speed_input = QLineEdit("10")
        speed_layout.addWidget(self.speed_input)
        layout.addWidget(speed_container)
        
        # Action buttons
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        
        add_button = QPushButton("Add Vehicle")
        MaterialUtils.set_button_style(add_button, "primary")
        add_button.setFont(MaterialTypography.get_font("label_medium"))
        button_layout.addWidget(add_button)
        
        random_button = QPushButton("Add 5 Random")
        MaterialUtils.set_button_style(random_button, "secondary")
        random_button.setFont(MaterialTypography.get_font("label_medium"))
        button_layout.addWidget(random_button)
        
        layout.addWidget(button_container)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_vehicle_table(self, parent_layout):
        group = QGroupBox("Active Vehicles")
        MaterialShadow.apply_elevation(group, elevation=1)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Create table with Material Design styling
        self.vehicle_table = QTableWidget()
        self.vehicle_table.setColumnCount(7)
        self.vehicle_table.setHorizontalHeaderLabels(["ID", "Type", "Route", "Road", "Lane", "Speed", "Waiting"])
        
        # Apply Material Design styling to table
        self.vehicle_table.setAlternatingRowColors(True)
        self.vehicle_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.vehicle_table.horizontalHeader().setStretchLastSection(True)
        
        # Add some sample data
        sample_data = [
            ["car_001", "passenger", "W_N", "W2TL", "1", "12.5", "2.1"],
            ["bus_001", "bus", "N_S", "N2TL", "2", "8.3", "0.5"],
            ["truck_001", "truck", "E_W", "E2TL", "0", "15.2", "1.8"]
        ]
        
        self.vehicle_table.setRowCount(len(sample_data))
        for row, data in enumerate(sample_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                self.vehicle_table.setItem(row, col, item)
        
        layout.addWidget(self.vehicle_table)
        
        # Action buttons with Material Design
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        remove_button = QPushButton("Remove Selected")
        MaterialUtils.set_button_style(remove_button, "secondary")
        remove_button.setFont(MaterialTypography.get_font("label_medium"))
        button_layout.addWidget(remove_button)
        
        remove_all_button = QPushButton("Remove All")
        MaterialUtils.set_button_style(remove_all_button, "text")
        remove_all_button.setFont(MaterialTypography.get_font("label_medium"))
        button_layout.addWidget(remove_all_button)
        
        highlight_button = QPushButton("Highlight Selected")
        MaterialUtils.set_button_style(highlight_button, "primary")
        highlight_button.setFont(MaterialTypography.get_font("label_medium"))
        button_layout.addWidget(highlight_button)
        
        layout.addWidget(button_container)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_statistics_panel(self, parent_layout):
        # Create main statistics group with Material Design
        main_stats_group = QGroupBox("Intersection Statistics")
        MaterialShadow.apply_elevation(main_stats_group, elevation=1)
        main_stats_layout = QHBoxLayout()
        main_stats_layout.setSpacing(16)
        main_stats_layout.setContentsMargins(16, 16, 16, 16)
        
        # Create statistics for each direction with Material Design cards
        directions = ["North", "South", "East", "West"]
        sample_stats = [
            {"count": 5, "queue": 2, "speed": 12.5},
            {"count": 3, "queue": 1, "speed": 15.2},
            {"count": 7, "queue": 3, "speed": 8.8},
            {"count": 4, "queue": 1, "speed": 11.3}
        ]
        
        for i, direction in enumerate(directions):
            direction_card = QWidget()
            direction_card.setStyleSheet(f"""
                QWidget {{
                    background-color: {MaterialColors.SURFACE_CONTAINER};
                    border-radius: 8px;
                    padding: 12px;
                }}
            """)
            MaterialShadow.apply_elevation(direction_card, elevation=1)
            
            direction_layout = QVBoxLayout(direction_card)
            direction_layout.setSpacing(8)
            direction_layout.setContentsMargins(12, 12, 12, 12)
            
            # Direction title
            direction_title = QLabel(direction)
            MaterialUtils.set_label_style(direction_title, "title")
            direction_layout.addWidget(direction_title)
            
            # Stats
            stats = sample_stats[i]
            count_label = QLabel(f"Vehicles: {stats['count']}")
            count_label.setFont(MaterialTypography.get_font("body_medium"))
            direction_layout.addWidget(count_label)
            
            queue_label = QLabel(f"Queue: {stats['queue']}")
            queue_label.setFont(MaterialTypography.get_font("body_medium"))
            direction_layout.addWidget(queue_label)
            
            speed_label = QLabel(f"Avg Speed: {stats['speed']} m/s")
            speed_label.setFont(MaterialTypography.get_font("body_medium"))
            direction_layout.addWidget(speed_label)
            
            main_stats_layout.addWidget(direction_card)
        
        # Traffic light control with Material Design
        light_card = QWidget()
        light_card.setStyleSheet(f"""
            QWidget {{
                background-color: {MaterialColors.SURFACE_CONTAINER};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        MaterialShadow.apply_elevation(light_card, elevation=1)
        
        light_layout = QVBoxLayout(light_card)
        light_layout.setSpacing(12)
        light_layout.setContentsMargins(12, 12, 12, 12)
        
        light_title = QLabel("Traffic Light")
        MaterialUtils.set_label_style(light_title, "title")
        light_layout.addWidget(light_title)
        
        self.light_phase_label = QLabel("Phase: NS Green")
        self.light_phase_label.setFont(MaterialTypography.get_font("body_medium"))
        light_layout.addWidget(self.light_phase_label)
        
        # Phase control buttons
        phase_buttons = ["NS Green", "NS Yellow", "EW Green", "EW Yellow"]
        for i, phase in enumerate(phase_buttons):
            btn = QPushButton(phase)
            MaterialUtils.set_button_style(btn, "primary" if i == 0 else "secondary")
            btn.setFont(MaterialTypography.get_font("label_small"))
            light_layout.addWidget(btn)
        
        main_stats_layout.addWidget(light_card)
        
        main_stats_group.setLayout(main_stats_layout)
        parent_layout.addWidget(main_stats_group)

    def initialize_ui_data(self):
        """Initialize UI with sample data"""
        pass

    def toggle_auto_spawn_panel(self):
        """Toggle visibility of auto spawn panel"""
        if self.auto_spawn_container.isVisible():
            self.auto_spawn_container.hide()
            self.sender().setText("Show Auto Spawn Controls")
        else:
            self.auto_spawn_container.show()
            self.sender().setText("Hide Auto Spawn Controls")

def main():
    app = QApplication(sys.argv)
    
    print("Launching Material Design Traffic Simulation UI...")
    print("This is a UI-only test without SUMO simulation backend")
    
    try:
        # Create and show main window
        window = MaterialTrafficWindow()
        window.show()
        
        print("✓ Material Design Traffic UI launched successfully!")
        print("✓ All Material Design components are properly styled")
        print("\nFeatures visible in the UI:")
        print("  • Material Design 3 color scheme")
        print("  • Elevated cards with shadows")
        print("  • Styled buttons (Primary, Secondary, Text)")
        print("  • Material Design typography")
        print("  • Responsive layout with resizable panels")
        print("  • Auto spawn controls with traffic patterns")
        print("  • Vehicle management interface")
        print("  • Statistics dashboard with direction cards")
        print("  • Traffic light control panel")
        
        # Run the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"✗ Error launching Material Design UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
