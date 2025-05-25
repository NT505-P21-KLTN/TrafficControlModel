from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QComboBox, 
                            QLineEdit, QTableWidget, QTableWidgetItem, QGroupBox,
                            QCheckBox, QSlider, QSpinBox, QRadioButton, QFrame, QHeaderView,
                            QSplitter, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon
from add_vehicle import SimulationThread
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import traci
import random
import os
import sys
from sumolib import checkBinary
from material_theme import (MaterialStylesheet, MaterialShadow, MaterialUtils, 
                          MaterialColors, MaterialTypography, MaterialAnimations)



class MainWindow(QMainWindow):
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

        # Create simulation thread FIRST
        self.sim_thread = SimulationThread()
        self.sim_thread.step_updated.connect(self.update_step)
        self.sim_thread.vehicle_updated.connect(self.update_vehicles)
        self.sim_thread.stats_updated.connect(self.update_statistics)
        self.sim_thread.cumulative_stats_updated.connect(self.update_cumulative_statistics)

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
        toggle_button.clicked.connect(self.toggle_auto_spawn_panel)
        left_layout.addWidget(toggle_button)
        
        # Create auto spawn controls container
        self.auto_spawn_container = QWidget()
        auto_spawn_layout = QVBoxLayout(self.auto_spawn_container)
        self.create_auto_spawn_panel(auto_spawn_layout)
        left_layout.addWidget(self.auto_spawn_container)
        
        # Create plot for average statistics
        plot_group = QGroupBox("Road Statistics Plots")
        plot_layout = QVBoxLayout()
        
        # Create matplotlib figure with 4 subplots in a column
        self.figure = Figure(figsize=(8, 12))  # Taller figure for vertical layout
        self.canvas = FigureCanvas(self.figure)
        
        # Create 4 subplots in a column
        self.axes = {
            'N2TL': self.figure.add_subplot(411),  # Changed to 4x1 layout
            'S2TL': self.figure.add_subplot(412),
            'E2TL': self.figure.add_subplot(413),
            'W2TL': self.figure.add_subplot(414)
        }
        
        # Initialize plot data for each road
        self.plot_data = {
            'steps': [],
            'N2TL': {'queue': [], 'wait': [], 'length': []},
            'S2TL': {'queue': [], 'wait': [], 'length': []},
            'E2TL': {'queue': [], 'wait': [], 'length': []},
            'W2TL': {'queue': [], 'wait': [], 'length': []}
        }
        
        # Set up plots
        for road, ax in self.axes.items():
            ax.set_title(f'{road} Statistics')
            ax.set_xlabel('Simulation Steps')
            ax.set_ylabel('Value')
            ax.grid(True)
            ax.legend(['Queue', 'Wait Time', 'Queue Length'])
        
        # Adjust layout to prevent overlap
        self.figure.tight_layout(pad=3.0)
        
        # Add canvas to layout
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)
        left_layout.addWidget(plot_group)
        
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

        # Initialize vehicle counter
        self.vehicle_counter = 0

        # Show window
        self.show()
    
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
        self.start_button.clicked.connect(self.toggle_simulation)
        layout.addWidget(self.start_button)
        
        # Render mode toggle - Secondary style
        self.render_mode_check = QCheckBox("Simple Shapes")
        self.render_mode_check.setChecked(True)
        self.render_mode_check.setFont(MaterialTypography.get_font("body_medium"))
        self.render_mode_check.stateChanged.connect(self.toggle_render_mode)
        layout.addWidget(self.render_mode_check)
        
        # Status label - Title style
        self.status_label = QLabel("Status: Not running")
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
        self.speed_slider.valueChanged.connect(self.update_speed)
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
        
        # Basic controls container
        basic_container = QWidget()
        basic_layout = QVBoxLayout(basic_container)
        basic_layout.setSpacing(16)
        
        # Enable/disable auto spawn
        self.auto_spawn_check = QCheckBox("Enable Auto Spawn")
        self.auto_spawn_check.setChecked(True)
        self.auto_spawn_check.setFont(MaterialTypography.get_font("body_large"))
        self.auto_spawn_check.stateChanged.connect(self.toggle_auto_spawn)
        basic_layout.addWidget(self.auto_spawn_check)
        
        # Initialize auto spawn as enabled in the simulation thread
        self.sim_thread.auto_spawn = True
        
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
            radio.clicked.connect(lambda checked, idx=i+1: self.apply_distribution_preset(idx) if checked else None)
            self.preset_buttons.append(radio)
            preset_layout.addWidget(radio)
        
        preset_group.setLayout(preset_layout)
        basic_layout.addWidget(preset_group)
        
        # Spawn interval with Material Design styling
        interval_group = QGroupBox("Spawn Interval")
        MaterialShadow.apply_elevation(interval_group, elevation=1)
        interval_layout = QVBoxLayout()
        interval_layout.setSpacing(12)
        
        # Fixed interval controls
        fixed_interval_container = QWidget()
        fixed_interval_layout = QHBoxLayout(fixed_interval_container)
        fixed_interval_layout.setContentsMargins(0, 0, 0, 0)
        
        fixed_label = QLabel("Fixed:")
        fixed_label.setFont(MaterialTypography.get_font("label_medium"))
        fixed_interval_layout.addWidget(fixed_label)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(100)
        self.interval_spin.setValue(4)
        self.interval_spin.valueChanged.connect(self.update_spawn_interval)
        fixed_interval_layout.addWidget(self.interval_spin)
        interval_layout.addWidget(fixed_interval_container)
        
        # Random interval controls
        self.random_interval_check = QCheckBox("Random Interval")
        self.random_interval_check.setChecked(True)
        self.random_interval_check.setFont(MaterialTypography.get_font("body_medium"))
        self.random_interval_check.stateChanged.connect(self.toggle_random_interval)
        interval_layout.addWidget(self.random_interval_check)
        
        # Min/Max interval controls
        min_max_container = QWidget()
        min_max_layout = QHBoxLayout(min_max_container)
        min_max_layout.setContentsMargins(0, 0, 0, 0)
        
        min_label = QLabel("Min:")
        min_label.setFont(MaterialTypography.get_font("label_small"))
        min_max_layout.addWidget(min_label)
        
        self.min_interval_spin = QSpinBox()
        self.min_interval_spin.setMinimum(1)
        self.min_interval_spin.setMaximum(50)
        self.min_interval_spin.setValue(4)
        self.min_interval_spin.valueChanged.connect(self.update_min_interval)
        min_max_layout.addWidget(self.min_interval_spin)
        
        max_label = QLabel("Max:")
        max_label.setFont(MaterialTypography.get_font("label_small"))
        min_max_layout.addWidget(max_label)
        
        self.max_interval_spin = QSpinBox()
        self.max_interval_spin.setMinimum(1)
        self.max_interval_spin.setMaximum(100)
        self.max_interval_spin.setValue(15)
        self.max_interval_spin.valueChanged.connect(self.update_max_interval)
        min_max_layout.addWidget(self.max_interval_spin)
        
        interval_layout.addWidget(min_max_container)
        interval_group.setLayout(interval_layout)
        basic_layout.addWidget(interval_group)
        
        # Vehicle count controls
        count_group = QGroupBox("Vehicles per Spawn")
        MaterialShadow.apply_elevation(count_group, elevation=1)
        count_layout = QVBoxLayout()
        count_layout.setSpacing(12)
        
        # Fixed count controls
        fixed_count_container = QWidget()
        fixed_count_layout = QHBoxLayout(fixed_count_container)
        fixed_count_layout.setContentsMargins(0, 0, 0, 0)
        
        count_label = QLabel("Fixed:")
        count_label.setFont(MaterialTypography.get_font("label_medium"))
        fixed_count_layout.addWidget(count_label)
        
        self.count_spin = QSpinBox()
        self.count_spin.setMinimum(1)
        self.count_spin.setMaximum(10)
        self.count_spin.setValue(5)
        self.count_spin.valueChanged.connect(self.update_spawn_count)
        fixed_count_layout.addWidget(self.count_spin)
        count_layout.addWidget(fixed_count_container)
        
        # Random count controls
        self.random_count_check = QCheckBox("Random Count")
        self.random_count_check.setChecked(True)
        self.random_count_check.setFont(MaterialTypography.get_font("body_medium"))
        self.random_count_check.stateChanged.connect(self.toggle_random_count)
        count_layout.addWidget(self.random_count_check)
        
        # Min/Max count controls
        min_max_count_container = QWidget()
        min_max_count_layout = QHBoxLayout(min_max_count_container)
        min_max_count_layout.setContentsMargins(0, 0, 0, 0)
        
        min_count_label = QLabel("Min:")
        min_count_label.setFont(MaterialTypography.get_font("label_small"))
        min_max_count_layout.addWidget(min_count_label)
        
        self.min_count_spin = QSpinBox()
        self.min_count_spin.setMinimum(1)
        self.min_count_spin.setMaximum(5)
        self.min_count_spin.setValue(1)
        self.min_count_spin.valueChanged.connect(self.update_min_count)
        min_max_count_layout.addWidget(self.min_count_spin)
        
        max_count_label = QLabel("Max:")
        max_count_label.setFont(MaterialTypography.get_font("label_small"))
        min_max_count_layout.addWidget(max_count_label)
        
        self.max_count_spin = QSpinBox()
        self.max_count_spin.setMinimum(1)
        self.max_count_spin.setMaximum(10)
        self.max_count_spin.setValue(6)
        self.max_count_spin.valueChanged.connect(self.update_max_count)
        min_max_count_layout.addWidget(self.max_count_spin)
        
        count_layout.addWidget(min_max_count_container)
        count_group.setLayout(count_layout)
        basic_layout.addWidget(count_group)
        
        layout.addWidget(basic_container)
        
        # In the create_auto_spawn_panel method, modify the vehicle type distribution section:
