from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os
import time
import threading
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import folium
from folium.plugins import MarkerCluster
import math
import xml.etree.ElementTree as ET
from collections import deque
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
# from mock_firebase_service import FirebaseService

app = Flask(__name__)
CORS(app)  # Cho phép truy cập từ Flutter Web
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Initialize Firebase service - TEMPORARILY DISABLED
# firebase = FirebaseService()

# Global variables
active_agents = {}
agent_configs = {}
agent_metrics = {}
training_sessions = {}  # Track training sessions

# Data storage
agent_data = {}
last_update = {}
analytics_data = {}  # Store analytics data
system_alerts = []   # Store system alerts
TIMEOUT_THRESHOLD = 60  # seconds until agent considered offline

# Store recent server logs
server_logs = deque(maxlen=100)  # Keep the last 100 logs

# Create directories for data storage
os.makedirs('server_data', exist_ok=True)
os.makedirs('server_data/figures', exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Define file paths
VEHICLE_TRANSFER_FILE = os.path.join(os.path.dirname(__file__), 'server_data', 'vehicle_transfers.json')

def log_event(message):
    """Add a message to the server logs with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    server_logs.append(log_entry)
    print(log_entry)

def generate_intersection_map():
    """Generate a map showing all connected intersections with their network structure"""
    # Default center coordinates
    default_center = [10.777807, 106.681676]

    # Create a map centered on the specified location
    m = folium.Map(location=default_center, zoom_start=15)

    # Create a marker cluster for better visualization
    marker_cluster = MarkerCluster().add_to(m)

    # Track intersections with valid location data
    valid_intersections = {}

    # Add markers for each agent with location data
    has_markers = False
    for agent_id, data in agent_data.items():
        # Check if location data exists
        if 'topology' in data and 'location' in data['topology']:
            location = data['topology']['location']
            if 'latitude' in location and 'longitude' in location:
                try:
                    lat = float(location['latitude'])
                    lng = float(location['longitude'])
                    name = location.get('intersection_name', f'Intersection {agent_id}')

                    # Determine agent status (online/offline)
                    is_online = agent_id in last_update and (time.time() - last_update[agent_id] <= TIMEOUT_THRESHOLD)
                    color = 'green' if is_online else 'red'

                    # Get performance data if available
                    queue_info = ""
                    if 'queue_lengths' in data and len(data['queue_lengths']) > 0:
                        avg_queue = sum(data['queue_lengths'][-10:]) / min(10, len(data['queue_lengths']))
                        queue_info = f"<br>Average queue: {avg_queue:.2f} vehicles"

                    # Create popup content with more detailed information
                    popup_content = f"""
                    <div style="width: 200px;">
                        <h3>{name}</h3>
                        <b>Agent ID:</b> {agent_id}<br>
                        <b>Status:</b> {'Online' if is_online else 'Offline'}{queue_info}<br>
                        <b>Location:</b> {lat:.6f}, {lng:.6f}
                    </div>
                    """

                    # Add marker to the cluster
                    folium.Marker(
                        location=[lat, lng],
                        popup=folium.Popup(popup_content, max_width=250),
                        tooltip=name,
                        icon=folium.Icon(color=color, icon='traffic-light', prefix='fa')
                    ).add_to(marker_cluster)

                    # Store the intersection for connection drawing
                    valid_intersections[agent_id] = {
                        'lat': lat,
                        'lng': lng,
                        'environment': data['topology'].get('environment', {}) if 'topology' in data else {},
                        'connected_to': data.get('connected_to', [])  # Get explicit connections
                    }

                    has_markers = True

                except (ValueError, TypeError) as e:
                    print(f"Error processing location for agent {agent_id}: {e}")

    # Draw connections between intersections based on explicit connections
    connections_drawn = set()
    for id1, info1 in valid_intersections.items():
        # Get list of connected intersections from config
        connected_to = info1.get('connected_to', [])
        if isinstance(connected_to, str):
            connected_to = [x.strip() for x in connected_to.split(',')]

        for id2 in connected_to:
            if id2 in valid_intersections and (id1, id2) not in connections_drawn and (id2, id1) not in connections_drawn:
                info2 = valid_intersections[id2]
                # Calculate distance for tooltip
                distance_km = haversine_distance(
                    (info1['lat'], info1['lng']),
                    (info2['lat'], info2['lng'])
                )

                folium.PolyLine(
                    locations=[(info1['lat'], info1['lng']), (info2['lat'], info2['lng'])],
                    color='blue',
                    weight=2,
                    opacity=0.7,
                    tooltip=f"Distance: {distance_km:.2f} km"
                ).add_to(m)
                connections_drawn.add((id1, id2))

    # If no valid markers were added, add a default one
    if not has_markers:
        folium.Marker(
            location=default_center,
            popup="Default Location (No Agent Data)",
            tooltip="Default Location",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)

    # Save to static directory for serving
    map_path = 'static/intersection_map.html'
    m.save(map_path)

    # Also save as template
    with open('templates/map.html', 'w', encoding='utf-8') as f:  # Add encoding='utf-8'
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Traffic Control Network - Map View</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/static/style.css">
    <style>
        .map-container {
            width: 100%;
            height: calc(100vh - 200px);
            min-height: 600px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        .dashboard-link {
            margin-bottom: 20px;
            display: inline-block;
            padding: 8px 16px;
            background: #f8f9fa;
            border-radius: 6px;
            text-decoration: none;
            color: #333;
        }
        .dashboard-link:hover {
            background: #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Traffic Light Control System - Network Map</h1>
            <div class="server-status">
                <span class="status-label">Server Status:</span>
                <span class="status-value online">Online</span>
            </div>
        </header>
        
        <a href="/" class="dashboard-link">← Back to Dashboard</a>
        
        <div class="map-container">
            <iframe src="/static/intersection_map.html" width="100%" height="100%" frameborder="0"></iframe>
        </div>
        
        <footer>
            <p>Traffic Light Control System - Central Server &copy; 2025</p>
        </footer>
    </div>
</body>
</html>
        ''')

    return map_path

def haversine_distance(point1, point2):
    """Calculate the great-circle distance between two points in kilometers"""
    lat1, lon1 = point1
    lat2, lon2 = point2

    # Convert latitude and longitude to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    return c * r

def calculate_intersection_sync_times():
    """Calculate sync times between connected intersections based on distance and expected travel time."""
    if not agent_data:
        log_event("No agent data available for calculating sync times")
        return {}

    sync_times = {}
    intersections_with_locations = {}

    # First, collect all intersections with valid location data
    for agent_id, data in agent_data.items():
        if 'topology' in data and 'location' in data['topology']:
            location = data['topology']['location']
            if 'latitude' in location and 'longitude' in location:
                try:
                    lat = float(location['latitude'])
                    lng = float(location['longitude'])
                    intersections_with_locations[agent_id] = (lat, lng)
                except (ValueError, TypeError):
                    log_event(f"Invalid location format for agent {agent_id}")

    # For each pair of intersections, calculate sync time
    for id1, loc1 in intersections_with_locations.items():
        sync_times[id1] = {}
        for id2, loc2 in intersections_with_locations.items():
            if id1 != id2:
                # Calculate distance between intersections
                distance_km = haversine_distance(loc1, loc2)

                # Calculate travel time based on average speed (assuming 40 km/h)
                avg_speed_kmh = 40.0

                # Get actual speed if available in agent data
                if id1 in agent_data and 'states' in agent_data[id1]:
                    states = agent_data[id1]['states']
                    if states and 'traffic_data' in states[-1] and 'avg_speed' in states[-1]['traffic_data']:
                        speeds = states[-1]['traffic_data']['avg_speed']
                        # Convert m/s to km/h and average all directions
                        if speeds:
                            avg_speed_kmh = sum(speeds.values()) * 3.6 / len(speeds)

                # Calculate travel time in seconds
                travel_time_sec = (distance_km / avg_speed_kmh) * 3600

                # Calculate optimal offset based on travel time (green wave)
                # This is a simple calculation - in real systems it would be more complex
                cycle_time = 0
                if id1 in agent_data and 'config' in agent_data[id1]:
                    green_duration = agent_data[id1]['config'].get('green_duration', 0)
                    yellow_duration = agent_data[id1]['config'].get('yellow_duration', 0)
                    cycle_time = (green_duration + yellow_duration) * 2  # Simplified cycle time calculation

                # Default cycle time if not available
                if cycle_time == 0:
                    cycle_time = 38  # Typical cycle time as fallback

                # Calculate optimal offset (modulo the cycle time)
                optimal_offset = travel_time_sec % cycle_time

                # Store the sync data
                sync_times[id1][id2] = {
                    "distance_km": round(distance_km, 2),
                    "travel_time_sec": round(travel_time_sec, 2),
                    "optimal_offset_sec": round(optimal_offset, 2),
                    "cycle_time_sec": cycle_time
                }

    # Save the sync times to a file for reference
    with open('server_data/sync_times.json', 'w') as f:
        json.dump(sync_times, f, indent=2)

    log_event(f"Calculated sync times between {len(intersections_with_locations)} intersections")
    for id1, targets in sync_times.items():
        for id2, sync_data in targets.items():
            log_event(f"  {id1} → {id2}: Distance={sync_data['distance_km']}km, "

                      f"Travel Time={sync_data['travel_time_sec']}s, " +
                      f"Optimal Offset={sync_data['optimal_offset_sec']}s")
    return sync_times

def save_data_periodically():
    """Save collected data to disk periodically"""
    while True:
        # Save current data
        with open('server_data/agent_data.json', 'w') as f:
            json.dump(agent_data, f)

        # Check for disconnected agents
        current_time = time.time()
        for agent_id, last_time in list(last_update.items()):
            if current_time - last_time > TIMEOUT_THRESHOLD:
                log_event(f"WARNING: Agent {agent_id} appears to be offline")

        # Generate visualizations if data exists
        if agent_data:
            try:
                generate_comparison_charts()
                generate_intersection_map()
                log_event("Generated updated charts and map")
            except Exception as e:
                log_event(f"ERROR generating visualizations: {e}")

        time.sleep(30)  # Update every 30 seconds

def generate_comparison_charts():
    """Generate comparison charts from collected agent data"""
    if not agent_data:
        return

    # Prepare data for plotting
    agents = list(agent_data.keys())
    rewards = {agent: data.get('rewards', []) for agent, data in agent_data.items() if 'rewards' in data}
    queue_lengths = {agent: data.get('queue_lengths', []) for agent, data in agent_data.items() if 'queue_lengths' in data}

    # Only plot if we have data
    if rewards and any(len(r) > 0 for r in rewards.values()):
        # Plot rewards
        plt.figure(figsize=(12, 6))
        for agent, reward_data in rewards.items():
            if reward_data:
                plt.plot(reward_data, label=f"Agent {agent}")
        plt.title('Cumulative Rewards by Agent')
        plt.xlabel('Episode')
        plt.ylabel('Reward')
        plt.legend()
        plt.savefig(f'server_data/figures/rewards_comparison.png')
        plt.savefig(f'static/rewards_comparison.png')
        plt.close()

    # Plot queue lengths if available
    if queue_lengths and any(len(q) > 0 for q in queue_lengths.values()):
        plt.figure(figsize=(12, 6))
        for agent, queue_data in queue_lengths.items():
            if queue_data:
                plt.plot(queue_data, label=f"Agent {agent}")
        plt.title('Average Queue Length by Agent')
        plt.xlabel('Episode')
        plt.ylabel('Queue Length')
        plt.legend()
        plt.savefig(f'server_data/figures/queue_comparison.png')
        plt.savefig(f'static/queue_comparison.png')
        plt.close()

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get overall system status in Flutter dashboard format"""
    online_count = len([a for a_id in agent_data.keys() if a_id in last_update and (time.time() - last_update[a_id] <= TIMEOUT_THRESHOLD)])
    total_count = len(agent_data)
    
    # Generate some sample alerts
    alerts = []
    if online_count < total_count:
        alerts.append({
            'id': 'offline_agents',
            'title': 'Offline Agents Detected',
            'message': f'{total_count - online_count} agents are currently offline',
            'severity': 'warning',
            'timestamp': datetime.now().isoformat(),
            'intersectionId': None,
            'isRead': False
        })
    
    # Add system alerts from global list
    alerts.extend(system_alerts[-10:])  # Last 10 alerts
    
    status = {
        'isOnline': True,
        'activeIntersections': online_count,
        'totalIntersections': total_count,
        'systemHealth': 0.95 if online_count == total_count else (online_count / total_count if total_count > 0 else 0.0),
        'version': '1.0.0',
        'lastUpdate': datetime.now().isoformat(),
        'serverInfo': {
            'uptime': time.time() - start_time if 'start_time' in globals() else 0,
            'memory_usage': '45%',
            'cpu_usage': '12%',
            'connected_clients': len(agent_data),
            'server_port': 5000
        },
        'alerts': alerts
    }
    return jsonify(status)

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get all agent data in Flutter dashboard format"""
    intersections = []
    
    for agent_id, data in agent_data.items():
        # Convert agent data to IntersectionData format
        intersection = {
            'id': agent_id,
            'name': data.get('topology', {}).get('location', {}).get('intersection_name', f'Intersection {agent_id}'),
            'latitude': data.get('topology', {}).get('location', {}).get('latitude', 10.777807),
            'longitude': data.get('topology', {}).get('location', {}).get('longitude', 106.681676),
            'status': 'online' if agent_id in last_update and (time.time() - last_update[agent_id] <= TIMEOUT_THRESHOLD) else 'offline',
            'lastUpdate': datetime.fromtimestamp(last_update.get(agent_id, time.time())).isoformat() if agent_id in last_update else datetime.now().isoformat(),
            'configuration': data.get('config', {}),
            'metrics': {
                'averageWaitTime': np.mean(data.get('waiting_times', [30.0])[-10:]) if data.get('waiting_times') else 30.0,
                'averageQueueLength': np.mean(data.get('queue_lengths', [5.0])[-10:]) if data.get('queue_lengths') else 5.0,
                'vehicleCount': len(data.get('queue_lengths', [])),
                'throughput': np.random.uniform(50, 150),
                'efficiency': np.random.uniform(0.7, 0.95),
                'waitTimes': data.get('waiting_times', [])[-24:],  # Last 24 data points
                'queueLengths': data.get('queue_lengths', [])[-24:],  # Last 24 data points
                'timestamp': datetime.now().isoformat()
            },
            'phases': [
                {
                    'id': 'phase_1',
                    'name': 'North-South',
                    'directions': ['north', 'south'],
                    'duration': 30,
                    'isActive': True,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                },
                {
                    'id': 'phase_2',
                    'name': 'East-West',
                    'directions': ['east', 'west'],
                    'duration': 25,
                    'isActive': False,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                }
            ],
            'connectedIntersections': data.get('connected_to', []) if isinstance(data.get('connected_to'), list) else []
        }
        intersections.append(intersection)
    
    return jsonify({'intersections': intersections})

@app.route('/api/agent/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get all data for a specific agent"""
    if agent_id in agent_data:
        return jsonify(agent_data[agent_id])
    else:
        return jsonify({'error': 'Agent not found'}), 404

@app.route('/api/agent/<agent_id>/coordination', methods=['GET'])
def get_agent_coordination(agent_id):
    """Get coordination data for a specific agent"""
    try:
        # Get coordination data from memory
        coordination_data = retrieve_coordination_data(agent_id)

        # Get vehicle transfers from file
        vehicle_transfers = get_vehicle_transfers(agent_id)

        # Combine the data
        if coordination_data:
            coordination_data['vehicle_transfers'] = vehicle_transfers

        return jsonify(coordination_data or {})
    except Exception as e:
        log_event(f"ERROR getting coordination data for agent {agent_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/coordination/<agent_id>', methods=['GET'])
def get_coordination(agent_id):
    """Get coordination data for a specific agent (alternative endpoint)"""
    if agent_id not in agent_data:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(agent_data[agent_id].get('coordination', {}))

@app.route('/api/agent/<agent_id>/config', methods=['POST'])
def update_agent_config(agent_id):
    """Update agent configuration"""
    config = request.json
    # firebase.update_agent_config(agent_id, config)
    return jsonify({'status': 'success'})

@app.route('/api/agent/<agent_id>/metrics', methods=['POST'])
def update_agent_metrics(agent_id):
    """Update agent metrics"""
    metrics = request.json
    # firebase.update_agent_metrics(agent_id, metrics)
    return jsonify({'status': 'success'})

@app.route('/api/agent/<agent_id>/status', methods=['POST'])
def update_agent_status(agent_id):
    """Update agent status"""
    status = request.json.get('status')
    # firebase.update_agent_status(agent_id, status)
    return jsonify({'status': 'success'})

@app.route('/api/agent/<agent_id>/location', methods=['POST'])
def update_agent_location(agent_id):
    """Update agent location"""
    data = request.json
    # firebase.update_agent_location(
    #     agent_id,
    #     data.get('latitude'),
    #     data.get('longitude')
    # )
    return jsonify({'status': 'success'})

@app.route('/api/agent/<agent_id>/performance', methods=['POST'])
def update_agent_performance(agent_id):
    """Update agent performance metrics"""
    performance_data = request.json
    # firebase.update_agent_performance(agent_id, performance_data)
    return jsonify({'status': 'success'})

@app.route('/api/agent/<agent_id>/log', methods=['POST'])
def add_agent_log(agent_id):
    """Add agent log entry"""
    data = request.json
    # firebase.add_agent_log(
    #     agent_id,
    #     data.get('message'),
    #     data.get('level', 'INFO')
    # )
    return jsonify({'status': 'success'})

def update_system_status():
    """Periodically update system status"""
    while True:
        # agents = firebase.get_all_agents()
        if agent_data:
            total_agents = len(agent_data)
            online_agents = sum(1 for agent in agent_data.values()
                                if agent.get('online', False))
            # firebase.update_system_status(total_agents, online_agents)
            print(f"📊 System Status: {online_agents}/{total_agents} agents online")
        time.sleep(5)

@app.route('/api/latest_charts', methods=['GET'])
def get_latest_charts():
    """Get information about the latest generated charts"""
    charts = {
        'rewards_chart': '/static/rewards_comparison.png?t=' + str(int(time.time())),
        'queue_chart': '/static/queue_comparison.png?t=' + str(int(time.time())),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return jsonify(charts)

@app.route('/api/reset', methods=['GET'])
def reset_server_data():
    """Clear all stored data and reset the server state"""
    global agent_data, last_update
    agent_data = {}
    last_update = {}

    print("Server data has been reset")
    return jsonify({'status': 'success', 'message': 'Server data has been reset'}), 200

@app.route('/map')
def show_map():
    """Serve the intersection map page"""
    return render_template('map.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Endpoint to retrieve server logs"""
    return jsonify({'logs': list(server_logs)})

@app.route('/api/update', methods=['POST'])
def receive_updates():
    """Endpoint for agents to send their data"""
    try:
        data = request.json
        log_event(f"Received update from agent: {data['agent_id']}")
        agent_id = data.get('agent_id')

        if not agent_id:
            log_event("ERROR: Received update without agent_id")
            return jsonify({'status': 'error', 'message': 'Missing agent_id'}), 400

        # Store the update time
        last_update[agent_id] = time.time()

        # Initialize agent data if it doesn't exist
        if agent_id not in agent_data:
            agent_data[agent_id] = {
                'rewards': [],
                'queue_lengths': [],
                'waiting_times': [],
                'status': 'unknown',
                'online': True,  # New agents are online by default
                'last_episode': -1
            }
            log_event(f"New agent registered: {agent_id}")

        # Handle vehicle transfers
        if 'vehicle_transfer' in data:
            transfer_data = data['vehicle_transfer']
            log_event(f"Received vehicle transfer: {transfer_data['vehicle_id']} from {transfer_data['from_agent']} to {transfer_data['to_agent']}")

            # Store the transfer data in the destination agent's coordination data
            to_agent = transfer_data['to_agent']
            if to_agent not in agent_data:
                agent_data[to_agent] = {'coordination': {'incoming_vehicles': []}}
            elif 'coordination' not in agent_data[to_agent]:
                agent_data[to_agent]['coordination'] = {'incoming_vehicles': []}
            elif 'incoming_vehicles' not in agent_data[to_agent]['coordination']:
                agent_data[to_agent]['coordination']['incoming_vehicles'] = []

            # Add the vehicle to the destination agent's incoming vehicles
            agent_data[to_agent]['coordination']['incoming_vehicles'].append(transfer_data)
            log_event(f"Added vehicle {transfer_data['vehicle_id']} to {to_agent}'s incoming vehicles")
            print(f"Added vehicle {transfer_data['vehicle_id']} to {to_agent}'s incoming vehicles")
        # Handle states data
        if 'states' in data:
            store_agent_states(agent_id, data['states'])

        # Handle one-time topology data
        if 'topology' in data and 'topology' not in agent_data[agent_id]:
            agent_data[agent_id]['topology'] = data['topology']
            log_event(f"Received topology data for {agent_id}: {data['topology']}")
            try:
                generate_intersection_map()
            except Exception as e:
                log_event(f"Error generating map: {e}")
            
            # Immediately save the updated agent data with topology
            try:
                with open('server_data/agent_data.json', 'w') as f:
                    json.dump(agent_data, f, indent=2)
                log_event(f"Saved topology data for {agent_id} to agent_data.json")
            except Exception as e:
                log_event(f"Error saving agent data: {e}")

        # ACCUMULATE metrics data rather than replacing
        if 'rewards' in data and data['rewards']:
            agent_data[agent_id].setdefault('rewards', []).extend(data['rewards'])

        if 'queue_lengths' in data and data['queue_lengths']:
            agent_data[agent_id].setdefault('queue_lengths', []).extend(data['queue_lengths'])

        if 'waiting_times' in data and data['waiting_times']:
            agent_data[agent_id].setdefault('waiting_times', []).extend(data['waiting_times'])

        # Update scalar values
        if 'status' in data:
            agent_data[agent_id]['status'] = data['status']
            # Update online status based on the new status
            agent_data[agent_id]['online'] = data['status'] != 'terminated'
            # Update status in Firebase
            # firebase.update_agent_status(agent_id, data['status'])

        # Update system status
        # firebase.update_system_status(len(agent_data), sum(1 for agent in agent_data.values() if agent.get('online', False)))

        return jsonify({'status': 'success'})
    except Exception as e:
        log_event(f"ERROR in receive_updates: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

coordination_storage = {}  # Simple in-memory storage for coordination data

def store_agent_states(agent_id, states):
    """Store state data received from an agent"""
    if agent_id not in agent_data:
        agent_data[agent_id] = {}

    agent_data[agent_id]['states'] = states
    log_event(f"Stored {len(states)} states from agent {agent_id}")

    # Trigger coordination processing when new states arrive
    process_all_intersections()

def get_intersection_topology():
    """Get topology data for all intersections"""
    topology = {}
    for agent_id, data in agent_data.items():
        if 'topology' in data:
            topology[agent_id] = data['topology']
    return topology

def store_coordination_data(agent_id, data):
    """Store coordination data for sync agent"""
    if agent_id not in coordination_storage:
        coordination_storage[agent_id] = []

    # Keep only last 100 entries
    if len(coordination_storage[agent_id]) >= 100:
        coordination_storage[agent_id].pop(0)

    coordination_storage[agent_id].append(data)

def retrieve_coordination_data(agent_id):
    """Retrieve coordination data for sync agent"""
    if agent_id not in coordination_storage:
        return None
    return coordination_storage[agent_id][-1] if coordination_storage[agent_id] else None

def process_all_intersections():
    """Process states from all intersections to generate coordination"""
    all_states = {}
    for agent_id, data in agent_data.items():
        if 'states' in data and data['states']:
            all_states[agent_id] = data['states']

    # Store states for sync agent to use
    for agent_id, states in all_states.items():
        if not states:
            continue

        latest_state = states[-1]  # Get most recent state
        traffic_data = latest_state.get('traffic_data', {})

        # Get vehicle statistics
        vehicle_stats = agent_data[agent_id].get('vehicle_stats', {})

        # Store basic traffic data
        store_coordination_data(agent_id, {
            'timestamp': time.time(),
            'queue_length': traffic_data.get('queue_length', 0),
            'current_phase': traffic_data.get('current_phase', 0),
            'incoming_vehicles': traffic_data.get('incoming_vehicles', {}),
            'avg_speed': traffic_data.get('avg_speed', {}),
            'vehicle_transfers': agent_data[agent_id].get('coordination', {}).get('incoming_vehicles', []),
            'vehicle_stats': vehicle_stats
        })

        # Clear processed vehicle transfers
        if 'coordination' in agent_data[agent_id] and 'incoming_vehicles' in agent_data[agent_id]['coordination']:
            agent_data[agent_id]['coordination']['incoming_vehicles'] = []

def get_all_agent_states():
    """Retrieve states from all agents"""
    all_states = {}
    for agent_id, data in agent_data.items():
        if 'states' in data:
            all_states[agent_id] = data['states']
    return all_states

def calculate_travel_times(topology):
    """Calculate travel times between intersections based on topology"""
    travel_times = {}
    for agent_id, data in topology.items():
        if 'connections' in data:
            for connection in data['connections']:
                # Calculate travel time based on distance and speed limit
                distance = haversine_distance(
                    (data['location']['latitude'], data['location']['longitude']),
                    (connection['latitude'], connection['longitude'])
                )
                speed_limit = connection.get('speed_limit', 1)  # Default to 1 m/s to avoid division by zero
                travel_time = distance / speed_limit
                travel_times[(agent_id, connection['agent_id'])] = travel_time
    return travel_times

def get_drl_optimized_sync_times():
    """Get DRL-optimized synchronization times if available"""
    sync_file = 'server_data/sync_times.json'

    try:
        if os.path.exists(sync_file):
            with open(sync_file, 'r') as f:
                sync_times = json.load(f)

            # Check if this has DRL optimization flag
            has_drl = False
            for id1, targets in sync_times.items():
                for id2, data in targets.items():
                    if 'drl_optimized' in data and data['drl_optimized']:
                        has_drl = True
                        break
                if has_drl:
                    break

            if has_drl:
                log_event("Using DRL-optimized synchronization times")
                return sync_times
    except Exception as e:
        log_event(f"Error loading DRL sync times: {e}")

    # If not available or error, calculate them
    return calculate_intersection_sync_times()

@app.route('/api/sync_times', methods=['GET'])
def get_sync_times():
    """Get synchronization timing data"""
    try:
        sync_file = os.path.join(os.path.dirname(__file__), 'server_data', 'sync_times.json')
        if os.path.exists(sync_file):
            with open(sync_file, 'r') as f:
                sync_times = json.load(f)
            return jsonify(sync_times)
        else:
            return jsonify({}), 404
    except Exception as e:
        log_event(f"Error getting sync times: {e}")
        return jsonify({'error': str(e)}), 500

def store_vehicle_transfer(transfer_data):
    """Store vehicle transfer data in a JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(VEHICLE_TRANSFER_FILE), exist_ok=True)
        log_event(f"Ensuring directory exists: {os.path.dirname(VEHICLE_TRANSFER_FILE)}")

        # Load existing data
        existing_data = []
        if os.path.exists(VEHICLE_TRANSFER_FILE):
            try:
                with open(VEHICLE_TRANSFER_FILE, 'r') as f:
                    existing_data = json.load(f)
                log_event(f"Successfully loaded existing vehicle transfer data from {VEHICLE_TRANSFER_FILE}")
            except json.JSONDecodeError:
                log_event(f"Error reading vehicle transfer file, creating new file at {VEHICLE_TRANSFER_FILE}")
                existing_data = []
        else:
            log_event(f"Vehicle transfer file not found, creating new file at {VEHICLE_TRANSFER_FILE}")

        # Add timestamp to transfer data
        transfer_data['stored_at'] = datetime.now().isoformat()

        # Append new transfer data
        existing_data.append(transfer_data)

        # Save updated data
        try:
            with open(VEHICLE_TRANSFER_FILE, 'w') as f:
                json.dump(existing_data, f, indent=2)
            log_event(f"Successfully stored vehicle transfer data in {VEHICLE_TRANSFER_FILE}")
            return True
        except Exception as e:
            log_event(f"Error writing to vehicle transfer file: {str(e)}")
            return False

    except Exception as e:
        log_event(f"ERROR storing vehicle transfer data: {str(e)}")
        return False

def get_vehicle_transfers(to_agent=None):
    """Get vehicle transfer data for a specific agent"""
    try:
        if not os.path.exists(VEHICLE_TRANSFER_FILE):
            log_event(f"Vehicle transfer file not found at {VEHICLE_TRANSFER_FILE}, returning empty list")
            return []

        with open(VEHICLE_TRANSFER_FILE, 'r') as f:
            transfers = json.load(f)
            log_event(f"Successfully loaded {len(transfers)} vehicle transfers from {VEHICLE_TRANSFER_FILE}")

        if to_agent:
            transfers = [t for t in transfers if t.get('to_agent') == to_agent]
            log_event(f"Filtered to {len(transfers)} transfers for agent {to_agent}")

        return transfers
    except Exception as e:
        log_event(f"ERROR getting vehicle transfers: {str(e)}")
        return []

@app.route('/api/vehicle_transfers', methods=['GET'])
def get_vehicle_transfers():
    """Get all vehicle transfers or filter by agent"""
    try:
        agent_id = request.args.get('agent_id')

        if not os.path.exists(VEHICLE_TRANSFER_FILE):
            return jsonify([])

        with open(VEHICLE_TRANSFER_FILE, 'r') as f:
            all_transfers = json.load(f)

        if agent_id:
            # Filter transfers for the specific agent
            transfers = [t for t in all_transfers if t.get('to_agent') == agent_id]
        else:
            transfers = all_transfers

        return jsonify(transfers)
    except Exception as e:
        log_event(f"ERROR getting vehicle transfers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vehicle_transfer', methods=['POST'])
def receive_vehicle_transfer():
    """Endpoint for receiving vehicle transfer data between intersections"""
    try:
        transfer_data = request.json
        if not transfer_data or not isinstance(transfer_data, dict):
            return jsonify({'status': 'error', 'message': 'Invalid transfer data format'}), 400

        required_fields = ['vehicle_id', 'from_agent', 'to_agent', 'type', 'speed', 'waiting_time']
        missing_fields = [field for field in required_fields if field not in transfer_data]
        if missing_fields:
            return jsonify({'status': 'error', 'message': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        log_event(f"Received vehicle transfer: {transfer_data['vehicle_id']} from {transfer_data['from_agent']} to {transfer_data['to_agent']}")
        log_event(f"Vehicle details: type={transfer_data['type']}, speed={transfer_data['speed']:.2f}, waiting_time={transfer_data['waiting_time']:.2f}")

        # Store the transfer data in the file
        if store_vehicle_transfer(transfer_data):
            # Also store in memory for immediate access
            to_agent = transfer_data['to_agent']
            if to_agent not in agent_data:
                agent_data[to_agent] = {'coordination': {'incoming_vehicles': []}}
            elif 'coordination' not in agent_data[to_agent]:
                agent_data[to_agent]['coordination'] = {'incoming_vehicles': []}
            elif 'incoming_vehicles' not in agent_data[to_agent]['coordination']:
                agent_data[to_agent]['coordination']['incoming_vehicles'] = []

            # Add the vehicle to the destination agent's incoming vehicles
            agent_data[to_agent]['coordination']['incoming_vehicles'].append(transfer_data)
            log_event(f"Added vehicle {transfer_data['vehicle_id']} to {to_agent}'s incoming vehicles")

            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to store vehicle transfer data'}), 500

    except Exception as e:
        log_event(f"ERROR in receive_vehicle_transfer: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def delete_vehicle_transfer(vehicle_id):
    """Delete vehicle transfer data for a specific vehicle"""
    try:
        if not os.path.exists(VEHICLE_TRANSFER_FILE):
            log_event(f"Vehicle transfer file not found at {VEHICLE_TRANSFER_FILE}")
            return False

        with open(VEHICLE_TRANSFER_FILE, 'r') as f:
            transfers = json.load(f)

        # Find and remove the transfer data for the specified vehicle
        original_length = len(transfers)
        transfers = [t for t in transfers if t.get('vehicle_id') != vehicle_id]

        if len(transfers) < original_length:
            # Save the updated data
            with open(VEHICLE_TRANSFER_FILE, 'w') as f:
                json.dump(transfers, f, indent=2)
            log_event(f"Successfully deleted vehicle transfer data for vehicle {vehicle_id}")
            return True
        else:
            log_event(f"No transfer data found for vehicle {vehicle_id}")
            return False

    except Exception as e:
        log_event(f"ERROR deleting vehicle transfer data: {str(e)}")
        return False

@app.route('/api/vehicle_transfer/<vehicle_id>', methods=['DELETE'])
def delete_transfer(vehicle_id):
    """Endpoint for deleting vehicle transfer data after successful spawning"""
    try:
        if delete_vehicle_transfer(vehicle_id):
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Vehicle transfer data not found'}), 404
    except Exception as e:
        log_event(f"ERROR in delete_transfer: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vehicle_transfers/clear/<agent_id>', methods=['DELETE'])
def clear_agent_transfers(agent_id):
    """Endpoint for clearing all vehicle transfer data for a specific agent"""
    try:
        if not os.path.exists(VEHICLE_TRANSFER_FILE):
            log_event(f"Vehicle transfer file not found at {VEHICLE_TRANSFER_FILE}")
            return jsonify({'status': 'success', 'cleared': 0})

        with open(VEHICLE_TRANSFER_FILE, 'r') as f:
            transfers = json.load(f)

        # Count transfers for this agent before removal
        original_length = len(transfers)
        agent_transfers = [t for t in transfers if t.get('to_agent') == agent_id]
        cleared_count = len(agent_transfers)
        
        # Remove all transfers for the specified agent
        transfers = [t for t in transfers if t.get('to_agent') != agent_id]

        # Save the updated data
        with open(VEHICLE_TRANSFER_FILE, 'w') as f:
            json.dump(transfers, f, indent=2)
            
        # Also clear from memory
        if agent_id in agent_data and 'coordination' in agent_data[agent_id]:
            if 'incoming_vehicles' in agent_data[agent_id]['coordination']:
                agent_data[agent_id]['coordination']['incoming_vehicles'] = []

        log_event(f"Successfully cleared {cleared_count} vehicle transfer records for agent {agent_id}")
        return jsonify({'status': 'success', 'cleared': cleared_count})

    except Exception as e:
        log_event(f"ERROR clearing vehicle transfers for agent {agent_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === ANALYTICS API ENDPOINTS ===
@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data for dashboard"""
    try:
        start_date = request.args.get('start')
        end_date = request.args.get('end') 
        intersection_id = request.args.get('intersection')
        
        # Parse dates
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_date = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_date = datetime.now()
        
        # Generate analytics data
        analytics = generate_analytics_data(start_date, end_date, intersection_id)
        
        return jsonify(analytics)
    except Exception as e:
        log_event(f"ERROR in get_analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

def generate_analytics_data(start_date, end_date, intersection_id=None):
    """Generate analytics data based on existing agent data"""
    metrics = []
    wait_time_series = []
    queue_length_series = []
    throughput_series = []
    
    # Get data for specific intersection or all
    if intersection_id and intersection_id in agent_data:
        agents = {intersection_id: agent_data[intersection_id]}
    else:
        agents = agent_data
    
    current_time = datetime.now()
    
    # Generate sample metrics for the dashboard
    for agent_id, data in agents.items():
        # Performance metrics
        metrics.extend([
            {
                'name': f'Average Wait Time - {agent_id}',
                'value': data.get('metrics', {}).get('average_wait_time', np.random.uniform(15, 45)),
                'unit': 'seconds',
                'previousValue': np.random.uniform(20, 50),
                'trend': 'down' if np.random.random() > 0.5 else 'up',
                'timestamp': current_time.isoformat()
            },
            {
                'name': f'Queue Length - {agent_id}',
                'value': data.get('metrics', {}).get('average_queue_length', np.random.uniform(2, 8)),
                'unit': 'vehicles',
                'previousValue': np.random.uniform(3, 10),
                'trend': 'down' if np.random.random() > 0.5 else 'up',
                'timestamp': current_time.isoformat()
            },
            {
                'name': f'Efficiency - {agent_id}',
                'value': data.get('metrics', {}).get('efficiency', np.random.uniform(0.7, 0.95)),
                'unit': '%',
                'previousValue': np.random.uniform(0.6, 0.9),
                'trend': 'up' if np.random.random() > 0.5 else 'down',
                'timestamp': current_time.isoformat()
            }
        ])
        
        # Generate time series data
        for i in range(24):  # 24 hours of data
            time_point = current_time - timedelta(hours=23-i)
            
            wait_time_series.append({
                'timestamp': time_point.isoformat(),
                'value': np.random.uniform(10, 60),
                'label': f'{agent_id}_wait_time'
            })
            
            queue_length_series.append({
                'timestamp': time_point.isoformat(),
                'value': np.random.uniform(1, 10),
                'label': f'{agent_id}_queue_length'
            })
            
            throughput_series.append({
                'timestamp': time_point.isoformat(),
                'value': np.random.uniform(50, 200),
                'label': f'{agent_id}_throughput'
            })
    
    # Aggregated metrics
    aggregated_metrics = {
        'totalIntersections': len(agents),
        'averageWaitTime': np.mean([m['value'] for m in metrics if 'Wait Time' in m['name']]) if metrics else 0,
        'averageQueueLength': np.mean([m['value'] for m in metrics if 'Queue Length' in m['name']]) if metrics else 0,
        'systemEfficiency': np.mean([m['value'] for m in metrics if 'Efficiency' in m['name']]) if metrics else 0.8,
        'totalVehicles': sum([data.get('metrics', {}).get('vehicle_count', np.random.randint(50, 200)) for data in agents.values()])
    }
    
    # Comparison data
    comparisons = [
        {
            'name': 'Average Wait Time',
            'beforeValue': 45.2,
            'afterValue': 32.8,
            'unit': 'seconds',
            'improvementPercentage': 27.4,
            'comparisonDate': current_time.isoformat()
        },
        {
            'name': 'Queue Length',
            'beforeValue': 8.5,
            'afterValue': 5.2,
            'unit': 'vehicles',
            'improvementPercentage': 38.8,
            'comparisonDate': current_time.isoformat()
        }
    ]
    
    return {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'intersectionId': intersection_id,
        'metrics': metrics,
        'waitTimeSeries': wait_time_series,
        'queueLengthSeries': queue_length_series,
        'throughputSeries': throughput_series,
        'aggregatedMetrics': aggregated_metrics,
        'comparisons': comparisons
    }

# === INTERSECTION CRUD ENDPOINTS ===
@app.route('/api/intersections', methods=['POST'])
def add_intersection():
    """Add a new intersection"""
    try:
        data = request.get_json()
        agent_id = data.get('id') or f"agent_{len(agent_data) + 1}"
        
        # Create new intersection data
        agent_data[agent_id] = {
            'id': agent_id,
            'name': data.get('name', f'Intersection {agent_id}'),
            'latitude': data.get('latitude', 10.777807),
            'longitude': data.get('longitude', 106.681676),
            'status': 'offline',
            'lastUpdate': datetime.now().isoformat(),
            'configuration': data.get('configuration', {}),
            'metrics': {
                'averageWaitTime': 0.0,
                'averageQueueLength': 0.0,
                'vehicleCount': 0,
                'throughput': 0.0,
                'efficiency': 0.0,
                'waitTimes': [],
                'queueLengths': [],
                'timestamp': datetime.now().isoformat()
            },
            'phases': data.get('phases', []),
            'connectedIntersections': data.get('connectedIntersections', [])
        }
        
        last_update[agent_id] = time.time()
        log_event(f"Added new intersection: {agent_id}")
        
        # Emit WebSocket update
        socketio.emit('intersection_update', {
            'type': 'intersection_added',
            'data': agent_data[agent_id]
        })
        
        return jsonify({'status': 'success', 'agent_id': agent_id})
    except Exception as e:
        log_event(f"ERROR adding intersection: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/agent/<agent_id>', methods=['DELETE'])
def remove_intersection(agent_id):
    """Remove an intersection"""
    try:
        if agent_id in agent_data:
            del agent_data[agent_id]
            if agent_id in last_update:
                del last_update[agent_id]
            if agent_id in agent_configs:
                del agent_configs[agent_id]
            if agent_id in agent_metrics:
                del agent_metrics[agent_id]
            if agent_id in training_sessions:
                del training_sessions[agent_id]
                
            log_event(f"Removed intersection: {agent_id}")
            
            # Emit WebSocket update
            socketio.emit('intersection_update', {
                'type': 'intersection_removed',
                'data': {'id': agent_id}
            })
            
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Intersection not found'}), 404
    except Exception as e:
        log_event(f"ERROR removing intersection: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === TRAINING API ENDPOINTS ===
@app.route('/api/training/start', methods=['POST'])
def start_training():
    """Start training for an intersection"""
    try:
        data = request.get_json()
        intersection_id = data.get('intersection_id')
        parameters = data.get('parameters', {})
        
        if not intersection_id or intersection_id not in agent_data:
            return jsonify({'status': 'error', 'message': 'Intersection not found'}), 404
        
        # Create training session
        training_sessions[intersection_id] = {
            'id': f"training_{intersection_id}_{int(time.time())}",
            'intersection_id': intersection_id,
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'parameters': parameters,
            'progress': 0.0,
            'current_episode': 0,
            'total_episodes': parameters.get('episodes', 1000),
            'metrics': {
                'reward': [],
                'loss': [],
                'episode_length': []
            }
        }
        
        # Update intersection status
        agent_data[intersection_id]['status'] = 'training'
        
        log_event(f"Started training for intersection {intersection_id}")
        
        # Emit WebSocket update
        socketio.emit('training_update', {
            'type': 'training_started',
            'data': training_sessions[intersection_id]
        })
        
        return jsonify({'status': 'success', 'session_id': training_sessions[intersection_id]['id']})
    except Exception as e:
        log_event(f"ERROR starting training: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/training/stop', methods=['POST'])
def stop_training():
    """Stop training for an intersection"""
    try:
        data = request.get_json()
        intersection_id = data.get('intersection_id')
        
        if intersection_id in training_sessions:
            training_sessions[intersection_id]['status'] = 'stopped'
            training_sessions[intersection_id]['end_time'] = datetime.now().isoformat()
            
            # Update intersection status
            if intersection_id in agent_data:
                agent_data[intersection_id]['status'] = 'online'
            
            log_event(f"Stopped training for intersection {intersection_id}")
            
            # Emit WebSocket update
            socketio.emit('training_update', {
                'type': 'training_stopped',
                'data': training_sessions[intersection_id]
            })
            
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'No active training session found'}), 404
    except Exception as e:
        log_event(f"ERROR stopping training: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/training/status/<intersection_id>', methods=['GET'])
def get_training_status(intersection_id):
    """Get training status for an intersection"""
    try:
        if intersection_id in training_sessions:
            session = training_sessions[intersection_id].copy()
            
            # Simulate training progress
            if session['status'] == 'running':
                elapsed_time = (datetime.now() - datetime.fromisoformat(session['start_time'])).total_seconds()
                estimated_duration = session['parameters'].get('estimated_duration', 3600)  # 1 hour default
                session['progress'] = min(elapsed_time / estimated_duration, 1.0) * 100
                session['current_episode'] = int(session['progress'] / 100 * session['total_episodes'])
                
                # Add some sample metrics
                session['metrics']['reward'].append(np.random.uniform(-50, 50))
                session['metrics']['loss'].append(np.random.uniform(0.1, 2.0))
                session['metrics']['episode_length'].append(np.random.randint(50, 200))
            
            return jsonify(session)
        else:
            return jsonify({'status': 'no_session', 'message': 'No training session found'}), 404
    except Exception as e:
        log_event(f"ERROR getting training status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === WEBSOCKET ENDPOINTS ===
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    log_event("Client connected to WebSocket")
    emit('connection_response', {'status': 'connected', 'message': 'Welcome to Traffic Control WebSocket'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    log_event("Client disconnected from WebSocket")

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle subscription to data updates"""
    log_event(f"Client subscribed to: {data}")
    emit('subscription_response', {'status': 'subscribed', 'data': data})

# Function to broadcast real-time updates
def broadcast_system_update():
    """Broadcast system status update to all connected clients"""
    try:
        system_data = {
            'type': 'system_status',
            'data': {
                'isOnline': True,
                'activeIntersections': len([a for a in agent_data.values() if a.get('status') == 'online']),
                'totalIntersections': len(agent_data),
                'systemHealth': 0.95,
                'version': '1.0.0',
                'lastUpdate': datetime.now().isoformat(),
                'serverInfo': {
                    'uptime': time.time() - start_time if 'start_time' in globals() else 0,
                    'memory_usage': '45%',
                    'cpu_usage': '12%'
                },
                'alerts': system_alerts
            }
        }
        socketio.emit('system_update', system_data)
    except Exception as e:
        log_event(f"ERROR broadcasting system update: {str(e)}")

# Start time tracking
start_time = time.time()

if __name__ == '__main__':
    # Create template files if they don't exist
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write('''<!DOCTYPE html>
<html>
<head>
    <title>Traffic Light Control System - Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="/static/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <nav class="main-nav">
                <a href="/" class="nav-link active">Dashboard</a>
                <a href="/map" class="nav-link">Network Map</a>
            </nav>
            <h1>Traffic Light Control System - Central Server</h1>
            <div class="server-status">
                <span class="status-label">Server Status:</span>
                <span class="status-value online">Online</span>
                <span class="last-update">Last update: <span id="last-update-time">-</span></span>
            </div>
        </header>
        
        <div class="dashboard">
            <div class="sidebar">
                <div class="agent-summary">
                    <h2>Agent Summary</h2>
                    <div class="summary-stats">
                        <div class="stat-box">
                            <span class="stat-value" id="total-agents">0</span>
                            <span class="stat-label">Total Agents</span>
                        </div>
                        <div class="stat-box">
                            <span class="stat-value" id="online-agents">0</span>
                            <span class="stat-label">Online Agents</span>
                        </div>
                    </div>
                </div>
                
                <div class="agent-list">
                    <h2>Agent List</h2>
                    <div id="agent-list-container">
                        <p>No agents connected</p>
                    </div>
                </div>
            </div>
            
            <div class="main-content">
                <div class="chart-container">
                    <h2>Performance Comparison</h2>
                    <div class="chart-tabs">
                        <button class="tab-button active" onclick="showChart('rewards')">Rewards</button>
                        <button class="tab-button" onclick="showChart('queue')">Queue Length</button>
                    </div>
                    <div class="chart-display">
                        <div id="rewards-chart" class="chart active">
                            <img src="/static/rewards_comparison.png" alt="Rewards Chart" id="rewards-img">
                        </div>
                        <div id="queue-chart" class="chart">
                            <img src="/static/queue_comparison.png" alt="Queue Length Chart" id="queue-img">
                        </div>
                    </div>
                    <div class="chart-info">
                        <span>Last updated: <span id="chart-update-time">-</span></span>
                    </div>
                </div>
                    <div class="log-container">
                <h2>Server Log</h2>
                    <div class="log-controls">
                        <button id="refresh-logs" class="log-button">Refresh</button>
                        <button id="clear-logs" class="log-button">Clear Display</button>
                        <div class="auto-refresh">
                            <input type="checkbox" id="auto-refresh" checked>
                            <label for="auto-refresh">Auto-refresh</label>
                        </div>
                    </div>
                    <div class="log-box" id="log-box">
                        <div class="log-entry">Waiting for server logs...</div>
                    </div>
                </div>
                
                <div class="agent-details">
                    <h2>Agent Details</h2>
                    <select id="agent-selector">
                        <option value="">Select an agent</option>
                    </select>
                    <div id="agent-detail-container">
                        <p>Select an agent to view details</p>
                    </div>
                </div>
            </div>
        </div>
        
        <footer>
            <p>Traffic Light Control System - Central Server &copy; 2025</p>
        </footer>
    </div>
    
    <script src="/static/dashboard.js"></script>
</body>
</html>''')

    # Create CSS file if it doesn't exist
    if not os.path.exists('static/style.css'):
        with open('static/style.css', 'w') as f:
            f.write('''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f4f6f9;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #fff;
    padding: 15px 25px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

header h1 {
    font-size: 1.8rem;
    color: #2c3e50;
}

.server-status {
    display: flex;
    align-items: center;
    gap: 10px;
}

.status-label {
    font-weight: 600;
}

.status-value {
    padding: 5px 10px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
}

.online {
    background: #d4edda;
    color: #155724;
}

.offline {
    background: #f8d7da;
    color: #721c24;
}

.dashboard {
    display: flex;
    gap: 20px;
}

.sidebar {
    width: 300px;
    flex-shrink: 0;
}

.agent-summary, .agent-list {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

.summary-stats {
    display: flex;
    justify-content: space-between;
    margin-top: 15px;
}

.stat-box {
    width: 48%;
    padding: 15px;
    text-align: center;
    background: #f8f9fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
}

.stat-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 5px;
}

.stat-label {
    font-size: 0.9rem;
    color: #6c757d;
}

.agent-list h2, .agent-summary h2 {
    margin-bottom: 15px;
    font-size: 1.3rem;
    color: #2c3e50;
}

.agent-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    border-bottom: 1px solid #eee;
}

.agent-item:last-child {
    border-bottom: none;
}

.agent-name {
    font-weight: 600;
}

.agent-status {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
}

.agent-status.online {
    background: #28a745;
}

.agent-status.offline {
    background: #dc3545;
}

.main-content {
    flex-grow: 1;
}

.chart-container, .agent-details {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

.chart-container h2, .agent-details h2 {
    margin-bottom: 15px;
    font-size: 1.3rem;
    color: #2c3e50;
}

.chart-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
}

.tab-button {
    padding: 8px 15px;
    border: none;
    background: #f8f9fa;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
}

.tab-button.active {
    background: #007bff;
    color: white;
}

.chart-display {
    position: relative;
    height: 400px;
    border: 1px solid #eee;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 10px;
}

.chart {
    display: none;
    width: 100%;
    height: 100%;
}

.chart.active {
    display: block;
}

.chart img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.chart-info {
    text-align: right;
    color: #6c757d;
    font-size: 0.9rem;
}

select {
    width: 100%;
    padding: 10px;
    border-radius: 6px;
    border: 1px solid #ced4da;
    margin-bottom: 20px;
}

detail-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
}

detail-item {
    padding: 15px;
    background: #f8f9fa;
    border-radius: 8px;
}

detail-label {
    font-weight: 600;
    margin-bottom: 8px;
    color: #6c757d;
}

detail-value {
    font-size: 1.2rem;
    font-weight: 700;
    color: #2c3e50;
}

footer {
    text-align: center;
    color: #6c757d;
    padding: 20px 0;
}

/* Agent status badges */
.status-badge {
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 600;
}

.status-badge.idle {
    background: #e2e3e5;
    color: #41464b;
}

.status-badge.training {
    background: #cff4fc;
    color: #055160;
}

.status-badge.simulating {
    background: #d1e7dd;
    color: #0f5132;
}

.status-badge.terminated {
    background: #f8d7da;
    color: #842029;
}
                    
.main-nav {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
}

.nav-link {
    padding: 8px 16px;
    background: #f8f9fa;
    border-radius: 6px;
    text-decoration: none;
    color: #333;
}

.nav-link:hover {
    background: #e9ecef;
}

.nav-link.active {
    background: #007bff;
    color: white;
}
                    
                    /* Log Box Styles */
.log-container {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

.log-controls {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin-bottom: 10px;
    gap: 10px;
}

.log-button {
    padding: 6px 12px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.log-button:hover {
    background: #e9ecef;
}

.auto-refresh {
    display: flex;
    align-items: center;
    margin-left: auto;
    font-size: 0.9rem;
}

.auto-refresh input {
    margin-right: 5px;
}

.log-box {
    height: 250px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 10px;
    overflow-y: auto;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.85rem;
    line-height: 1.4;
}

.log-entry {
    margin-bottom: 5px;
    padding-bottom: 5px;
    border-bottom: 1px solid #eee;
    word-break: break-word;
}

.log-entry:last-child {
    margin-bottom: 0;
    border-bottom: none;
}

.log-entry.error {
    color: #dc3545;
}

.log-entry.warning {
    color: #ffc107;
}

.log-entry.success {
    color: #28a745;
}

/* Responsive styles */
@media (max-width: 1000px) {
    .dashboard {
        flex-direction: column;
    }
    
    .sidebar {
        width: 100%;
    }
}''')

    # Create JavaScript file if it doesn't exist
    if not os.path.exists('static/dashboard.js'):
        with open('static/dashboard.js', 'w') as f:
            f.write('''// Global variables
let agentData = {};
let selectedAgent = null;
let refreshInterval = 5000; // 5 seconds

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initial data fetch
    fetchAgentStatus();
    fetchLatestCharts();
    
    // Set up periodic refreshes
    setInterval(fetchAgentStatus, refreshInterval);
    setInterval(fetchLatestCharts, refreshInterval * 6); // Refresh charts less frequently
    
    // Set up agent selector change event
    document.getElementById('agent-selector').addEventListener('change', function(e) {
        selectedAgent = e.target.value;
        updateAgentDetails();
    });
});

// Fetch the status of all agents
function fetchAgentStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // Update UI with the received data
            updateStatusUI(data);
            // Also fetch detailed data
            fetchAgentData();
        })
        .catch(error => {
            console.error('Error fetching agent status:', error);
        });
}

// Fetch detailed data for all agents
function fetchAgentData() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            agentData = data;
            updateAgentDetails();
        })
        .catch(error => {
            console.error('Error fetching agent data:', error);
        });
}

// Fetch the latest chart information
function fetchLatestCharts() {
    fetch('/api/latest_charts')
        .then(response => response.json())
        .then(data => {
            document.getElementById('rewards-img').src = data.rewards_chart;
            document.getElementById('queue-img').src = data.queue_chart;
            document.getElementById('chart-update-time').textContent = data.timestamp;
        })
        .catch(error => {
            console.error('Error fetching latest charts:', error);
        });
}

// Update the UI with agent status information
function updateStatusUI(statusData) {
    // Update summary statistics
    document.getElementById('total-agents').textContent = statusData.total_agents;
    document.getElementById('online-agents').textContent = statusData.online_agents;
    document.getElementById('last-update-time').textContent = new Date().toLocaleTimeString();
    
    // Update agent list
    const agentListContainer = document.getElementById('agent-list-container');
    
    if (statusData.total_agents === 0) {
        agentListContainer.innerHTML = '<p>No agents connected</p>';
        return;
    }
    
    let agentListHTML = '';
    for (const [agentId, agentInfo] of Object.entries(statusData.agents)) {
        const statusClass = agentInfo.online ? 'online' : 'offline';
        const statusBadge = getStatusBadge(agentInfo.status);
        
        agentListHTML += `
            <div class="agent-item">
                <div>
                    <span class="agent-status ${statusClass}"></span>
                    <span class="agent-name">${agentId}</span>
                    ${statusBadge}
                </div>
                <div>
                    <span class="agent-episode">Ep: ${agentInfo.last_episode}</span>
                </div>
            </div>
        `;
    }
    
    agentListContainer.innerHTML = agentListHTML;
    
    // Update agent selector
    const agentSelector = document.getElementById('agent-selector');
    const currentValue = agentSelector.value;
    
    // Clear existing options except the first one
    while (agentSelector.options.length > 1) {
        agentSelector.remove(1);
    }
    
    // Add options for each agent
    for (const agentId of Object.keys(statusData.agents)) {
        const option = document.createElement('option');
        option.value = agentId;
        option.textContent = agentId;
        agentSelector.appendChild(option);
    }
    
    // Restore selected value if possible
    if (currentValue && Array.from(agentSelector.options).some(opt => opt.value === currentValue)) {
        agentSelector.value = currentValue;
    }
}

// Update the agent details section
function updateAgentDetails() {
    const detailContainer = document.getElementById('agent-detail-container');
    
    if (!selectedAgent || !agentData[selectedAgent]) {
        detailContainer.innerHTML = '<p>Select an agent to view details</p>';
        return;
    }
    
    const agent = agentData[selectedAgent];
    
    // Format configuration
    let configHTML = '';
    if (agent.config) {
        for (const [key, value] of Object.entries(agent.config)) {
            configHTML += `<div class="config-item">
                <span class="config-key">${key}:</span>
                <span class="config-value">${value}</span>
            </div>`;
        }
    }
    
    // Get last episode data
    const lastEpisode = agent.last_episode || 0;
    const rewardValue = agent.rewards && agent.rewards.length > 0 ? 
        agent.rewards[agent.rewards.length - 1].toFixed(2) : 'N/A';
    const queueValue = agent.queue_lengths && agent.queue_lengths.length > 0 ? 
        agent.queue_lengths[agent.queue_lengths.length - 1].toFixed(2) : 'N/A';
    
    detailContainer.innerHTML = `
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">Status</div>
                <div class="detail-value">${agent.status || 'Unknown'}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Current Episode</div>
                <div class="detail-value">${lastEpisode}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Latest Reward</div>
                <div class="detail-value">${rewardValue}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Latest Queue Length</div>
                <div class="detail-value">${queueValue}</div>
            </div>
        </div>
        
        <h3 class="section-title">Agent Configuration</h3>
        <div class="config-container">
            ${configHTML || '<p>No configuration available</p>'}
        </div>
    `;
}

// Switch between chart tabs
function showChart(chartType) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // Find the clicked button and activate it
    const activeButton = Array.from(tabButtons).find(button => {
        return button.textContent.toLowerCase().includes(chartType);
    });
    
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Update chart displays
    const charts = document.querySelectorAll('.chart');
    charts.forEach(chart => {
        chart.classList.remove('active');
    });
    
    document.getElementById(`${chartType}-chart`).classList.add('active');
}

// Helper function to get a status badge HTML
function getStatusBadge(status) {
    if (!status) return '';
    
    let badgeClass = 'idle';
    
    if (status === 'training') {
        badgeClass = 'training';
    } else if (status === 'simulating') {
        badgeClass = 'simulating';
    } else if (status === 'terminated') {
        badgeClass = 'terminated';
    }
    
    return `<span class="status-badge ${badgeClass}">${status}</span>`;
}''')

    # Generate an initial map
    try:
        generate_intersection_map()
        print("Generated initial map")
    except Exception as e:
        print(f"Error generating initial map: {e}")

    # Start the background thread for saving data
    bg_thread = threading.Thread(target=save_data_periodically, daemon=True)
    bg_thread.start()

    # Start system status update thread
    status_thread = threading.Thread(target=update_system_status)
    status_thread.daemon = True
    status_thread.start()

    # Run the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)