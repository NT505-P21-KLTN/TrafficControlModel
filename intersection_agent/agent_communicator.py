import requests
import json
import time
import socket
import threading
import os
import numpy as np
import traci
import logging
from main_window import MainWindow


logger = logging.getLogger(__name__)

class AgentCommunicatorTraining:
    def __init__(self, server_url, agent_id=None, mapping_config=None, env_file_path=None):
        """
        Initialize the communicator with the server URL
        
        Args:
            server_url: URL of the central server
            agent_id: Unique ID for this agent (if None, hostname will be used)
            location_data: Dictionary containing location information (lat, long, intersection name)
            env_file_path: Path to the environment.net.xml file
        """
        self.server_url = server_url
        self.agent_id = agent_id or socket.gethostname()
        
        # Initialize direct connections (for direct agent-to-agent communication)
        self.direct_connections = {}
        
        self.data = {
            'agent_id': self.agent_id,
            'rewards': [],
            'queue_lengths': [],
            'waiting_times': [],
            'status': 'initializing',
            'last_episode': -1,
            'config': {},
            'model_info': {}
        }
        
        # Add new structure for current data (to be sent in next sync)
        self.current_data = {
            'agent_id': self.agent_id,
            'rewards': [],
            'queue_lengths': [],
            'waiting_times': [],
            'status': 'initializing',
            'last_episode': -1,
            'states': []
        }
        
        # Store location data separately - will be sent only on first sync
        self.mapping_config = mapping_config if mapping_config else {}
        self.env_file_path = env_file_path
        self.env_info = self._extract_env_info() if env_file_path else None
        self.topology_sent = False
        
        self.last_sync = 0
        self.sync_interval = 30  # seconds
        self.background_thread = None
        self.running = False
        
        # Create a directory to store data locally in case of connection issues
        self.backup_dir = f'agent_{self.agent_id}_data'
        os.makedirs(self.backup_dir, exist_ok=True)
        
        print(f"Agent communicator initialized with ID: {self.agent_id}")
        
        # Clean up any old transfer vehicles for this agent to ensure fresh start
        self._cleanup_old_transfers()
        
        # Log what will be sent on first sync
        if self.mapping_config:
            print(f"Mapping configuration will be sent on first sync")
        if env_file_path:
            print(f"Environment topology data will be sent on first sync")
    
    def _cleanup_old_transfers(self):
        """Clean up any old transfer vehicle records for this agent to ensure fresh start"""
        try:
            print(f"[INIT] Cleaning up old transfer records for agent {self.agent_id}")
            
            # Get all transfers for this agent
            response = requests.get(f"{self.server_url}/api/vehicle_transfers?agent_id={self.agent_id}", timeout=5)
            if response.status_code == 200:
                transfers = response.json()
                if transfers:
                    print(f"[INIT] Found {len(transfers)} old transfer records to clean up")
                    
                    # Delete each old transfer
                    cleaned_count = 0
                    for transfer in transfers:
                        vehicle_id = transfer.get('vehicle_id')
                        if vehicle_id:
                            try:
                                delete_response = requests.delete(f"{self.server_url}/api/vehicle_transfer/{vehicle_id}", timeout=2)
                                if delete_response.status_code == 200:
                                    cleaned_count += 1
                            except Exception as e:
                                print(f"[INIT] Failed to delete transfer for vehicle {vehicle_id}: {e}")
                    
                    print(f"[INIT] Successfully cleaned up {cleaned_count} old transfer records")
                else:
                    print(f"[INIT] No old transfer records found for agent {self.agent_id}")
            else:
                print(f"[INIT] Could not retrieve transfer records for cleanup (status: {response.status_code})")
                
        except Exception as e:
            print(f"[INIT] Warning: Failed to cleanup old transfers: {e}")
            print(f"[INIT] Continuing with initialization...")
    
    def start_background_sync(self):
        """Start a background thread to periodically sync with the server"""
        if self.background_thread is not None and self.background_thread.is_alive():
            return  # Already running
        
        self.running = True
        self.background_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.background_thread.start()
        
    def stop_background_sync(self):
        """Stop the background sync thread"""
        self.running = False
        if self.background_thread:
            self.background_thread.join(timeout=5)
    
    def _sync_loop(self):
        """Background thread function to periodically sync with server"""
        while self.running:
            try:
                self.sync_with_server()
            except Exception as e:
                print(f"Error in background sync: {e}")
                # Backup data locally
                self._backup_data()
            
            # Sleep until next sync
            time.sleep(self.sync_interval)
    
    def _backup_data(self):
        """Save data locally as backup in case of server connection issues"""
        backup_file = os.path.join(self.backup_dir, f'backup_{int(time.time())}.json')
        with open(backup_file, 'w') as f:
            json.dump(self.data, f)
    
    def update_episode_result(self, episode, reward, queue_length, waiting_time=None):
        """Update results for a specific episode"""
        # Update both master data and current data
        self.data['last_episode'] = episode
        self.current_data['last_episode'] = episode
        
        self.data['rewards'].append(float(reward))
        self.current_data['rewards'].append(float(reward))
        
        self.data['queue_lengths'].append(float(queue_length))
        self.current_data['queue_lengths'].append(float(queue_length))
        
        if waiting_time is not None:
            self.data['waiting_times'].append(float(waiting_time))
            self.current_data['waiting_times'].append(float(waiting_time))
        
        # If it's been long enough since last sync, sync now
        current_time = time.time()
        if current_time - self.last_sync >= self.sync_interval:
            self.sync_with_server()
    
    def update_status(self, status):
        """Update the agent's status"""
        self.data['status'] = status
        
    def update_config(self, config):
        """Update the agent's configuration"""
        self.data['config'] = config
        
    def update_model_info(self, model_info):
        """Update information about the model"""
        self.data['model_info'] = model_info
    
    def sync_with_server(self):
        """Send only current data to the central server"""
        try:
            # Create a copy of only the current data to send
            send_data = self.current_data.copy()
            
            # Add topology data only on first sync
            if not self.topology_sent:
                topology_data = {}
                
                # Add mapping configuration if available
                if self.mapping_config:
                    if isinstance(self.mapping_config, dict):
                        topology_data.update(self.mapping_config)
                    else:
                        print(f"Warning: mapping_config is not a dict, got {type(self.mapping_config)}. Skipping topology update.")
                
                # Add environment data if available
                if self.env_info:
                    topology_data['environment'] = self.env_info
                
                # Only add topology section if we have data to send
                if topology_data:
                    send_data['topology'] = topology_data
            
            # Only send if there's actual data to send
            if (len(send_data['rewards']) > 0 or 
                len(send_data['queue_lengths']) > 0 or 
                len(send_data['states']) > 0 or 
                not self.topology_sent):
                
                print("Sending current data to server:", send_data)
                response = requests.post(
                    f"{self.server_url}/api/update", 
                    json=send_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"Successfully synced with server. Episodes: {len(self.current_data['rewards'])}")
                    self.last_sync = time.time()
                    
                    # Clear current data after successful sync
                    self.current_data['rewards'] = []
                    self.current_data['queue_lengths'] = []
                    self.current_data['waiting_times'] = []
                    self.current_data['states'] = []
                    
                    # Mark topology as sent if it was included
                    if not self.topology_sent and 'topology' in send_data:
                        self.topology_sent = True
                        print(f"Topology data sent to server for agent {self.agent_id}")
                    
                    return True
                else:
                    print(f"Server sync failed with status code: {response.status_code}")
                    return False
            else:
                print("No new data to send")
                return True
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error during sync: {e}")
            return False
        
    def send_state(self, state, step, traffic_data):
        """Send state to server and connected agents"""
        try:
            # Send to server
            if self.server_url:
                # If there's vehicle transfer data, send it separately
                if traffic_data and 'vehicle_transfer' in traffic_data:
                    transfer_data = traffic_data['vehicle_transfer']
                    try:
                        response = requests.post(
                            f"{self.server_url}/api/vehicle_transfer",
                            json=transfer_data,
                            timeout=5
                        )
                        if response.status_code != 200:
                            print(f"Error sending vehicle transfer to server: {response.status_code}")
                    except Exception as e:
                        print(f"Error sending vehicle transfer: {e}")
                    
                    # Remove vehicle transfer from traffic data to avoid duplicate sending
                    traffic_data = traffic_data.copy()
                    del traffic_data['vehicle_transfer']
                
                # Send the rest of the state data
                # Handle different state types properly
                state_data = None
                if state is not None:
                    if hasattr(state, 'tolist'):
                        state_data = state.tolist()
                    elif isinstance(state, (list, tuple)):
                        state_data = list(state)
                    else:
                        state_data = state
                
                data = {
                    'agent_id': self.agent_id,
                    'step': step,
                    'state': state_data,
                    'traffic_data': traffic_data
                }
                response = requests.post(f"{self.server_url}/api/update", json=data)
                if response.status_code != 200:
                    print(f"Error sending state to server: {response.status_code}")
            
            # Send directly to connected agents
            for agent_id, connection in self.direct_connections.items():
                try:
                    data = {
                        'from_agent': self.agent_id,
                        'step': step,
                        'traffic_data': traffic_data
                    }
                    response = requests.post(f"{connection['url']}/api/agent_data", json=data)
                    if response.status_code != 200:
                        print(f"Error sending data to agent {agent_id}: {response.status_code}")
                except Exception as e:
                    print(f"Error sending data to agent {agent_id}: {e}")
                    
        except Exception as e:
            print(f"Error in send_state: {e}")
            
    def get_coordination_data(self):
        """Get coordination data from server including incoming vehicles"""
        try:
            # Get vehicle transfers for this agent
            transfer_response = requests.get(
                f"{self.server_url}/api/vehicle_transfers",
                params={'agent_id': self.agent_id},
                timeout=5
            )
            
            # Get general coordination data
            coord_response = requests.get(
                f"{self.server_url}/api/coordination/{self.agent_id}",
                timeout=5
            )
            
            # Combine the responses
            result = {}
            if coord_response.status_code == 200:
                result = coord_response.json()
                
            if transfer_response.status_code == 200:
                transfers = transfer_response.json()
                if 'coordination' not in result:
                    result['coordination'] = {}
                result['coordination']['incoming_vehicles'] = transfers
                
            return result if result else None
        except Exception as e:
            print(f"Error getting coordination data: {e}")
            return None

    def get_sync_timing(self):
        """Get synchronization timing from the central server"""
        try:
            response = requests.get(
                f"{self.server_url}/api/sync_times",
                timeout=5
            )
            if response.status_code == 200:
                sync_data = response.json()
                # Get timing data for this agent
                if self.agent_id in sync_data:
                    return sync_data[self.agent_id]
            return None
        except Exception as e:
            print(f"Error getting sync timing data: {e}")
            return None

    def _extract_env_info(self):
        """Extract relevant information from the environment.net.xml file"""
        if not self.env_file_path or not os.path.exists(self.env_file_path):
            print(f"Environment file not found: {self.env_file_path}")
            return None
            
        try:
            import xml.etree.ElementTree as ET
            
            # Parse the XML file
            tree = ET.parse(self.env_file_path)
            root = tree.getroot()
            
            # Extract location information
            location_elem = root.find('location')
            net_offset = location_elem.get('netOffset', '0.00,0.00') if location_elem else '0.00,0.00'
            conv_boundary = location_elem.get('convBoundary', '') if location_elem else ''
            
            # Extract junction information for the traffic light
            junctions = []
            for junction in root.findall('.//junction'):
                if junction.get('type') == 'traffic_light':
                    junctions.append({
                        'id': junction.get('id'),
                        'x': float(junction.get('x', 0)),
                        'y': float(junction.get('y', 0)),
                        'type': junction.get('type')
                    })
            
            # Extract edge information
            edges = []
            for edge in root.findall('.//edge'):
                if edge.get('function') != 'internal':  # Skip internal edges
                    edge_data = {
                        'id': edge.get('id'),
                        'from': edge.get('from', ''),
                        'to': edge.get('to', ''),
                        'lanes': []
                    }
                    
                    # Get lane information
                    for lane in edge.findall('lane'):
                        edge_data['lanes'].append({
                            'id': lane.get('id'),
                            'index': lane.get('index'),
                            'speed': lane.get('speed'),
                            'length': lane.get('length')
                        })
                    
                    edges.append(edge_data)
            
            # Extract traffic light phases
            tl_logic = []
            for tl in root.findall('.//tlLogic'):
                tl_data = {
                    'id': tl.get('id'),
                    'type': tl.get('type'),
                    'programID': tl.get('programID'),
                    'offset': tl.get('offset'),
                    'phases': []
                }
                
                for phase in tl.findall('phase'):
                    tl_data['phases'].append({
                        'duration': phase.get('duration'),
                        'state': phase.get('state')
                    })
                
                tl_logic.append(tl_data)
            
            return {
                'net_offset': net_offset,
                'boundary': conv_boundary,
                'junctions': junctions,
                'edges': edges,
                'tl_logic': tl_logic
            }
            
        except Exception as e:
            print(f"Error extracting environment information: {e}")
            return None

