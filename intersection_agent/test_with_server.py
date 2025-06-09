from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import datetime
import numpy as np
import configparser
import socket
import timeit
import traci
import argparse
import glob
import random
import requests
import time

from testing_simulation import Simulation
from generator import TrafficGenerator
from model import TestModel
from utils import import_test_configuration, set_sumo, set_test_path
from agent_communicator import AgentCommunicatorTesting
from interactive_simulation import InteractiveSimulation

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare the environment variable 'SUMO_HOME'")

def get_latest_model_for_agent(models_dir, agent_id, phase=None):
    """
    Find the latest model for a specific agent
    Args:
        models_dir: Directory containing model folders
        agent_id: Agent ID (e.g., 'agent1')
        phase: If specified, look for phase-based model (e.g., 'base', 'sync')
    Returns:
        tuple: (model_number, model_path) or (None, None) if no model found
    """
    # Extract agent number from agent_id (e.g., 'agent1' -> '1')
    agent_num = agent_id#.replace('agent', '')
    
    # Find all model directories
    model_dirs = glob.glob(os.path.join(models_dir, 'model_*'))
    if not model_dirs:
        return None, None
    
    # Sort directories by model number
    model_dirs.sort(key=lambda x: int(x.split('_')[-1]), reverse=True)
    
    # Look for the latest model that has a file for this agent
    for model_dir in model_dirs:
        model_num = int(model_dir.split('_')[-1])
        if phase:
            # For phase-based models, look for trained_model_{phase}.h5
            model_file = os.path.join(model_dir, f'trained_model_{phase}.h5')
        else:
            # For non-phase models, look for intersection_{num}_model.h5
            model_file = os.path.join(model_dir, f'intersection_{agent_num}_model.h5')
            
        if os.path.exists(model_file):
            return model_num, model_file
    
    return None, None

def read_server_config(config_file='server_config_2.ini'):
    if not os.path.exists(config_file):
        return None, None, None, None
    config = configparser.ConfigParser()
    config.read(config_file)
    if 'server' not in config:
        return None, None, None, None
    if not config['server'].getboolean('enabled', fallback=False):
        return None, None, None, None
    server_url = config['server'].get('server_url', None)
    agent_id = config['server'].get('agent_id', socket.gethostname())
    # Read location data if available
    location_data = None
    if 'location' in config:
        location_data = {
            'latitude': config['location'].get('latitude', None),
            'longitude': config['location'].get('longitude', None),
            'intersection_name': config['location'].get('intersection_name', f'Intersection {agent_id}'),
            'orientation': config['location'].get('orientation', '0')
        }
    # Read map configuration
    map_config = {}
    if 'map' in config:
        map_config = {
            'send_topology': config['map'].getboolean('send_topology', True),
            'environment_file': config['map'].get('environment_file', 'intersection/environment.net.xml'),
            'connection_distance': config['map'].getfloat('connection_distance', 1.5),
            'connected_to': [x.strip() for x in config['map'].get('connected_to', '').split(',') if x.strip()]
        }
    else:
        map_config = {
            'send_topology': True,
            'environment_file': 'intersection/environment.net.xml',
            'connection_distance': 1.5,
            'connected_to': []
        }
    # Read visualization options
    viz_config = {}
    if 'visualization' in config:
        viz_config = {
            'marker_color': config['visualization'].get('marker_color', 'green'),
            'marker_icon': config['visualization'].get('marker_icon', 'traffic-light')
        }
    mapping_config = {
        'location': location_data,
        'map': map_config,
        'visualization': viz_config
    }
    env_file_path = map_config['environment_file'] if map_config['send_topology'] else None
    if env_file_path and not os.path.exists(env_file_path):
        print(f"Warning: Environment file not found at {env_file_path}")
        env_file_path = None
    return server_url, agent_id, mapping_config, env_file_path