# Around line 225-262

        # Vehicle type distribution with Material Design
        type_group = QGroupBox("Vehicle Type Distribution")
        MaterialShadow.apply_elevation(type_group, elevation=1)
        type_container = QWidget()
        type_layout = QVBoxLayout(type_container)
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
            slider.valueChanged.connect(lambda v, t=vehicle_type: self.update_vehicle_type_distribution(t, v))
            self.type_sliders[vehicle_type] = slider
            slider_layout.addWidget(slider)
            
            percentage_label = QLabel(f"{percentage}%")
            percentage_label.setFont(MaterialTypography.get_font("label_small"))
            percentage_label.setMinimumWidth(40)
            slider_layout.addWidget(percentage_label)
            self.type_sliders[f"{vehicle_type}_label"] = percentage_label
            
            type_layout.addWidget(slider_container)
        
        # Remove scrolling - just use the container directly
        type_group_layout = QVBoxLayout()
        type_group_layout.addWidget(type_container)
        type_group.setLayout(type_group_layout)
        layout.addWidget(type_group)
        
        # Route distribution with Material Design
        route_group = QGroupBox("Route Distribution")
        MaterialShadow.apply_elevation(route_group, elevation=1)
        route_container = QWidget()
        route_layout = QVBoxLayout(route_container)
        route_layout.setSpacing(8)
        
        self.route_sliders = {}
        for route, weight in self.sim_thread.route_weights.items():
            route_container_item = QWidget()
            route_slider_layout = QHBoxLayout(route_container_item)
            route_slider_layout.setContentsMargins(0, 0, 0, 0)
            
            route_label = QLabel(f"{route}:")
            route_label.setFont(MaterialTypography.get_font("body_small"))
            route_label.setMinimumWidth(60)
            route_slider_layout.addWidget(route_label)
            
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(100)
            slider.setValue(weight)
            slider.valueChanged.connect(lambda v, r=route: self.update_route_distribution(r, v))
            self.route_sliders[route] = slider
            route_slider_layout.addWidget(slider)
            
            weight_label = QLabel(f"{weight}%")
            weight_label.setFont(MaterialTypography.get_font("label_small"))
            weight_label.setMinimumWidth(40)
            route_slider_layout.addWidget(weight_label)
            self.route_sliders[f"{route}_label"] = weight_label
            
            route_layout.addWidget(route_container_item)
        
        # Remove scrolling - just use the container directly
        route_group_layout = QVBoxLayout()
        route_group_layout.addWidget(route_container)
        route_group.setLayout(route_group_layout)
        layout.addWidget(route_group)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
        # Set N-S Dominant as default after all UI elements are created
        self.preset_buttons[4].setChecked(True)  # Index 4 is N-S Dominant
        self.apply_distribution_preset(5)  # Apply N-S Dominant preset
    
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
        
        # Lane selection
        lane_container = QWidget()
        lane_layout = QVBoxLayout(lane_container)
        lane_layout.setContentsMargins(0, 0, 0, 0)
        
        lane_label = QLabel("Lane:")
        lane_label.setFont(MaterialTypography.get_font("label_medium"))
        lane_layout.addWidget(lane_label)
        
        self.lane_combo = QComboBox()
        self.lane_combo.addItems(["random", "0", "1", "2", "3"])
        lane_layout.addWidget(self.lane_combo)
        layout.addWidget(lane_container)
        
        # Action buttons
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        
        add_button = QPushButton("Add Vehicle")
        MaterialUtils.set_button_style(add_button, "primary")
        add_button.setFont(MaterialTypography.get_font("label_medium"))
        add_button.clicked.connect(self.add_vehicle)
        button_layout.addWidget(add_button)
        
        random_button = QPushButton("Add 5 Random")
        MaterialUtils.set_button_style(random_button, "secondary")
        random_button.setFont(MaterialTypography.get_font("label_medium"))
        random_button.clicked.connect(self.add_random_vehicles)
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
        layout.addWidget(self.vehicle_table)
        
        # Action buttons with Material Design
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        remove_button = QPushButton("Remove Selected")
        MaterialUtils.set_button_style(remove_button, "secondary")
        remove_button.setFont(MaterialTypography.get_font("label_medium"))
        remove_button.clicked.connect(self.remove_vehicle)
        button_layout.addWidget(remove_button)
        
        remove_all_button = QPushButton("Remove All")
        MaterialUtils.set_button_style(remove_all_button, "text")
        remove_all_button.setFont(MaterialTypography.get_font("label_medium"))
        remove_all_button.clicked.connect(self.remove_all_vehicles)
        button_layout.addWidget(remove_all_button)
        
        highlight_button = QPushButton("Highlight Selected")
        MaterialUtils.set_button_style(highlight_button, "primary")
        highlight_button.setFont(MaterialTypography.get_font("label_medium"))
        highlight_button.clicked.connect(self.highlight_vehicle)
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
        for direction in ["North", "South", "East", "West"]:
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
            
            # Statistics labels
            count_label = QLabel("Count: 0")
            count_label.setFont(MaterialTypography.get_font("body_medium"))
            queue_label = QLabel("Queue: 0")
            queue_label.setFont(MaterialTypography.get_font("body_medium"))
            speed_label = QLabel("Speed: 0 m/s")
            speed_label.setFont(MaterialTypography.get_font("body_medium"))
            
            direction_layout.addWidget(count_label)
            direction_layout.addWidget(queue_label)
            direction_layout.addWidget(speed_label)
            
            setattr(self, f"{direction.lower()}_count", count_label)
            setattr(self, f"{direction.lower()}_queue", queue_label)
            setattr(self, f"{direction.lower()}_speed", speed_label)
            
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
        
        self.light_phase_label = QLabel("Phase: N/A")
        self.light_phase_label.setFont(MaterialTypography.get_font("body_medium"))
        light_layout.addWidget(self.light_phase_label)
        
        self.manual_control = QCheckBox("Manual Control")
        self.manual_control.setFont(MaterialTypography.get_font("body_medium"))
        light_layout.addWidget(self.manual_control)
        
        phase_layout = QHBoxLayout()
        phase_layout.setSpacing(8)
        for i, name in enumerate(["NS", "NSL", "EW", "EWL"]):
            button = QPushButton(name)
            MaterialUtils.set_button_style(button, "secondary")
            button.setFont(MaterialTypography.get_font("label_small"))
            button.clicked.connect(lambda checked, i=i: self.set_traffic_light_phase(i*2))
            phase_layout.addWidget(button)
        
        light_layout.addLayout(phase_layout)
        main_stats_layout.addWidget(light_card)
        
        main_stats_group.setLayout(main_stats_layout)
        parent_layout.addWidget(main_stats_group)
        
        # Create cumulative statistics group with Material Design
        cumulative_stats_group = QGroupBox("Cumulative Statistics")
        MaterialShadow.apply_elevation(cumulative_stats_group, elevation=1)
        cumulative_stats_layout = QVBoxLayout()
        cumulative_stats_layout.setContentsMargins(16, 16, 16, 16)
        cumulative_stats_layout.setSpacing(12)
        
        # Create statistics table with Material Design styling
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(14)
        self.stats_table.setRowCount(5)
        
        # Set headers with Material Design typography
        headers = [
            "Road", "Current Queue", "Current Wait", "Current Vehicles", "Current Length",
            "Total Queue", "Total Wait", "Total Vehicles", "Total Length",
            "Max Queue", "Max Wait", "Avg Queue", "Avg Wait", "Avg Length"
        ]
        self.stats_table.setHorizontalHeaderLabels(headers)
        
        # Set row labels
        row_labels = ["Global", "N2TL", "S2TL", "E2TL", "W2TL"]
        self.stats_table.setVerticalHeaderLabels(row_labels)
        
        # Initialize cells with Material Design styling
        for row in range(5):
            for col in range(14):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(MaterialTypography.get_font("body_small"))
                self.stats_table.setItem(row, col, item)
        
        # Apply Material Design table styling
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.stats_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Set header fonts
        header_font = MaterialTypography.get_font("label_medium")
        self.stats_table.horizontalHeader().setFont(header_font)
        self.stats_table.verticalHeader().setFont(header_font)
        
        cumulative_stats_layout.addWidget(self.stats_table)
        
        # Add legend with Material Design typography
        legend_container = QWidget()
        legend_layout = QHBoxLayout(legend_container)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(8)
        
        units_label = QLabel("Units:")
        units_label.setFont(MaterialTypography.get_font("label_medium"))
        legend_layout.addWidget(units_label)
        
        legend_text = QLabel("Queue: vehicles | Wait: seconds | Length: meters")
        legend_text.setFont(MaterialTypography.get_font("body_small"))
        legend_layout.addWidget(legend_text)
        
        cumulative_stats_layout.addWidget(legend_container)
        cumulative_stats_group.setLayout(cumulative_stats_layout)
        parent_layout.addWidget(cumulative_stats_group)
    
    def toggle_simulation(self):
        if not self.sim_thread.running:
            self.sim_thread.running = True
            self.sim_thread.start()
            self.start_button.setText("Stop Simulation")
            self.status_label.setText("Status: Running")
        else:
            self.sim_thread.running = False
            self.start_button.setText("Start Simulation")
            self.status_label.setText("Status: Stopped")
    
    def update_speed(self, value):
        self.sim_thread.speed = value
    
    def update_step(self, step):
        self.step_label.setText(f"Steps: {step}")
    
    def update_vehicles(self, vehicles):
        """Update the vehicle table with current vehicle data"""
        self.vehicle_table.setRowCount(len(vehicles))
        for row, (vid, data) in enumerate(vehicles.items()):
            try:
                # Handle both dictionary and string data formats
                if isinstance(data, dict):
                    vehicle_type = data.get('type', 'standard_car')
                    route = data.get('route', '')
                    road = data.get('road', '')
                    lane = str(data.get('lane', ''))
                    speed = str(data.get('speed', '0'))
                    waiting = str(data.get('waiting', '0'))
                else:
                    # If data is a string, try to parse it
                    vehicle_type = 'standard_car'
                    route = ''
                    road = ''
                    lane = ''
                    speed = '0'
                    waiting = '0'
                    
                    # Try to extract vehicle type from the ID
                    if '_' in vid:
                        parts = vid.split('_')
                        if len(parts) >= 2:
                            vehicle_type = parts[0]
                            if len(parts) >= 3:
                                route = parts[1] + '_' + parts[2]
                
                self.vehicle_table.setItem(row, 0, QTableWidgetItem(vid))
                self.vehicle_table.setItem(row, 1, QTableWidgetItem(vehicle_type))
                self.vehicle_table.setItem(row, 2, QTableWidgetItem(route))
                self.vehicle_table.setItem(row, 3, QTableWidgetItem(road))
                self.vehicle_table.setItem(row, 4, QTableWidgetItem(lane))
                self.vehicle_table.setItem(row, 5, QTableWidgetItem(speed))
                self.vehicle_table.setItem(row, 6, QTableWidgetItem(waiting))
            except Exception as e:
                print(f"Error updating vehicle row {row} for vehicle {vid}: {e}")
                # Set default values if there's an error
                self.vehicle_table.setItem(row, 0, QTableWidgetItem(vid))
                self.vehicle_table.setItem(row, 1, QTableWidgetItem('unknown'))
                self.vehicle_table.setItem(row, 2, QTableWidgetItem(''))
                self.vehicle_table.setItem(row, 3, QTableWidgetItem(''))
                self.vehicle_table.setItem(row, 4, QTableWidgetItem(''))
                self.vehicle_table.setItem(row, 5, QTableWidgetItem('0'))
                self.vehicle_table.setItem(row, 6, QTableWidgetItem('0'))
    
    def update_statistics(self, stats):
        for direction in ["north", "south", "east", "west"]:
            if direction in stats:
                getattr(self, f"{direction}_count").setText(f"Count: {stats[direction]['count']}")
                getattr(self, f"{direction}_queue").setText(f"Queue: {stats[direction]['queue']}")
                getattr(self, f"{direction}_speed").setText(f"Speed: {stats[direction]['speed']:.1f} m/s")
        
        if 'light_phase' in stats:
            phase_names = ["NS Green", "NS Yellow", "NSL Green", "NSL Yellow", 
                          "EW Green", "EW Yellow", "EWL Green", "EWL Yellow"]
            phase = stats['light_phase']
            if 0 <= phase < len(phase_names):
                self.light_phase_label.setText(f"Phase: {phase_names[phase]}")
            else:
                self.light_phase_label.setText(f"Phase: {phase}")
    
    def add_vehicle(self):
        if not self.sim_thread.running:
            return
        
        try:
            route = self.route_combo.currentText()
            vehicle_type = self.vehicle_type_combo.currentText()
            speed = float(self.speed_input.text())
            lane = self.lane_combo.currentText()
            
            vehicle_id = f"{vehicle_type}_{route}_{self.vehicle_counter}"
            self.vehicle_counter += 1
        
            traci.vehicle.add(
                vehID=vehicle_id,
                routeID=route,
                typeID=vehicle_type,
                departLane=lane,
                departSpeed=str(speed)
            )
        except Exception as e:
            print(f"Error adding vehicle: {e}")
    
    def add_random_vehicles(self):
        if not self.sim_thread.running:
            return
        
        for _ in range(5):
            self.route_combo.setCurrentIndex(random.randint(0, self.route_combo.count()-1))
            self.vehicle_type_combo.setCurrentIndex(random.randint(0, self.vehicle_type_combo.count()-1))
            self.speed_input.setText(str(random.uniform(5, 15)))
            self.lane_combo.setCurrentIndex(random.randint(0, self.lane_combo.count()-1))
            self.add_vehicle()
    
    def remove_vehicle(self):
        if not self.sim_thread.running:
            return
        
        selected = self.vehicle_table.selectedItems()
        if selected:
            vehicle_id = self.vehicle_table.item(selected[0].row(), 0).text()
            try:
                traci.vehicle.remove(vehicle_id)
            except Exception as e:
                print(f"Error removing vehicle: {e}")
    
    def remove_all_vehicles(self):
        if not self.sim_thread.running:
            return
        
        try:
            for vid in traci.vehicle.getIDList():
                traci.vehicle.remove(vid)
        except Exception as e:
            print(f"Error removing vehicles: {e}")
    
    def highlight_vehicle(self):
        if not self.sim_thread.running:
            return
        
        selected = self.vehicle_table.selectedItems()
        if selected:
            vehicle_id = self.vehicle_table.item(selected[0].row(), 0).text()
            try:
                traci.vehicle.setColor(vehicle_id, (255, 255, 0, 255))
                traci.gui.trackVehicle("View #0", vehicle_id)
                traci.gui.setZoom("View #0", 3000)
            except Exception as e:
                print(f"Error highlighting vehicle: {e}")
    
    def set_traffic_light_phase(self, phase):
        if not self.sim_thread.running:
            return
        
        try:
            traci.trafficlight.setPhase("TL", phase)
        except Exception as e:
            print(f"Error setting traffic light phase: {e}")

    def toggle_auto_spawn(self, state):
        self.sim_thread.auto_spawn = bool(state)
    
    def update_spawn_interval(self, value):
        self.sim_thread.spawn_interval = value
    
    def update_spawn_count(self, value):
        self.sim_thread.spawn_count = value
    
    def toggle_random_interval(self, state):
        self.sim_thread.spawn_interval_random = bool(state)
        self.min_interval_spin.setEnabled(state)
        self.max_interval_spin.setEnabled(state)
    
    def toggle_random_count(self, state):
        self.sim_thread.spawn_count_random = bool(state)
        self.min_count_spin.setEnabled(state)
        self.max_count_spin.setEnabled(state)
    
    def update_min_interval(self, value):
        self.sim_thread.min_interval = value
        if value > self.max_interval_spin.value():
            self.max_interval_spin.setValue(value)
    
    def update_max_interval(self, value):
        self.sim_thread.max_interval = value
        if value < self.min_interval_spin.value():
            self.min_interval_spin.setValue(value)
    
    def update_min_count(self, value):
        self.sim_thread.min_count = value
        if value > self.max_count_spin.value():
            self.max_count_spin.setValue(value)
    
    def update_max_count(self, value):
        self.sim_thread.max_count = value
        if value < self.min_count_spin.value():
            self.min_count_spin.setValue(value)
    
    def update_vehicle_type_distribution(self, vehicle_type, value):
        self.sim_thread.vehicle_types[vehicle_type] = value
        self.type_sliders[f"{vehicle_type}_label"].setText(f"{value}%")
    
    def update_route_distribution(self, route, value):
        self.sim_thread.route_weights[route] = value
        self.route_sliders[f"{route}_label"].setText(f"{value}%")

    def toggle_render_mode(self, state):
        try:
            if state:
                # Switch to simple shapes
                view_file = os.path.join('intersection', 'view.xml')
                with open(view_file, 'w') as f:
                    f.write("""<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <scheme name="standard"/>
    <delay value="20"/>
    <vehicleMode value="0"/>
    <vehicleQuality value="0"/>
    <vehicleName value="0"/>
    <vehicleSize value="1.0"/>
    <vehicleNameShow value="0"/>
    <vehicleNameSize value="50"/>
    <vehicleNameColor value="0,0,0"/>
    <vehicleNameBackground value="0"/>
    <vehicleNameBackgroundColor value="255,255,255"/>
    <vehicleNameBackgroundAlpha value="0.5"/>
    <vehicleNameBackgroundSize value="0.5"/>
    <vehicleNameBackgroundOffset value="0.0"/>
    <vehicleNameBackgroundRotation value="0.0"/>
    <vehicleNameBackgroundScale value="1.0"/>
    <minGap value="0.5"/>
</viewsettings>""")
            else:
                # Switch to real world rendering
                view_file = os.path.join('intersection', 'view.xml')
                with open(view_file, 'w') as f:
                    f.write("""<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <scheme name="real world"/>
    <delay value="20"/>
    <vehicleMode value="9"/>
    <vehicleQuality value="3"/>
    <vehicleName value="0"/>
    <vehicleSize value="1.0"/>
    <vehicleNameShow value="0"/>
    <vehicleNameSize value="50"/>
    <vehicleNameColor value="0,0,0"/>
    <vehicleNameBackground value="0"/>
    <vehicleNameBackgroundColor value="255,255,255"/>
    <vehicleNameBackgroundAlpha value="0.5"/>
    <vehicleNameBackgroundSize value="0.5"/>
    <vehicleNameBackgroundOffset value="0.0"/>
    <vehicleNameBackgroundRotation value="0.0"/>
    <vehicleNameBackgroundScale value="1.0"/>
    <minGap value="2.5"/>
</viewsettings>""")            
            print("Render mode toggled: ", state)
            
        except Exception as e:
            print(f"Error toggling render mode: {e}")

    def apply_distribution_preset(self, preset_num):
        if preset_num == 1:  # Urban Rush Hour
            # More passenger cars, some buses, few trucks
            self.sim_thread.vehicle_types = {
                "veh_passenger": 75,
                "veh_bus": 15,
                "veh_truck": 5,
                "veh_emergency": 3,
                "veh_motorcycle": 2
            }
            # More traffic on main roads
            self.sim_thread.route_weights = {
                "W_N": 12, "W_E": 15, "W_S": 8,
                "N_W": 8, "N_E": 15, "N_S": 12,
                "E_N": 15, "E_S": 8, "E_W": 12,
                "S_N": 8, "S_E": 12, "S_W": 15
            }
        elif preset_num == 2:  # Highway Traffic
            # More trucks, fewer passenger cars
            self.sim_thread.vehicle_types = {
                "veh_passenger": 45,
                "veh_bus": 10,
                "veh_truck": 35,
                "veh_emergency": 5,
                "veh_motorcycle": 5
            }
            # More through traffic
            self.sim_thread.route_weights = {
                "W_N": 10, "W_E": 20, "W_S": 10,
                "N_W": 10, "N_E": 20, "N_S": 10,
                "E_N": 10, "E_S": 20, "E_W": 10,
                "S_N": 10, "S_E": 20, "S_W": 10
            }
        elif preset_num == 3:  # Mixed Traffic
            # Even distribution of vehicle types
            self.sim_thread.vehicle_types = {
                "veh_passenger": 40,
                "veh_bus": 20,
                "veh_truck": 20,
                "veh_emergency": 10,
                "veh_motorcycle": 10
            }
            # Even distribution of routes
            self.sim_thread.route_weights = {
                "W_N": 8, "W_E": 8, "W_S": 8,
                "N_W": 8, "N_E": 8, "N_S": 8,
                "E_N": 8, "E_S": 8, "E_W": 8,
                "S_N": 8, "S_E": 8, "S_W": 8
            }
        elif preset_num == 4:  # Emergency Heavy
            # More emergency vehicles
            self.sim_thread.vehicle_types = {
                "veh_passenger": 30,
                "veh_bus": 10,
                "veh_truck": 10,
                "veh_emergency": 40,
                "veh_motorcycle": 10
            }
            # More traffic on emergency routes
            self.sim_thread.route_weights = {
                "W_N": 15, "W_E": 5, "W_S": 15,
                "N_W": 5, "N_E": 15, "N_S": 5,
                "E_N": 15, "E_S": 5, "E_W": 15,
                "S_N": 5, "S_E": 15, "S_W": 5
            }
        elif preset_num == 5:  # North-South Dominant
            # High passenger and motorcycle, low truck
            self.sim_thread.vehicle_types = {
                "veh_passenger": 45,
                "veh_bus": 10,
                "veh_truck": 2,
                "veh_emergency": 3,
                "veh_motorcycle": 40
            }
            # Heavy N-S traffic
            self.sim_thread.route_weights = {
                "W_N": 5, "W_E": 10, "W_S": 5,
                "N_W": 15, "N_E": 5, "N_S": 15,
                "E_N": 15, "E_S": 5, "E_W": 10,
                "S_N": 15, "S_E": 5, "S_W": 5
            }
        elif preset_num == 6:  # East-West Dominant
            # More passenger than motorcycle
            self.sim_thread.vehicle_types = {
                "veh_passenger": 55,
                "veh_bus": 12,
                "veh_truck": 1,
                "veh_emergency": 2,
                "veh_motorcycle": 30
            }
            # Heavy E-W traffic
            self.sim_thread.route_weights = {
                "W_N": 10, "W_E": 15, "W_S": 10,
                "N_W": 5, "N_E": 15, "N_S": 5,
                "E_N": 5, "E_S": 15, "E_W": 15,
                "S_N": 5, "S_E": 15, "S_W": 5
            }
        elif preset_num == 7:  # Diagonal Dominant
            # Equal passenger and motorcycle
            self.sim_thread.vehicle_types = {
                "veh_passenger": 40,
                "veh_bus": 8,
                "veh_truck": 2,
                "veh_emergency": 5,
                "veh_motorcycle": 45
            }
            # Heavy diagonal traffic
            self.sim_thread.route_weights = {
                "W_N": 15, "W_E": 5, "W_S": 5,
                "N_W": 5, "N_E": 15, "N_S": 5,
                "E_N": 5, "E_S": 15, "E_W": 5,
                "S_N": 5, "S_E": 5, "S_W": 15
            }
        elif preset_num == 8:  # Circular Flow
            # More motorcycle than passenger
            self.sim_thread.vehicle_types = {
                "veh_passenger": 35,
                "veh_bus": 7,
                "veh_truck": 1,
                "veh_emergency": 2,
                "veh_motorcycle": 55
            }
            # Circular traffic pattern
            self.sim_thread.route_weights = {
                "W_N": 15, "W_E": 5, "W_S": 5,
                "N_W": 5, "N_E": 15, "N_S": 5,
                "E_N": 5, "E_S": 15, "E_W": 5,
                "S_N": 5, "S_E": 5, "S_W": 15
            }
        
        # Update the UI sliders
        for vehicle_type, percentage in self.sim_thread.vehicle_types.items():
            self.type_sliders[vehicle_type].setValue(percentage)
            self.type_sliders[f"{vehicle_type}_label"].setText(f"{percentage}%")
        
        for route, weight in self.sim_thread.route_weights.items():
            self.route_sliders[route].setValue(weight)
            self.route_sliders[f"{route}_label"].setText(f"{weight}%")

    def toggle_auto_spawn_panel(self):
        sender = self.sender()
        if self.auto_spawn_container.isVisible():
            self.auto_spawn_container.hide()
            sender.setText("Show Auto Spawn Controls")
        else:
            self.auto_spawn_container.show()
            sender.setText("Hide Auto Spawn Controls")

    def update_cumulative_statistics(self, stats):
        # Update table statistics
        self.update_table_row(0, {
            'current': {
                'queue': stats['total_queue'],
                'waiting': stats['total_waiting_time'],
                'vehicles': stats['total_vehicles'],
                'length': stats['total_length']
            },
            'total': {
                'queue': stats['total_queue'],
                'waiting': stats['total_waiting_time'],
                'vehicles': stats['total_vehicles'],
                'length': stats['total_length']
            },
            'max': {
                'queue': stats['max_queue'],
                'waiting': stats['max_waiting_time']
            },
            'avg': {
                'queue': stats['average_queue'],
                'waiting': stats['average_waiting_time'],
                'length': stats['average_length']
            }
        })
        
        # Update per-road statistics
        for i, road_id in enumerate(['N2TL', 'S2TL', 'E2TL', 'W2TL'], 1):
            road_stats = stats['road_stats'][road_id]
            self.update_table_row(i, {
                'current': {
                    'queue': road_stats['current_queue'],
                    'waiting': road_stats['current_waiting_time'],
                    'vehicles': road_stats['current_vehicles'],
                    'length': road_stats['current_length']
                },
                'total': {
                    'queue': road_stats['total_queue'],
                    'waiting': road_stats['total_waiting_time'],
                    'vehicles': road_stats['total_vehicles'],
                    'length': road_stats['total_length']
                },
                'max': {
                    'queue': road_stats['max_queue'],
                    'waiting': road_stats['max_waiting_time']
                },
                'avg': {
                    'queue': road_stats['average_queue'],
                    'waiting': road_stats['average_waiting_time'],
                    'length': road_stats['average_length']
                }
            })
            
            # Update plot data for each road
            self.plot_data[road_id]['queue'].append(road_stats['current_queue'])
            self.plot_data[road_id]['wait'].append(road_stats['current_waiting_time'])
            self.plot_data[road_id]['length'].append(road_stats['current_length'])
        
        # Update steps
        self.plot_data['steps'].append(self.sim_thread.step)
        
        # Keep only last 100 points for better visualization
        max_points = 100
        if len(self.plot_data['steps']) > max_points:
            self.plot_data['steps'] = self.plot_data['steps'][-max_points:]
            for road in ['N2TL', 'S2TL', 'E2TL', 'W2TL']:
                self.plot_data[road]['queue'] = self.plot_data[road]['queue'][-max_points:]
                self.plot_data[road]['wait'] = self.plot_data[road]['wait'][-max_points:]
                self.plot_data[road]['length'] = self.plot_data[road]['length'][-max_points:]
        
        try:
            # Update plots for each road
            for road, ax in self.axes.items():
                ax.clear()
                ax.plot(self.plot_data['steps'], self.plot_data[road]['queue'], 
                       label='Queue', color='red', linewidth=2)
                ax.plot(self.plot_data['steps'], self.plot_data[road]['wait'], 
                       label='Wait Time', color='blue', linewidth=2)
                ax.plot(self.plot_data['steps'], self.plot_data[road]['length'], 
                       label='Queue Length', color='green', linewidth=2)
                ax.set_title(f'{road} Statistics')
                ax.set_xlabel('Simulation Steps')
                ax.set_ylabel('Queue (veh) / Wait Time (s)')
                ax.grid(True)
                ax.legend()
            
            # Use a more robust layout adjustment
            self.figure.subplots_adjust(
                left=0.1,
                right=0.9,
                top=0.95,
                bottom=0.05,
                hspace=0.3,
                wspace=0.2
            )
            
            self.canvas.draw()
        except Exception as e:
            print(f"Error updating plots: {e}")

    def update_table_row(self, row, stats):
        # Current stats
        self.stats_table.item(row, 1).setText(f"{stats['current']['queue']}")
        self.stats_table.item(row, 2).setText(f"{stats['current']['waiting']:.1f}s")
        self.stats_table.item(row, 3).setText(f"{stats['current']['vehicles']}")
        self.stats_table.item(row, 4).setText(f"{stats['current']['length']:.1f}m")
        
        # Total stats
        self.stats_table.item(row, 5).setText(f"{stats['total']['queue']}")
        self.stats_table.item(row, 6).setText(f"{stats['total']['waiting']:.1f}s")
        self.stats_table.item(row, 7).setText(f"{stats['total']['vehicles']}")
        self.stats_table.item(row, 8).setText(f"{stats['total']['length']:.1f}m")
        
        # Max stats
        self.stats_table.item(row, 9).setText(f"{stats['max']['queue']}")
        self.stats_table.item(row, 10).setText(f"{stats['max']['waiting']:.1f}s")
        
        # Average stats
        self.stats_table.item(row, 11).setText(f"{stats['avg']['queue']:.1f}")
        self.stats_table.item(row, 12).setText(f"{stats['avg']['waiting']:.1f}s")
        self.stats_table.item(row, 13).setText(f"{stats['avg']['length']:.1f}m")

    def _setup_traffic_light_controls(self):
        """Setup traffic light control buttons"""
        control_frame = QFrame()
        control_layout = QVBoxLayout()
        
        # Create button groups for each direction
        ns_group = QGroupBox("North-South")
        ns_layout = QVBoxLayout()
        self.ns_green_btn = QPushButton("NS Green")
        self.ns_yellow_btn = QPushButton("NS Yellow")
        ns_layout.addWidget(self.ns_green_btn)
        ns_layout.addWidget(self.ns_yellow_btn)
        ns_group.setLayout(ns_layout)
        
        ew_group = QGroupBox("East-West")
        ew_layout = QVBoxLayout()
        self.ew_green_btn = QPushButton("EW Green")
        self.ew_yellow_btn = QPushButton("EW Yellow")
        ew_layout.addWidget(self.ew_green_btn)
        ew_layout.addWidget(self.ew_yellow_btn)
        ew_group.setLayout(ew_layout)
        
        # Connect button signals
        self.ns_green_btn.clicked.connect(lambda: self._handle_traffic_light_click(0))  # NS Green
        self.ns_yellow_btn.clicked.connect(lambda: self._handle_traffic_light_click(1))  # NS Yellow
        self.ew_green_btn.clicked.connect(lambda: self._handle_traffic_light_click(4))  # EW Green
        self.ew_yellow_btn.clicked.connect(lambda: self._handle_traffic_light_click(5))  # EW Yellow
        
        control_layout.addWidget(ns_group)
        control_layout.addWidget(ew_group)
        control_frame.setLayout(control_layout)
        
        return control_frame

    def _handle_traffic_light_click(self, phase):
        """Handle traffic light control button clicks"""
        if not self.sim_thread.running:
            QMessageBox.warning(self, "Warning", "Simulation is not running")
            return
        
        try:
            self.sim_thread.set_traffic_light_phase(phase)
            print(f"Set traffic light phase to {phase}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set traffic light phase: {str(e)}")
            print(f"Error setting traffic light phase: {e}")

if __name__ == "__main__":
    # Initialize SUMO
    if 'SUMO_HOME' not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")
    
    # Set up SUMO command
    sumo_binary = checkBinary('sumo-gui')
    sumo_cmd = [sumo_binary, 
                '-c', 'intersection/sumo_config_interactive.sumocfg',
                '--no-step-log', 'true',
                '--no-warnings', 'true']
    
    # Create and show the main window
    app = QApplication(sys.argv)
    window = MainWindow()
    
    # Set the SUMO command in the simulation thread
    window.sim_thread._sumo_cmd = sumo_cmd
    
    sys.exit(app.exec_())