class AgentCommunicatorTesting:
    def __init__(self, server_url, agent_id, mapping_config=None, env_file_path=None):
        """
        Initialize the communicator with the server URL
        
        Args:
            server_url: URL of the central server
            agent_id: Unique ID for this agent
            mapping_config: Dictionary containing mapping configuration
            env_file_path: Path to the environment.net.xml file
        """
        self.server_url = server_url
        self.agent_id = agent_id
        self.data = {
            'agent_id': self.agent_id,
            'rewards': [],
            'queue_lengths': [],
            'waiting_times': [],
            'status': 'initializing',
            'last_episode': -1,
            'config': {},
            'model_info': {}
        }
        
        # Add new structure for current data (to be sent in next sync)
        self.current_data = {
            'agent_id': self.agent_id,
            'rewards': [],
            'queue_lengths': [],
            'waiting_times': [],
            'status': 'initializing',
            'last_episode': -1,
            'states': []
        }
        
        # Store location data separately - will be sent only on first sync
        self.mapping_config = mapping_config if mapping_config else {}
        self.env_file_path = env_file_path
        self.env_info = self._extract_env_info() if env_file_path else None
        self.topology_sent = False
        
        # Initialize connected agents tracking
        self.connected_agents = {}  # Store connected agent info
        self.direct_connections = {}  # Store direct connections
        
        # Initialize connections from mapping config if available
        if self.mapping_config and 'map' in self.mapping_config:
            map_config = self.mapping_config['map']
            if 'connected_to' in map_config:
                for connected_agent in map_config['connected_to']:
                    self.connected_agents[connected_agent] = {
                        'url': None,  # Will be populated when agent connects
                        'last_sync': 0,
                        'data': None
                    }
        
        self.last_sync = 0
        self.sync_interval = 30  # seconds
        self.background_thread = None
        self.running = False
        
        # Create a directory to store data locally in case of connection issues
        self.backup_dir = f'agent_{self.agent_id}_data'
        os.makedirs(self.backup_dir, exist_ok=True)
        
        print(f"Agent communicator initialized with ID: {self.agent_id}")
        
        # Clean up any old transfer vehicles for this agent to ensure fresh start
        self._cleanup_old_transfers()
        
        # Log what will be sent on first sync
        if self.mapping_config:
            print(f"Mapping configuration will be sent on first sync")
        if env_file_path:
            print(f"Environment topology data will be sent on first sync")
    
    def _cleanup_old_transfers(self):
        """Clean up any old transfer vehicle records for this agent to ensure fresh start"""
        try:
            print(f"[INIT] Cleaning up old transfer records for agent {self.agent_id}")
            
            # Get all transfers for this agent
            response = requests.get(f"{self.server_url}/api/vehicle_transfers?agent_id={self.agent_id}", timeout=5)
            if response.status_code == 200:
                transfers = response.json()
                if transfers:
                    print(f"[INIT] Found {len(transfers)} old transfer records to clean up")
                    
                    # Delete each old transfer
                    cleaned_count = 0
                    for transfer in transfers:
                        vehicle_id = transfer.get('vehicle_id')
                        if vehicle_id:
                            try:
                                delete_response = requests.delete(f"{self.server_url}/api/vehicle_transfer/{vehicle_id}", timeout=2)
                                if delete_response.status_code == 200:
                                    cleaned_count += 1
                            except Exception as e:
                                print(f"[INIT] Failed to delete transfer for vehicle {vehicle_id}: {e}")
                    
                    print(f"[INIT] Successfully cleaned up {cleaned_count} old transfer records")
                else:
                    print(f"[INIT] No old transfer records found for agent {self.agent_id}")
            else:
                print(f"[INIT] Could not retrieve transfer records for cleanup (status: {response.status_code})")
                
        except Exception as e:
            print(f"[INIT] Warning: Failed to cleanup old transfers: {e}")
            print(f"[INIT] Continuing with initialization...")
    
    def start_background_sync(self):
        """Start background sync thread"""
        if not self.running:
            self.running = True
            self.sync_thread = threading.Thread(target=self._sync_loop)
            self.sync_thread.daemon = True
            self.sync_thread.start()
    
    def _sync_loop(self):
        """Background sync loop"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_sync >= self.sync_interval:
                    self.sync_with_server()
                    self._sync_with_connected_agents()
                    self.last_sync = current_time
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in sync loop: {e}")
    
    def _sync_with_connected_agents(self):
        """Sync directly with connected agents"""
        for agent_id, agent_data in self.connected_agents.items():
            try:
                # Get data from connected agent
                if agent_id in self.direct_connections:
                    connection = self.direct_connections[agent_id]
                    response = requests.get(f"{connection['url']}/api/agent_data")
                    if response.status_code == 200:
                        data = response.json()
                        agent_data['data'] = data
                        agent_data['last_sync'] = time.time()
            except Exception as e:
                print(f"Error syncing with agent {agent_id}: {e}")
    
    def send_state(self, state, step, traffic_data):
        """Send state to server and connected agents"""
        try:
            # Send to server
            if self.server_url:
                # If there's vehicle transfer data, send it separately
                if traffic_data and 'vehicle_transfer' in traffic_data:
                    transfer_data = traffic_data['vehicle_transfer']
                    try:
                        response = requests.post(
                            f"{self.server_url}/api/vehicle_transfer",
                            json=transfer_data,
                            timeout=5
                        )
                        if response.status_code != 200:
                            print(f"Error sending vehicle transfer to server: {response.status_code}")
                    except Exception as e:
                        print(f"Error sending vehicle transfer: {e}")
                    
                    # Remove vehicle transfer from traffic data to avoid duplicate sending
                    traffic_data = traffic_data.copy()
                    del traffic_data['vehicle_transfer']
                
                # Send the rest of the state data
                # Handle different state types properly
                state_data = None
                if state is not None:
                    if hasattr(state, 'tolist'):
                        state_data = state.tolist()
                    elif isinstance(state, (list, tuple)):
                        state_data = list(state)
                    else:
                        state_data = state
                
                data = {
                    'agent_id': self.agent_id,
                    'step': step,
                    'state': state_data,
                    'traffic_data': traffic_data
                }
                response = requests.post(f"{self.server_url}/api/update", json=data)
                if response.status_code != 200:
                    print(f"Error sending state to server: {response.status_code}")
            
            # Send directly to connected agents
            for agent_id, connection in self.direct_connections.items():
                try:
                    data = {
                        'from_agent': self.agent_id,
                        'step': step,
                        'traffic_data': traffic_data
                    }
                    response = requests.post(f"{connection['url']}/api/agent_data", json=data)
                    if response.status_code != 200:
                        print(f"Error sending data to agent {agent_id}: {response.status_code}")
                except Exception as e:
                    print(f"Error sending data to agent {agent_id}: {e}")
                    
        except Exception as e:
            print(f"Error in send_state: {e}")
    
    def get_connected_agent_data(self, agent_id):
        """Get data from a connected agent"""
        if agent_id in self.connected_agents:
            agent_data = self.connected_agents[agent_id]
            if time.time() - agent_data['last_sync'] < 5.0:  # Data is fresh if less than 5 seconds old
                return agent_data['data']
        return None
    
    def add_direct_connection(self, agent_id, url):
        """Add a direct connection to another agent"""
        self.direct_connections[agent_id] = {
            'url': url,
            'last_sync': 0
        }
        if agent_id not in self.connected_agents:
            self.connected_agents[agent_id] = {
                'url': None,
                'last_sync': 0,
                'data': None
            }

    def sync_with_server(self):
        try:
            send_data = self.current_data.copy()
            if not self.topology_sent:
                topology_data = {}
                if self.mapping_config:
                    if isinstance(self.mapping_config, dict):
                        topology_data.update(self.mapping_config)
                    else:
                        print(f"[TEST] Warning: mapping_config is not a dict, got {type(self.mapping_config)}. Skipping topology update.")
                if self.env_info:
                    topology_data['environment'] = self.env_info
                if topology_data:
                    send_data['topology'] = topology_data
            if len(send_data['states']) > 0 or not self.topology_sent:
                #print("[TEST] Sending current data to server:", send_data)
                response = requests.post(
                    f"{self.server_url}/api/update",
                    json=send_data,
                    timeout=10
                )
                if response.status_code == 200:
                    print(f"[TEST] Successfully synced with server.")
                    self.last_sync = time.time()
                    self.current_data['states'] = []
                    if not self.topology_sent and 'topology' in send_data:
                        self.topology_sent = True
                        print(f"[TEST] Topology data sent to server for agent {self.agent_id}")
                    return True
                else:
                    print(f"[TEST] Server sync failed with status code: {response.status_code}")
                    return False
            else:
                print("[TEST] No new data to send")
                return True
        except requests.exceptions.RequestException as e:
            print(f"[TEST] Connection error during sync: {e}")
            return False

    def get_sync_timing(self):
        try:
            response = requests.get(
                f"{self.server_url}/api/sync_times",
                timeout=5
            )
            if response.status_code == 200:
                sync_data = response.json()
                if self.agent_id in sync_data:
                    return sync_data[self.agent_id]
            return None
        except Exception as e:
            print(f"[TEST] Error getting sync timing data: {e}")
            return None

    def _extract_env_info(self):
        """Extract relevant information from the environment.net.xml file"""
        if not self.env_file_path or not os.path.exists(self.env_file_path):
            print(f"Environment file not found: {self.env_file_path}")
            return None
            
        try:
            import xml.etree.ElementTree as ET
            
            # Parse the XML file
            tree = ET.parse(self.env_file_path)
            root = tree.getroot()
            
            # Extract location information
            location_elem = root.find('location')
            net_offset = location_elem.get('netOffset', '0.00,0.00') if location_elem else '0.00,0.00'
            conv_boundary = location_elem.get('convBoundary', '') if location_elem else ''
            
            # Extract junction information for the traffic light
            junctions = []
            for junction in root.findall('.//junction'):
                if junction.get('type') == 'traffic_light':
                    junctions.append({
                        'id': junction.get('id'),
                        'x': float(junction.get('x', 0)),
                        'y': float(junction.get('y', 0)),
                        'type': junction.get('type')
                    })
            
            # Extract edge information
            edges = []
            for edge in root.findall('.//edge'):
                if edge.get('function') != 'internal':  # Skip internal edges
                    edge_data = {
                        'id': edge.get('id'),
                        'from': edge.get('from', ''),
                        'to': edge.get('to', ''),
                        'lanes': []
                    }
                    
                    # Get lane information
                    for lane in edge.findall('lane'):
                        edge_data['lanes'].append({
                            'id': lane.get('id'),
                            'index': lane.get('index'),
                            'speed': lane.get('speed'),
                            'length': lane.get('length')
                        })
                    
                    edges.append(edge_data)
            
            # Extract traffic light phases
            tl_logic = []
            for tl in root.findall('.//tlLogic'):
                tl_data = {
                    'id': tl.get('id'),
                    'type': tl.get('type'),
                    'programID': tl.get('programID'),
                    'offset': tl.get('offset'),
                    'phases': []
                }
                
                for phase in tl.findall('phase'):
                    tl_data['phases'].append({
                        'duration': phase.get('duration'),
                        'state': phase.get('state')
                    })
                
                tl_logic.append(tl_data)
            
            return {
                'net_offset': net_offset,
                'boundary': conv_boundary,
                'junctions': junctions,
                'edges': edges,
                'tl_logic': tl_logic
            }
            
        except Exception as e:
            print(f"Error extracting environment information: {e}")
            return None

    def update_status(self, status):
        self.data['status'] = status
        self.current_data['status'] = status

    def update_config(self, config):
        self.data['config'] = config
        self.current_data['config'] = config

    def update_model_info(self, model_info):
        """Update information about the model"""
        self.data['model_info'] = model_info
        self.current_data['model_info'] = model_info

    def update_episode_result(self, episode, reward, queue_length, waiting_time=None):
        self.data['last_episode'] = episode
        self.current_data['last_episode'] = episode
        self.data['rewards'] = [float(reward)]
        self.current_data['rewards'] = [float(reward)]
        self.data['queue_lengths'] = [float(queue_length)]
        self.current_data['queue_lengths'] = [float(queue_length)]
        if waiting_time is not None:
            self.data['waiting_times'] = [float(waiting_time)]
            self.current_data['waiting_times'] = [float(waiting_time)]

    def get_coordination_data(self):
        """Get coordination data from server including incoming vehicles"""
        try:
            # Get vehicle transfers for this agent
            transfer_response = requests.get(
                f"{self.server_url}/api/vehicle_transfers",
                params={'agent_id': self.agent_id},
                timeout=5
            )
            
            # Get general coordination data
            coord_response = requests.get(
                f"{self.server_url}/api/coordination/{self.agent_id}",
                timeout=5
            )
            
            # Combine the responses
            result = {}
            if coord_response.status_code == 200:
                result = coord_response.json()
                
            if transfer_response.status_code == 200:
                transfers = transfer_response.json()
                if 'coordination' not in result:
                    result['coordination'] = {}
                result['coordination']['incoming_vehicles'] = transfers
                
            return result if result else None
        except Exception as e:
            print(f"Error getting coordination data: {e}")
            return None