class TestingSimulationWithServer(Simulation):
    def __init__(self, Model, TrafficGen, sumo_cmd, max_steps, green_duration, 
                 yellow_duration, num_states, num_actions, server_url=None, agent_id=None,
                 mapping_config=None, env_file_path=None, no_route_file=False, disable_spawn_filtering=False):
        # Call the parent constructor with all parameters
        super().__init__(Model, TrafficGen, sumo_cmd, max_steps, green_duration, 
                         yellow_duration, num_states, num_actions, server_url, agent_id,
                         mapping_config, env_file_path, no_route_file, disable_spawn_filtering)
        
        # Initialize server communication if URL is provided
        self._server_url = server_url
        self._agent_id = agent_id  # Store agent_id again for clarity
        
        # Disable auto spawn if no_route_file is True
        if no_route_file:
            self.auto_spawn = False
            print(f"Auto spawn disabled due to -n flag for agent {self._agent_id}")
        
        if server_url:
            self._communicator = AgentCommunicatorTesting(server_url, agent_id, mapping_config, env_file_path)
            self._communicator.update_status("test_initialized")
            self._communicator.update_config({
                "max_steps": max_steps,
                "green_duration": green_duration,
                "yellow_duration": yellow_duration,
                "num_states": num_states,
                "num_actions": num_actions,
                "mode": "testing"
            })
            self._communicator.start_background_sync()
        else:
            self._communicator = None

    def run(self, episode):
        """
        Runs the testing simulation and reports to server if enabled
        """
        start_time = timeit.default_timer()

        if self._communicator:
            self._communicator.update_status("testing")
            
        # Reset episode arrays
        self._reward_episode = []
        self._queue_length_episode = []
            
        # Generate route file and start simulation
        self._TrafficGen.generate_routefile(seed=episode)
        traci.start(self._sumo_cmd)
        print("Simulating...")

        # Initialize simulation variables
        self._step = 0
        self._waiting_times = {}
        old_total_wait = 0
        old_action = -1  # dummy init

        # Get initial sync timing if available
        if self._communicator:
            sync_data = self._communicator.get_sync_timing()
            if sync_data:
                self._adjust_timing(sync_data)

        # Main simulation loop
        while self._step < self._max_steps:
            # Handle automatic spawning with random intervals
            if self.auto_spawn:
                if self.spawn_interval_random:
                    current_interval = random.randint(self.min_interval, self.max_interval)
                else:
                    current_interval = self.spawn_interval

                if (self._step - self.last_spawn_step) >= current_interval:
                    self.last_spawn_step = self._step
                    if self.spawn_count_random:
                        count = random.randint(self.min_count, self.max_count)
                    else:
                        count = self.spawn_count
                    for _ in range(count):
                        self._spawn_random_vehicle()
                    print(f"Spawned {count} vehicles")

            # Track vehicles and check for incoming vehicles
            self._track_vehicles()
            if self._communicator:
                self._check_incoming_vehicles()

            # Get current state of the intersection
            current_state = self._get_state()

            # Calculate reward of previous action
            current_total_wait = self._collect_waiting_times()
            reward = old_total_wait - current_total_wait

            # Choose the light phase to activate
            action = self._choose_action(current_state)
            print("Agent chose action:  ", action)

            # If the chosen phase is different from the last phase, activate the yellow phase
            if self._step != 0 and old_action != action:
                self._set_yellow_phase(old_action)
                self._simulate(self._yellow_duration)

            # Execute the green phase
            self._set_green_phase(action)
            self._simulate(self._green_duration)

            # Save variables for next step
            old_action = action
            old_total_wait = current_total_wait

            # Add reward to episode total
            self._reward_episode.append(reward)

            # Update server with state and get new sync timing
            if self._communicator:
                # Send current state
                self._communicator.send_state(current_state, self._step, {
                    'queue_length': self._get_queue_length(),
                    'current_phase': traci.trafficlight.getPhase("TL"),
                    'incoming_vehicles': {
                        'N': traci.edge.getLastStepVehicleNumber("N2TL"),
                        'S': traci.edge.getLastStepVehicleNumber("S2TL"),
                        'E': traci.edge.getLastStepVehicleNumber("E2TL"),
                        'W': traci.edge.getLastStepVehicleNumber("W2TL")
                    },
                    'avg_speed': {
                        'N': traci.edge.getLastStepMeanSpeed("N2TL"),
                        'S': traci.edge.getLastStepMeanSpeed("S2TL"),
                        'E': traci.edge.getLastStepMeanSpeed("E2TL"),
                        'W': traci.edge.getLastStepMeanSpeed("W2TL")
                    }
                })

                # Get new sync timing periodically
                if self._step % 60 == 0:  # Check for new sync timing every minute
                    sync_data = self._communicator.get_sync_timing()
                    if sync_data:
                        self._adjust_timing(sync_data)

        # End simulation
        traci.close()
        simulation_time = round(timeit.default_timer() - start_time, 1)

        # Report final results to server
        if self._communicator:
            total_reward = np.sum(self._reward_episode)
            avg_queue_length = np.mean(self._queue_length_episode)
            total_waiting_time = np.sum(self._queue_length_episode)
            
            self._communicator.update_episode_result(
                episode=episode,
                reward=total_reward,
                queue_length=avg_queue_length,
                waiting_time=total_waiting_time
            )
            self._communicator.update_status("test_completed")

        return simulation_time

    def _track_vehicles(self):
        """Track vehicles that enter and exit the simulation"""
        if not traci.isLoaded():
            return

        try:
            # Get current vehicles
            current_vehicles = set(traci.vehicle.getIDList())
            
            # Define boundary detection points (in meters from intersection)
            boundary_distance = 20.0  # 20 meters from intersection
            
            # Check each vehicle's position
            for vehicle_id in current_vehicles:
                try:
                    # Skip if vehicle is already being tracked for exit
                    if vehicle_id in self._exited_vehicles:
                        continue
                    # Get vehicle's current road and position
                    current_road = traci.vehicle.getRoadID(vehicle_id)
                    current_position = traci.vehicle.getLanePosition(vehicle_id)
                    
                    # Check if vehicle is on an exit road and approaching the boundary
                    if current_road in ["TL2N", "TL2S", "TL2E", "TL2W"]:
                        # Check if vehicle is near the boundary point
                        if current_position >= boundary_distance:
                            # Get vehicle details
                            vehicle_type = traci.vehicle.getTypeID(vehicle_id)
                            route = traci.vehicle.getRouteID(vehicle_id)
                            speed = traci.vehicle.getSpeed(vehicle_id)
                            lane = traci.vehicle.getLaneIndex(vehicle_id)
                            position = traci.vehicle.getPosition(vehicle_id)
                            waiting_time = traci.vehicle.getAccumulatedWaitingTime(vehicle_id)
                            
                            # Determine exit direction and destination agent based on road
                            exit_direction = None
                            destination_agent = None
                            
                            if current_road == 'TL2N':
                                exit_direction = 'north'
                                destination_agent = 'agent2'  # Default to agent2 for north
                            elif current_road == 'TL2S':
                                exit_direction = 'south'
                                destination_agent = 'agent3'  # Default to agent3 for south
                            elif current_road == 'TL2E':
                                exit_direction = 'east'
                                destination_agent = 'agent4'  # Default to agent4 for east
                            elif current_road == 'TL2W':
                                exit_direction = 'west'
                                destination_agent = 'agent1'  # Default to agent1 for west

                            # Only proceed if we have both exit direction and destination
                            if exit_direction and destination_agent:
                                # Store vehicle info
                                self._exited_vehicles[vehicle_id] = {
                                    'type': vehicle_type,
                                    'route': route,
                                    'speed': speed,
                                    'lane': lane,
                                    'position': position,
                                    'waiting_time': waiting_time,
                                    'is_boundary_exit': True,
                                    'exit_direction': exit_direction,
                                    'destination': destination_agent,
                                    'timestamp': time.time()
                                }
                                
                                # Send vehicle info to server if connected
                                if self._communicator:
                                    transfer_data = {
                                        'vehicle_id': vehicle_id,
                                        'type': vehicle_type,
                                        'route': route,
                                        'speed': speed,
                                        'lane': lane,
                                        'position': position,
                                        'waiting_time': waiting_time,
                                        'exit_direction': exit_direction,
                                        'from_agent': self._agent_id,
                                        'to_agent': destination_agent,
                                        'timestamp': time.time()
                                    }
                                    
                                    # Send state update with vehicle transfer data
                                    self._communicator.send_state(None, self._step, {
                                        'vehicle_transfer': transfer_data
                                    })
                                    print(f"Sent vehicle {vehicle_id} to agent {destination_agent}")
                            
                except traci.exceptions.TraCIException:
                    # Vehicle is no longer in simulation, skip it
                    continue
                except Exception as e:
                    print(f"Error tracking vehicle {vehicle_id}: {e}")
            
            # Find vehicles that have actually exited
            exited = self._active_vehicles - current_vehicles
            for vehicle_id in exited:
                # Remove from active vehicles
                self._active_vehicles.discard(vehicle_id)
            
            # Update active vehicles
            self._active_vehicles = current_vehicles
            
        except Exception as e:
            print(f"Error in _track_vehicles: {e}")

    def _check_incoming_vehicles(self):
        """Check for and spawn incoming vehicles from other intersections"""
        if not self._communicator:
            return

        try:
            print(f"Checking for incoming vehicles to {self._agent_id}")
            # Get vehicle transfers from the server
            response = requests.get(f"{self._server_url}/api/vehicle_transfers?agent_id={self._agent_id}")
            if response.status_code != 200:
                print(f"Error getting vehicle transfers: {response.text}")
                return

            vehicle_transfers = response.json()
            if not vehicle_transfers:
                return

            print(f"Received {len(vehicle_transfers)} vehicles to spawn")

            for vehicle_data in vehicle_transfers:
                try:
                    # Add to incoming vehicles list with spawn position
                    entry_road = None
                    entry_lane = 0

                    # Determine entry road based on exit direction from previous intersection
                    if vehicle_data.get('exit_direction'):
                        if vehicle_data['exit_direction'] == 'north':
                            entry_road = 'S2TL'
                        elif vehicle_data['exit_direction'] == 'south':
                            entry_road = 'N2TL'
                        elif vehicle_data['exit_direction'] == 'east':
                            entry_road = 'W2TL'
                        elif vehicle_data['exit_direction'] == 'west':
                            entry_road = 'E2TL'

                    if entry_road:
                        # Get the road length
                        try:
                            road_length = traci.edge.getLength(entry_road)
                        except:
                            road_length = 100.0  # Default length if we can't get it

                        # Add spawn information to vehicle data
                        vehicle_data['spawn_road'] = entry_road
                        vehicle_data['spawn_lane'] = entry_lane
                        vehicle_data['road_length'] = road_length

                        # Add to incoming vehicles list
                        self._incoming_vehicles.append(vehicle_data)

                except Exception as e:
                    print(f"Error processing vehicle transfer: {e}")

            # Spawn any incoming vehicles
            while self._incoming_vehicles:
                vehicle_data = self._incoming_vehicles.pop(0)
                try:
                    # Create route for the vehicle
                    route_id = f"route_{vehicle_data['vehicle_id']}"

                    # Determine the route edges based on the original route and entry road
                    route_edges = [vehicle_data['spawn_road']]

                    # Add destination edge based on original route
                    if 'route' in vehicle_data:
                        route_parts = vehicle_data['route'].split('_')
                        if len(route_parts) >= 2:
                            # Map the route parts to actual edge names
                            from_dir = route_parts[0]
                            to_dir = route_parts[1]

                            # Map directions to edge names
                            edge_map = {
                                'N': 'TL2N',
                                'S': 'TL2S',
                                'E': 'TL2E',
                                'W': 'TL2W'
                            }

                            # Add the destination edge if it exists in our map
                            if to_dir in edge_map:
                                route_edges.append(edge_map[to_dir])
                                print(f"Created route {route_id} with edges: {route_edges}")

                    # Add the route (check if it already exists first)
                    try:
                        # Check if route already exists
                        existing_routes = traci.route.getIDList()
                        if route_id not in existing_routes:
                            traci.route.add(route_id, route_edges)
                        else:
                            print(f"Route {route_id} already exists, reusing it")
                    except Exception as route_error:
                        print(f"Error creating route {route_id}: {route_error}")
                        print(f"Route edges: {route_edges}")
                        # Try to create a unique route ID
                        unique_route_id = f"{route_id}_{int(time.time())}"
                        try:
                            traci.route.add(unique_route_id, route_edges)
                            route_id = unique_route_id
                            print(f"Created unique route: {route_id}")
                        except Exception as unique_error:
                            print(f"Failed to create unique route: {unique_error}")
                            # Put the vehicle back in the queue
                            self._incoming_vehicles.insert(0, vehicle_data)
                            continue

                    # Spawn the vehicle using the type from the transfer data
                    traci.vehicle.add(
                        vehID=vehicle_data['vehicle_id'],
                        routeID=route_id,
                        typeID=vehicle_data['type'],  # Use the type from transfer data
                        departLane=str(vehicle_data['spawn_lane']),
                        departSpeed=str(vehicle_data['speed']),
                        departPos="0"
                    )
                    print(f"Spawned transferred vehicle {vehicle_data['vehicle_id']} of type {vehicle_data['type']} on {vehicle_data['spawn_road']} with route {route_id}")

                    try:
                        delete_url = f"{self._server_url}/api/vehicle_transfer/{vehicle_data['vehicle_id']}"
                        print(f"Attempting to delete vehicle transfer at URL: {delete_url}")
                        
                        delete_response = requests.delete(delete_url)
                        print(f"Delete response status code: {delete_response.status_code}")
                        print(f"Delete response content: {delete_response.text}")
                        
                        if delete_response.status_code == 200:
                            print(f"Successfully deleted vehicle transfer for {vehicle_data['vehicle_id']}")
                        else:
                            print(f"Failed to delete vehicle transfer for {vehicle_data['vehicle_id']}: {delete_response.text}")
                            # Try alternative deletion endpoint
                            alt_delete_url = f"{self._server_url}/api/vehicle_transfers/{vehicle_data['vehicle_id']}"
                            print(f"Trying alternative deletion URL: {alt_delete_url}")
                            alt_delete_response = requests.delete(alt_delete_url)
                            if alt_delete_response.status_code == 200:
                                print(f"Successfully deleted vehicle transfer using alternative endpoint")
                            else:
                                print(f"Failed to delete using alternative endpoint: {alt_delete_response.text}")
                    except Exception as e:
                        print(f"Error deleting vehicle transfer: {e}")
                        print(f"Error type: {type(e)}")
                        print(f"Error details: {str(e)}")

                except Exception as e:
                    print(f"Error spawning transferred vehicle: {e}")
                    # Put the vehicle back in the queue if there was an error
                    self._incoming_vehicles.insert(0, vehicle_data)
                    break

        except Exception as e:
            print(f"Error in _check_incoming_vehicles: {e}")

    def cleanup(self):
        """Clean up when done"""
        if self._communicator:
            self._communicator.update_status("test_terminated")
            self._communicator.stop_background_sync()
            self._communicator.sync_with_server()  # Final sync

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-config', type=str, default='server_config_1.ini')
    parser.add_argument('--phase', type=str, help='Phase to use for model loading (e.g., "base", "sync"). If not specified, will use non-phase model.')
    parser.add_argument('-i', '--interactive', action='store_true', help='Run in interactive testing mode with UI')
    parser.add_argument('-n', '--no-route-file', action='store_true', help='Do not generate route file for this intersection')
    parser.add_argument('--disable-spawn-filtering', action='store_true', help='Allow spawning from all directions (ignore connected_to config)')
    args = parser.parse_args()
    
    # Read server configuration first to get agent ID
    server_url, agent_id, mapping_config, env_file_path = read_server_config(args.server_config)
    
    # Configure the test based on mode
    if args.interactive:
        config = import_test_configuration(config_file='testing_settings_interactive.ini')
        print("Running in interactive mode with UI")
    else:
        config = import_test_configuration(config_file='testing_settings.ini')
        print("Running in non-interactive mode")
    
    # Update SUMO config file name based on agent ID and mode
    if agent_id:
        if args.interactive:
            config['sumocfg_file_name'] = f'sumo_config_interactive.sumocfg'
        else:
            config['sumocfg_file_name'] = f'sumo_config.sumocfg'
        print(f"Using SUMO config file: {config['sumocfg_file_name']}")
    
    # Override interactive setting from command line
    config['interactive_testing'] = args.interactive
    
    sumo_cmd = set_sumo(config['gui'], config['sumocfg_file_name'], config['max_steps'], args.server_config)
    
    # Find the latest model for this agent
    models_dir = config['models_path_name']
    latest_model_num, model_path = get_latest_model_for_agent(models_dir, agent_id, args.phase)
    
    if latest_model_num is None:
        print(f"Error: No model found for agent {agent_id}")
        if args.phase:
            print(f"Tried to find base model: trained_model_{args.phase}.h5")
        else:
            print(f"Tried to find sync-aware model: intersection_{agent_id.replace('agent', '')}_model.h5")
        sys.exit(1)
    
    # Update config with the latest model number
    config['model_to_test'] = latest_model_num
    
    # Get plot path
    plot_path = os.path.join(models_dir, f'plots_{latest_model_num}')

    # Print model information
    print("\n=== Model Information ===")
    print(f"Agent ID: {agent_id}")
    print(f"Using model: {latest_model_num}")
    print(f"Model path: {model_path}")
    print(f"Plot path: {plot_path}")
    if args.phase == 'base':
        print("Using base model")
    else:
        print("Using sync-aware model (requires sync_agent)")
    print(f"Testing mode: {'Interactive' if args.interactive else 'Non-interactive'}")
    print("=======================\n")

    if server_url:
        print(f"Connecting to central server at {server_url} as agent {agent_id}")
    else:
        print("Running in standalone mode (no central server)")

    # Create model
    Model = TestModel(
        config['num_states'],
        model_path,
        phase=args.phase
    )

    if args.interactive:
        # Use interactive simulation with UI and random vehicle spawning
        print("[INFO] Running in INTERACTIVE TESTING mode (UI + random vehicle spawning)")
        simulation = InteractiveSimulation(
            Model,
            sumo_cmd,
            config['max_steps'],
            config['green_duration'],
            config['yellow_duration'],
            config['num_states'],
            config['num_actions'],
            server_url,
            agent_id,
            mapping_config,
            env_file_path
        )
        print("----- Testing episode (interactive)")
        simulation_time = simulation.run(config['episode_seed'])
        print("Simulation time:", simulation_time, "s")
        reward_episode = simulation.reward_episode
        print("Average reward:", np.mean(reward_episode))
        print("Total reward:", np.sum(reward_episode))
        queue_length_episode = simulation.queue_length_episode
        print("Average queue length:", np.mean(queue_length_episode))
        print("End of testing")
        simulation.cleanup()
    else:
        # Use the default server testing simulation
        print("Using default server testing simulation")
        # Extract agent number from agent_id (e.g., 'agent1' -> '1')
        agent_num = agent_id.replace('agent', '') if agent_id else '1'
        TrafficGen = TrafficGenerator(
            config['max_steps'], 
            config['n_cars_generated'],
            agent_num,
            no_route_file=args.no_route_file
        )
        simulation = TestingSimulationWithServer(
            Model,
            TrafficGen,
            sumo_cmd,
            config['max_steps'],
            config['green_duration'],
            config['yellow_duration'],
            config['num_states'],
            config['num_actions'],
            server_url,
            agent_id,
            mapping_config,
            env_file_path,
            args.no_route_file,
            args.disable_spawn_filtering
        )
        print("----- Testing episode")
        simulation_time = simulation.run(config['episode_seed'])
        print("Simulation time:", simulation_time, "s")
        reward_episode = simulation.reward_episode
        print("Average reward:", np.mean(reward_episode))
        print("Total reward:", np.sum(reward_episode))
        queue_length_episode = simulation.queue_length_episode
        print("Average queue length:", np.mean(queue_length_episode))
        print("End of testing")
    simulation.cleanup()