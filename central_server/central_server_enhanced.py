from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import os
import time
import threading
import math
import numpy as np
from datetime import datetime, timedelta
from collections import deque

app = Flask(__name__)
CORS(app)  # Allow access from Flutter Web
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

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
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

def log_event(message):
    """Add a message to the server logs with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    server_logs.append(log_entry)
    print(log_entry)

# === API ENDPOINTS ===

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return jsonify({'message': 'Traffic Control Server is running', 'status': 'online'})

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
    
    # If no data, create some sample data
    if not agent_data:
        sample_data = create_sample_data()
        intersections = sample_data['intersections']
    else:
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
                    'averageWaitTime': float(np.mean(data.get('waiting_times', [30.0])[-10:])) if data.get('waiting_times') else 30.0,
                    'averageQueueLength': float(np.mean(data.get('queue_lengths', [5.0])[-10:])) if data.get('queue_lengths') else 5.0,
                    'vehicleCount': len(data.get('queue_lengths', [])),
                    'throughput': float(np.random.uniform(50, 150)),
                    'efficiency': float(np.random.uniform(0.7, 0.95)),
                    'waitTimes': [float(x) for x in data.get('waiting_times', [])[-24:]],  # Last 24 data points
                    'queueLengths': [float(x) for x in data.get('queue_lengths', [])[-24:]],  # Last 24 data points
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

def create_sample_data():
    """Create sample intersection data for demo purposes"""
    return {
        'intersections': [
            {
                'id': 'demo_1',
                'name': 'Main St & 1st Ave',
                'latitude': 10.777807,
                'longitude': 106.681676,
                'status': 'online',
                'lastUpdate': datetime.now().isoformat(),
                'configuration': {'cycles_per_hour': 120, 'optimization_mode': 'adaptive'},
                'metrics': {
                    'averageWaitTime': 28.5,
                    'averageQueueLength': 4.2,
                    'vehicleCount': 156,
                    'throughput': 85.3,
                    'efficiency': 0.87,
                    'waitTimes': [float(np.random.uniform(15, 45)) for _ in range(24)],
                    'queueLengths': [float(np.random.uniform(2, 8)) for _ in range(24)],
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
                'connectedIntersections': ['demo_2']
            },
            {
                'id': 'demo_2',
                'name': 'Main St & 2nd Ave',
                'latitude': 10.778807,
                'longitude': 106.682676,
                'status': 'online',
                'lastUpdate': datetime.now().isoformat(),
                'configuration': {'cycles_per_hour': 100, 'optimization_mode': 'fixed'},
                'metrics': {
                    'averageWaitTime': 32.1,
                    'averageQueueLength': 5.8,
                    'vehicleCount': 142,
                    'throughput': 72.6,
                    'efficiency': 0.82,
                    'waitTimes': [float(np.random.uniform(20, 50)) for _ in range(24)],
                    'queueLengths': [float(np.random.uniform(3, 9)) for _ in range(24)],
                    'timestamp': datetime.now().isoformat()
                },
                'phases': [
                    {
                        'id': 'phase_1',
                        'name': 'North-South',
                        'directions': ['north', 'south'],
                        'duration': 35,
                        'isActive': False,
                        'yellowTime': 3,
                        'redTime': 2,
                        'configuration': {}
                    },
                    {
                        'id': 'phase_2',
                        'name': 'East-West',
                        'directions': ['east', 'west'],
                        'duration': 30,
                        'isActive': True,
                        'yellowTime': 3,
                        'redTime': 2,
                        'configuration': {}
                    }
                ],
                'connectedIntersections': ['demo_1']
            }
        ]
    }

@app.route('/api/agent/<agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Get all data for a specific agent"""
    if agent_id in agent_data:
        return jsonify(agent_data[agent_id])
    else:
        return jsonify({'error': 'Agent not found'}), 404

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

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Endpoint to retrieve server logs"""
    return jsonify({'logs': list(server_logs)})

@app.route('/api/reset', methods=['POST'])
def reset_server_data():
    """Clear all stored data and reset the server state"""
    global agent_data, last_update, training_sessions, system_alerts
    agent_data = {}
    last_update = {}
    training_sessions = {}
    system_alerts = []

    log_event("Server data has been reset")
    return jsonify({'status': 'success', 'message': 'Server data has been reset'}), 200

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
        agents = agent_data if agent_data else {'demo_1': {}, 'demo_2': {}}  # Fallback to demo data
    
    current_time = datetime.now()
    
    # Generate sample metrics for the dashboard
    for agent_id, data in agents.items():
        # Performance metrics
        metrics.extend([
            {
                'name': f'Average Wait Time - {agent_id}',
                'value': float(data.get('metrics', {}).get('average_wait_time', np.random.uniform(15, 45))),
                'unit': 'seconds',
                'previousValue': float(np.random.uniform(20, 50)),
                'trend': 'down' if np.random.random() > 0.5 else 'up',
                'timestamp': current_time.isoformat()
            },
            {
                'name': f'Queue Length - {agent_id}',
                'value': float(data.get('metrics', {}).get('average_queue_length', np.random.uniform(2, 8))),
                'unit': 'vehicles',
                'previousValue': float(np.random.uniform(3, 10)),
                'trend': 'down' if np.random.random() > 0.5 else 'up',
                'timestamp': current_time.isoformat()
            },
            {
                'name': f'Efficiency - {agent_id}',
                'value': float(data.get('metrics', {}).get('efficiency', np.random.uniform(0.7, 0.95))),
                'unit': '%',
                'previousValue': float(np.random.uniform(0.6, 0.9)),
                'trend': 'up' if np.random.random() > 0.5 else 'down',
                'timestamp': current_time.isoformat()
            }
        ])
        
        # Generate time series data
        for i in range(24):  # 24 hours of data
            time_point = current_time - timedelta(hours=23-i)
            
            wait_time_series.append({
                'timestamp': time_point.isoformat(),
                'value': float(np.random.uniform(10, 60)),
                'label': f'{agent_id}_wait_time'
            })
            
            queue_length_series.append({
                'timestamp': time_point.isoformat(),
                'value': float(np.random.uniform(1, 10)),
                'label': f'{agent_id}_queue_length'
            })
            
            throughput_series.append({
                'timestamp': time_point.isoformat(),
                'value': float(np.random.uniform(50, 200)),
                'label': f'{agent_id}_throughput'
            })
    
    # Aggregated metrics
    aggregated_metrics = {
        'totalIntersections': len(agents),
        'averageWaitTime': float(np.mean([m['value'] for m in metrics if 'Wait Time' in m['name']])) if metrics else 0.0,
        'averageQueueLength': float(np.mean([m['value'] for m in metrics if 'Queue Length' in m['name']])) if metrics else 0.0,
        'systemEfficiency': float(np.mean([m['value'] for m in metrics if 'Efficiency' in m['name']])) if metrics else 0.8,
        'totalVehicles': int(sum([data.get('metrics', {}).get('vehicle_count', np.random.randint(50, 200)) for data in agents.values()]))
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
            'cameras': data.get('cameras', [
                {'id': f'{agent_id}_cam_N', 'direction': 'north', 'latitude': data.get('latitude', 10.777807) + 0.0008, 'longitude': data.get('longitude', 106.681676), 'range': 200, 'active': True},
                {'id': f'{agent_id}_cam_E', 'direction': 'east', 'latitude': data.get('latitude', 10.777807), 'longitude': data.get('longitude', 106.681676) + 0.0008, 'range': 200, 'active': True},
                {'id': f'{agent_id}_cam_S', 'direction': 'south', 'latitude': data.get('latitude', 10.777807) - 0.0008, 'longitude': data.get('longitude', 106.681676), 'range': 200, 'active': True},
                {'id': f'{agent_id}_cam_W', 'direction': 'west', 'latitude': data.get('latitude', 10.777807), 'longitude': data.get('longitude', 106.681676) - 0.0008, 'range': 200, 'active': True}
            ]),
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
        save_intersection_data()  # Save to file
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

@app.route('/api/intersections/<intersection_id>', methods=['PUT'])
def update_intersection(intersection_id):
    """Update intersection configuration"""
    try:
        data = request.get_json()
        
        if intersection_id not in agent_data:
            return jsonify({'status': 'error', 'message': 'Intersection not found'}), 404
        
        # Update intersection data
        intersection = agent_data[intersection_id]
        intersection.update({
            'name': data.get('name', intersection.get('name')),
            'latitude': data.get('latitude', intersection.get('latitude')),
            'longitude': data.get('longitude', intersection.get('longitude')),
            'configuration': data.get('configuration', intersection.get('configuration', {})),
            'cameras': data.get('cameras', intersection.get('cameras', [])),
            'phases': data.get('phases', intersection.get('phases', [])),
            'connectedIntersections': data.get('connectedIntersections', intersection.get('connectedIntersections', [])),
            'lastUpdate': datetime.now().isoformat()
        })
        
        last_update[intersection_id] = time.time()
        save_intersection_data()  # Save to file
        log_event(f"Updated intersection: {intersection_id}")
        
        # Emit WebSocket update
        socketio.emit('intersection_update', {
            'type': 'intersection_updated',
            'data': intersection
        })
        
        return jsonify({'status': 'success', 'data': intersection})
    except Exception as e:
        log_event(f"ERROR updating intersection: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/intersections/<intersection_id>/position', methods=['PUT'])
def update_intersection_position(intersection_id):
    """Update intersection position"""
    try:
        data = request.get_json()
        
        if intersection_id not in agent_data:
            return jsonify({'status': 'error', 'message': 'Intersection not found'}), 404
        
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if latitude is None or longitude is None:
            return jsonify({'status': 'error', 'message': 'Latitude and longitude required'}), 400
        
        # Update intersection position
        intersection = agent_data[intersection_id]
        old_lat = intersection.get('latitude', 0)
        old_lng = intersection.get('longitude', 0)
        
        intersection['latitude'] = latitude
        intersection['longitude'] = longitude
        intersection['lastUpdate'] = datetime.now().isoformat()
        
        # Update camera positions relative to new intersection position
        if 'cameras' in intersection:
            lat_diff = latitude - old_lat
            lng_diff = longitude - old_lng
            
            for camera in intersection['cameras']:
                camera['latitude'] = camera.get('latitude', 0) + lat_diff
                camera['longitude'] = camera.get('longitude', 0) + lng_diff
        
        last_update[intersection_id] = time.time()
        save_intersection_data()  # Save to file
        log_event(f"Updated position for intersection: {intersection_id}")
        
        # Emit WebSocket update
        socketio.emit('intersection_update', {
            'type': 'position_updated',
            'data': intersection
        })
        
        return jsonify({'status': 'success', 'data': intersection})
    except Exception as e:
        log_event(f"ERROR updating intersection position: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/intersections/<intersection_id>/cameras', methods=['PUT'])
def update_intersection_cameras(intersection_id):
    """Update intersection camera configuration"""
    try:
        data = request.get_json()
        
        if intersection_id not in agent_data:
            return jsonify({'status': 'error', 'message': 'Intersection not found'}), 404
        
        cameras = data.get('cameras')
        if not cameras:
            return jsonify({'status': 'error', 'message': 'Cameras configuration required'}), 400
        
        # Update cameras
        intersection = agent_data[intersection_id]
        intersection['cameras'] = cameras
        intersection['lastUpdate'] = datetime.now().isoformat()
        
        last_update[intersection_id] = time.time()
        save_intersection_data()  # Save to file
        log_event(f"Updated cameras for intersection: {intersection_id}")
        
        # Emit WebSocket update
        socketio.emit('intersection_update', {
            'type': 'cameras_updated',
            'data': intersection
        })
        
        return jsonify({'status': 'success', 'data': intersection})
    except Exception as e:
        log_event(f"ERROR updating intersection cameras: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def generate_mock_intersections():
    """Generate mock intersection data based on the 4 intersection agent configurations"""
    mock_intersections = [
        {
            'id': 'agent1',
            'name': 'Dien Bien Phu - Hai Ba Trung', 
            'latitude': 10.786519,
            'longitude': 106.693680,
            'status': 'online',
            'lastUpdate': datetime.now().isoformat(),
            'configuration': {'cycles_per_hour': 120, 'optimization_mode': 'adaptive'},
            'cameras': [
                {
                    'id': 'agent1_north',
                    'direction': 'north',
                    'latitude': 10.786719,  # Slightly north
                    'longitude': 106.693680,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent1_east', 
                    'direction': 'east',
                    'latitude': 10.786519,
                    'longitude': 106.693880,  # Slightly east
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent1_south',
                    'direction': 'south', 
                    'latitude': 10.786319,  # Slightly south
                    'longitude': 106.693680,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent1_west',
                    'direction': 'west',
                    'latitude': 10.786519,
                    'longitude': 106.693480,  # Slightly west
                    'range': 100,
                    'active': True
                }
            ],
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
            'connectedIntersections': ['agent2', 'agent3'],
            'metrics': {
                'averageWaitTime': 25.4,
                'averageQueueLength': 3.8,
                'vehicleCount': 145,
                'throughput': 92.1,
                'efficiency': 0.85,
                'waitTimes': [float(np.random.uniform(15, 35)) for _ in range(24)],
                'queueLengths': [float(np.random.uniform(2, 6)) for _ in range(24)],
                'timestamp': datetime.now().isoformat()
            }
        },
        {
            'id': 'agent2',
            'name': 'Dien Bien Phu - Dinh Tien Hoang',
            'latitude': 10.799418,
            'longitude': 106.694178,
            'status': 'online',
            'lastUpdate': datetime.now().isoformat(),
            'configuration': {'cycles_per_hour': 110, 'optimization_mode': 'adaptive'},
            'cameras': [
                {
                    'id': 'agent2_north',
                    'direction': 'north',
                    'latitude': 10.799618,
                    'longitude': 106.694178,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent2_east',
                    'direction': 'east', 
                    'latitude': 10.799418,
                    'longitude': 106.694378,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent2_south',
                    'direction': 'south',
                    'latitude': 10.799218,
                    'longitude': 106.694178,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent2_west',
                    'direction': 'west',
                    'latitude': 10.799418,
                    'longitude': 106.693978,
                    'range': 100,
                    'active': True
                }
            ],
            'phases': [
                {
                    'id': 'phase_1',
                    'name': 'North-South',
                    'directions': ['north', 'south'],
                    'duration': 28,
                    'isActive': False,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                },
                {
                    'id': 'phase_2',
                    'name': 'East-West',
                    'directions': ['east', 'west'],
                    'duration': 32,
                    'isActive': True,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                }
            ],
            'connectedIntersections': ['agent1', 'agent4'],
            'metrics': {
                'averageWaitTime': 28.7,
                'averageQueueLength': 4.5,
                'vehicleCount': 168,
                'throughput': 87.3,
                'efficiency': 0.82,
                'waitTimes': [float(np.random.uniform(18, 40)) for _ in range(24)],
                'queueLengths': [float(np.random.uniform(3, 7)) for _ in range(24)],
                'timestamp': datetime.now().isoformat()
            }
        },
        {
            'id': 'agent3',
            'name': 'Hai Ba Trung - Nguyen Thi Minh Khai',
            'latitude': 10.782851,
            'longitude': 106.698079,
            'status': 'online', 
            'lastUpdate': datetime.now().isoformat(),
            'configuration': {'cycles_per_hour': 130, 'optimization_mode': 'fixed'},
            'cameras': [
                {
                    'id': 'agent3_north',
                    'direction': 'north',
                    'latitude': 10.783051,
                    'longitude': 106.698079,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent3_east',
                    'direction': 'east',
                    'latitude': 10.782851,
                    'longitude': 106.698279,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent3_south', 
                    'direction': 'south',
                    'latitude': 10.782651,
                    'longitude': 106.698079,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent3_west',
                    'direction': 'west',
                    'latitude': 10.782851,
                    'longitude': 106.697879,
                    'range': 100,
                    'active': True
                }
            ],
            'phases': [
                {
                    'id': 'phase_1',
                    'name': 'North-South',
                    'directions': ['north', 'south'],
                    'duration': 25,
                    'isActive': True,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                },
                {
                    'id': 'phase_2',
                    'name': 'East-West',
                    'directions': ['east', 'west'],
                    'duration': 30,
                    'isActive': False,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                }
            ],
            'connectedIntersections': ['agent1', 'agent4'],
            'metrics': {
                'averageWaitTime': 22.1,
                'averageQueueLength': 3.2,
                'vehicleCount': 134,
                'throughput': 98.5,
                'efficiency': 0.89,
                'waitTimes': [float(np.random.uniform(12, 32)) for _ in range(24)],
                'queueLengths': [float(np.random.uniform(2, 5)) for _ in range(24)],
                'timestamp': datetime.now().isoformat()
            }
        },
        {
            'id': 'agent4',
            'name': 'Nguyen Thi Minh Khai - Dinh Tien Hoang',
            'latitude': 10.786750,
            'longitude': 106.701765,
            'status': 'online',
            'lastUpdate': datetime.now().isoformat(),
            'configuration': {'cycles_per_hour': 100, 'optimization_mode': 'adaptive'},
            'cameras': [
                {
                    'id': 'agent4_north',
                    'direction': 'north',
                    'latitude': 10.786950,
                    'longitude': 106.701765,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent4_east',
                    'direction': 'east',
                    'latitude': 10.786750,
                    'longitude': 106.701965,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent4_south',
                    'direction': 'south',
                    'latitude': 10.786550,
                    'longitude': 106.701765,
                    'range': 100,
                    'active': True
                },
                {
                    'id': 'agent4_west',
                    'direction': 'west',
                    'latitude': 10.786750,
                    'longitude': 106.701565,
                    'range': 100,
                    'active': True
                }
            ],
            'phases': [
                {
                    'id': 'phase_1',
                    'name': 'North-South',
                    'directions': ['north', 'south'],
                    'duration': 35,
                    'isActive': False,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                },
                {
                    'id': 'phase_2',
                    'name': 'East-West',
                    'directions': ['east', 'west'],
                    'duration': 28,
                    'isActive': True,
                    'yellowTime': 3,
                    'redTime': 2,
                    'configuration': {}
                }
            ],
            'connectedIntersections': ['agent2', 'agent3'],
            'metrics': {
                'averageWaitTime': 31.6,
                'averageQueueLength': 5.1,
                'vehicleCount': 187,
                'throughput': 79.8,
                'efficiency': 0.78,
                'waitTimes': [float(np.random.uniform(20, 45)) for _ in range(24)],
                'queueLengths': [float(np.random.uniform(3, 8)) for _ in range(24)],
                'timestamp': datetime.now().isoformat()
            }
        }
    ]
    
    # Save the mock data to agent_data for persistence
    for intersection in mock_intersections:
        agent_data[intersection['id']] = intersection
        last_update[intersection['id']] = time.time()
    
    log_event("Generated mock intersection data based on intersection agent configs")
    return mock_intersections

@app.route('/api/intersections', methods=['GET'])
def get_intersections():
    """Get all intersections configuration"""
    try:
        intersections = []
        
        # If no intersections exist, generate mock data
        if not agent_data:
            intersections = generate_mock_intersections()
        else:
            for agent_id, data in agent_data.items():
                intersection = {
                    'id': agent_id,
                    'name': data.get('name', f'Intersection {agent_id}'),
                    'latitude': data.get('latitude', 10.777807),
                    'longitude': data.get('longitude', 106.681676),
                    'status': 'online' if agent_id in last_update and (time.time() - last_update[agent_id] <= TIMEOUT_THRESHOLD) else 'offline',
                    'lastUpdate': data.get('lastUpdate', datetime.now().isoformat()),
                    'configuration': data.get('configuration', {}),
                    'cameras': data.get('cameras', []),
                    'phases': data.get('phases', []),
                    'connectedIntersections': data.get('connectedIntersections', []),
                    'metrics': data.get('metrics', {})
                }
                intersections.append(intersection)
        
        return jsonify({'status': 'success', 'intersections': intersections})
    except Exception as e:
        log_event(f"ERROR getting intersections: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def save_intersection_data():
    """Save intersection data to file"""
    try:
        with open('server_data/intersections.json', 'w') as f:
            json.dump(agent_data, f, indent=2, default=str)
    except Exception as e:
        log_event(f"ERROR saving intersection data: {str(e)}")

def load_intersection_data():
    """Load intersection data from file"""
    try:
        if os.path.exists('server_data/intersections.json'):
            with open('server_data/intersections.json', 'r') as f:
                loaded_data = json.load(f)
                agent_data.update(loaded_data)
                log_event(f"Loaded {len(loaded_data)} intersections from file")
    except Exception as e:
        log_event(f"ERROR loading intersection data: {str(e)}")

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
                session['metrics']['reward'].append(float(np.random.uniform(-50, 50)))
                session['metrics']['loss'].append(float(np.random.uniform(0.1, 2.0)))
                session['metrics']['episode_length'].append(int(np.random.randint(50, 200)))
            
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

# Load existing intersection data on startup
load_intersection_data()

if __name__ == '__main__':
    log_event("Starting Traffic Control Central Server (Enhanced)")
    
    # Start the background thread for periodic system updates
    def periodic_broadcast():
        while True:
            time.sleep(30)  # Broadcast every 30 seconds
            broadcast_system_update()
    
    bg_thread = threading.Thread(target=periodic_broadcast, daemon=True)
    bg_thread.start()
    
    # Run the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True) 