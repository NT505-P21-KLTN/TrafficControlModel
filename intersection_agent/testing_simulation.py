import traci
import numpy as np
import random
import timeit
import os
import time
import requests
import xml.etree.ElementTree as ET
from agent_communicator import AgentCommunicatorTesting

# phase codes based on environment.net.xml
PHASE_NS_GREEN = 0  # action 0 code 00
PHASE_NS_YELLOW = 1
PHASE_NSL_GREEN = 2  # action 1 code 01
PHASE_NSL_YELLOW = 3
PHASE_EW_GREEN = 4  # action 2 code 10
PHASE_EW_YELLOW = 5
PHASE_EWL_GREEN = 6  # action 3 code 11
PHASE_EWL_YELLOW = 7


class Simulation:
    def __init__(self, Model, TrafficGen, sumo_cmd, max_steps, green_duration, yellow_duration, num_states, num_actions, server_url=None, agent_id=None, mapping_config=None, env_file_path=None, no_route_file=False):
        self._Model = Model
        self._TrafficGen = TrafficGen
        self._step = 0
        self._sumo_cmd = sumo_cmd
        self._max_steps = max_steps
        self._green_duration = green_duration
        self._yellow_duration = yellow_duration
        self._num_states = num_states
        self._num_actions = num_actions
        self._reward_episode = []
        self._queue_length_episode = []
        self.server_url = server_url
        self._agent_id = agent_id  # Store agent_id
        self._no_route_file = no_route_file
        self._vehicle_counter = 0
        self._active_vehicles = set()
        self._exited_vehicles = {}
        self._incoming_vehicles = []
        
        # Get road lengths from environment file
        if env_file_path is None:
            # Extract agent number from agent_id (e.g., 'agent1' -> '1')
            agent_num = self._agent_id.replace('agent', '') if self._agent_id else '1'
            env_file_path = f"intersection_{agent_num}/environment.net.xml"
        else:
            print(f"Using environment file: {env_file_path}, skipping road length calculation")
            
        self._road_lengths = self._get_road_lengths_from_xml(env_file_path)
        print(f"Using environment file: {env_file_path}")
        print("Road lengths from XML:", self._road_lengths)
        print(f"Agent ID: {self._agent_id}")  # Print agent ID for debugging
        
        # Vehicle spawning parameters
        self.auto_spawn = True
        self.spawn_interval = 4
        self.spawn_interval_random = True
        self.min_interval = 2
        self.max_interval = 6
        self.spawn_count = 5
        self.spawn_count_random = True
        self.min_count = 1
        self.max_count = 8
        self.last_spawn_step = 0
        
        # Vehicle type distribution (matching the N-S Dominant preset)
        self.vehicle_types = {
            "veh_passenger": 70,
            "veh_bus": 10,
            "veh_truck": 10,
            "veh_emergency": 5,
            "veh_motorcycle": 5
        }
        
        # Determine excluded directions from server config
        excluded_directions = set()
        if agent_id:
            server_config = f"server_config_{agent_id.replace('agent', '')}.ini"
            if os.path.exists(server_config):
                with open(server_config, 'r') as f:
                    for line in f:
                        if line.startswith('connected_to'):
                            connected_agents = [agent.strip() for agent in line.split('=')[1].split(',')]
                            for agent in connected_agents:
                                if '_' in agent:
                                    agent_id_part, direction = agent.split('_')
                                    if direction == 'east':
                                        excluded_directions.add('E')
                                    elif direction == 'south':
                                        excluded_directions.add('S')
                                    elif direction == 'west':
                                        excluded_directions.add('W')
                                    elif direction == 'north':
                                        excluded_directions.add('N')
                            break
        
        print(f"Excluded directions for random spawn: {list(excluded_directions)}")
        
        # Route distribution (exclude routes from external connection directions)
        all_routes = {
            "W_N": 15, "W_E": 15, "W_S": 15,
            "N_W": 15, "N_E": 15, "N_S": 15,
            "E_N": 15, "E_S": 15, "E_W": 15,
            "S_N": 15, "S_E": 15, "S_W": 15
        }
        
        # Filter out routes from excluded directions
        self.route_weights = {}
        for route_id, weight in all_routes.items():
            start_direction = route_id.split('_')[0]  # Get first letter (W, N, E, S)
            if start_direction not in excluded_directions:
                self.route_weights[route_id] = weight
        
        print(f"Routes available for random spawn: {list(self.route_weights.keys())}")
        
        # Speed ranges for different vehicle types
        self.speed_ranges = {
            "veh_passenger": (3, 8),
            "veh_bus": (2, 6),
            "veh_truck": (2, 5),
            "veh_emergency": (4, 10),
            "veh_motorcycle": (3, 8)
        }
        
        if server_url:
            self.communicator = AgentCommunicatorTesting(server_url, agent_id, mapping_config, env_file_path)
            self.communicator.update_status("initialized")
            self.communicator.update_config({
                "max_steps": max_steps,
                "green_duration": green_duration,
                "yellow_duration": yellow_duration,
                "num_states": num_states,
                "num_actions": num_actions,
                "mode": "testing"
            })
            self.communicator.start_background_sync()
        else:
            self.communicator = None

    def _get_road_lengths_from_xml(self, env_file_path):
        """Get road lengths from the environment XML file"""
        if not env_file_path:
            return {"W2TL": 750, "N2TL": 750, "E2TL": 750, "S2TL": 750}  # Default lengths
            
        try:
            tree = ET.parse(env_file_path)
            root = tree.getroot()
            
            road_lengths = {}
            for edge in root.findall('.//edge'):
                edge_id = edge.get('id')
                if edge_id in ["W2TL", "N2TL", "E2TL", "S2TL"]:
                    length = float(edge.get('length', '750'))
                    road_lengths[edge_id] = length
                    print(f"Found length for {edge_id}: {length}")
            
            # Ensure all required roads have lengths
            for road_id in ["W2TL", "N2TL", "E2TL", "S2TL"]:
                if road_id not in road_lengths:
                    road_lengths[road_id] = 750
                    print(f"Using default length for {road_id}: 750")
                    
            return road_lengths
            
        except Exception as e:
            print(f"Error reading XML file: {e}")
            return {"W2TL": 750, "N2TL": 750, "E2TL": 750, "S2TL": 750}  # Default lengths

    def run(self, episode):
        start_time = timeit.default_timer()
        if self.communicator:
            sync_data = self.communicator.get_sync_timing()
            if sync_data:
                self._adjust_timing(sync_data)
            self.communicator.update_status("testing")
        self._reward_episode = []
        self._queue_length_episode = []
        
        # Generate route file (empty if -n flag is used)
        self._TrafficGen.generate_routefile(seed=episode)
            
        traci.start(self._sumo_cmd)
        print("Simulating...")
        self._step = 0
        self._waiting_times = {}
        old_total_wait = 0
        old_action = -1
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
            if self.communicator:
                self._check_incoming_vehicles()
            
            current_state = self._get_state()
            current_total_wait = self._collect_waiting_times()
            reward = old_total_wait - current_total_wait
            action = self._choose_action(current_state)
            if self._step != 0 and old_action != action:
                self._set_yellow_phase(old_action)
                self._simulate(self._yellow_duration)
            self._set_green_phase(action)
            self._simulate(self._green_duration)
            old_action = action
            old_total_wait = current_total_wait
            self._reward_episode.append(reward)
            if self.communicator:
                self.communicator.send_state(current_state, self._step, {
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
                # Force immediate sync after each state update
                self.communicator.sync_with_server()
                if self._step % 60 == 0:
                    sync_data = self.communicator.get_sync_timing()
                    if sync_data:
                        self._adjust_timing(sync_data)
        traci.close()
        simulation_time = round(timeit.default_timer() - start_time, 1)
        if self.communicator:
            total_reward = np.sum(self._reward_episode)
            avg_queue_length = np.mean(self._queue_length_episode) if self._queue_length_episode else 0
            total_waiting_time = np.sum(self._queue_length_episode) if self._queue_length_episode else 0
            self.communicator.update_episode_result(
                episode=episode,
                reward=total_reward,
                queue_length=avg_queue_length,
                waiting_time=total_waiting_time
            )
            self.communicator.update_status("test_completed")
            # Force final sync at the end
            self.communicator.sync_with_server()
        return simulation_time

    def _simulate(self, steps_todo):
        if (self._step + steps_todo) >= self._max_steps:
            steps_todo = self._max_steps - self._step
        while steps_todo > 0:
            traci.simulationStep()
            self._step += 1
            steps_todo -= 1
            queue_length = self._get_queue_length()
            self._queue_length_episode.append(queue_length)

    def _collect_waiting_times(self):
        incoming_roads = ["E2TL", "N2TL", "W2TL", "S2TL"]
        car_list = traci.vehicle.getIDList()
        for car_id in car_list:
            wait_time = traci.vehicle.getAccumulatedWaitingTime(car_id)
            road_id = traci.vehicle.getRoadID(car_id)
            if road_id in incoming_roads:
                self._waiting_times[car_id] = wait_time
            else:
                if car_id in self._waiting_times:
                    del self._waiting_times[car_id]
        total_waiting_time = sum(self._waiting_times.values())
        return total_waiting_time

    def _choose_action(self, state):
        predictions = self._Model.predict_one(state)
        print("Model predictions:", predictions)
        action = np.argmax(predictions)
        print("Chosen action:", action)
        return action

    def _set_yellow_phase(self, old_action):
        yellow_phase_code = old_action * 2 + 1
        traci.trafficlight.setPhase("TL", yellow_phase_code)

    def _set_green_phase(self, action_number):
        if action_number == 0:
            traci.trafficlight.setPhase("TL", PHASE_NS_GREEN)
        elif action_number == 1:
            traci.trafficlight.setPhase("TL", PHASE_NSL_GREEN)
        elif action_number == 2:
            traci.trafficlight.setPhase("TL", PHASE_EW_GREEN)
        elif action_number == 3:
            traci.trafficlight.setPhase("TL", PHASE_EWL_GREEN)

    def _get_queue_length(self):
        halt_N = traci.edge.getLastStepHaltingNumber("N2TL")
        halt_S = traci.edge.getLastStepHaltingNumber("S2TL")
        halt_E = traci.edge.getLastStepHaltingNumber("E2TL")
        halt_W = traci.edge.getLastStepHaltingNumber("W2TL")
        queue_length = halt_N + halt_S + halt_E + halt_W
        return queue_length

    def _get_state(self):
        state = np.zeros(self._num_states)
        car_list = traci.vehicle.getIDList()
        print("Number of cars:", len(car_list))
        
        for car_id in car_list:
            lane_pos = traci.vehicle.getLanePosition(car_id)
            lane_id = traci.vehicle.getLaneID(car_id)
            
            # Get the road ID from lane ID (e.g., "W2TL_0" -> "W2TL")
            road_id = lane_id.split('_')[0]
            road_length = self._road_lengths.get(road_id, 750)  # Use lengths from XML
            
            # Calculate relative position (0 to 1)
            relative_pos = 1 - (lane_pos / road_length)
            
            # Convert to cell number (0-9)
            if relative_pos < 0.01:
                lane_cell = 0
            elif relative_pos < 0.02:
                lane_cell = 1
            elif relative_pos < 0.03:
                lane_cell = 2
            elif relative_pos < 0.04:
                lane_cell = 3
            elif relative_pos < 0.05:
                lane_cell = 4
            elif relative_pos < 0.08:
                lane_cell = 5
            elif relative_pos < 0.13:
                lane_cell = 6
            elif relative_pos < 0.21:
                lane_cell = 7
            elif relative_pos < 0.53:
                lane_cell = 8
            else:
                lane_cell = 9
                
            if lane_id == "W2TL_0" or lane_id == "W2TL_1" or lane_id == "W2TL_2":
                lane_group = 0
            elif lane_id == "W2TL_3":
                lane_group = 1
            elif lane_id == "N2TL_0" or lane_id == "N2TL_1" or lane_id == "N2TL_2":
                lane_group = 2
            elif lane_id == "N2TL_3":
                lane_group = 3
            elif lane_id == "E2TL_0" or lane_id == "E2TL_1" or lane_id == "E2TL_2":
                lane_group = 4
            elif lane_id == "E2TL_3":
                lane_group = 5
            elif lane_id == "S2TL_0" or lane_id == "S2TL_1" or lane_id == "S2TL_2":
                lane_group = 6
            elif lane_id == "S2TL_3":
                lane_group = 7
            else:
                lane_group = -1

            if lane_group >= 0 and lane_group <= 7:
                car_position = int(str(lane_group) + str(lane_cell))
                if car_position < self._num_states:
                    state[car_position] = 1
        
        print("State shape:", state.shape)
        print("Number of cars in state:", np.sum(state))
        
        if self.communicator:
            # Create traffic data dictionary
            traffic_data = {
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
            }
            
            try:
                # Convert state to list format
                if isinstance(state, np.ndarray):
                    state_list = state.tolist()
                else:
                    state_list = list(state)  # Convert to list if it's not a numpy array
                
                # Send state to server
                self.communicator.send_state(state_list, self._step, traffic_data)
            except Exception as e:
                print(f"Error in send_state: {e}")
                print(f"State type: {type(state_list)}")
                print(f"State content: {state_list}")
                
        return state

    def _adjust_timing(self, sync_data):
        if not sync_data:
            return
        for target_id, timing in sync_data.items():
            if 'optimal_offset_sec' in timing:
                offset = timing['optimal_offset_sec']
                cycle_time = timing.get('cycle_time_sec', self._green_duration * 2)
                if offset > 0:
                    self._green_duration = min(self._green_duration + offset, cycle_time - self._yellow_duration)
                else:
                    self._green_duration = max(self._green_duration + offset, self._yellow_duration + 5)
                print(f"Adjusted timing for sync with {target_id}: offset={offset}s, cycle={cycle_time}s, green={self._green_duration}s")
                break

    def _spawn_random_vehicle(self):
        """Spawn a random vehicle in the simulation"""
        try:
            # Select vehicle type based on distribution
            vehicle_type = random.choices(
                list(self.vehicle_types.keys()),
                weights=list(self.vehicle_types.values())
            )[0]

            # Select route based on distribution
            route = random.choices(
                list(self.route_weights.keys()),
                weights=list(self.route_weights.values())
            )[0]

            # Get speed range for vehicle type
            min_speed, max_speed = self.speed_ranges[vehicle_type]
            speed = random.uniform(min_speed, max_speed)

            # Create unique vehicle ID using counter and larger random number
            self._vehicle_counter += 1
            random_suffix = random.randint(10000, 99999)
            vehicle_id = f"{vehicle_type}_{route}_{self._vehicle_counter}_{random_suffix}"

            # Add vehicle with proper type and departure time
            traci.vehicle.add(
                vehID=vehicle_id,
                routeID=route,
                typeID=vehicle_type,
                departLane="random",
                departSpeed=str(speed)
            )
            print(f"Spawned random vehicle {vehicle_id} of type {vehicle_type} on route {route}")
        except Exception as e:
            print(f"Error spawning random vehicle: {e}")

    def _check_incoming_vehicles(self):
        """Check for and spawn incoming vehicles from other intersections"""
        if not self.communicator:
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

                    # Add the route
                    traci.route.add(route_id, route_edges)

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

                    # Delete the vehicle transfer from the server after successful spawning
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

    def _track_vehicles(self):
        """Track vehicles that enter and exit the simulation"""
        if not traci.isLoaded():
            return

        try:
            # Get current vehicles
            current_vehicles = set(traci.vehicle.getIDList())
            
            # Define boundary detection points (in meters from intersection)
            boundary_distance = 20.0  # 50 meters from intersection
            
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
                                if self.communicator:
                                    transfer_data = {
                                        'vehicle_id': vehicle_id,
                                        'type': vehicle_type,
                                        'route': route,
                                        'speed': speed,
                                        'lane': lane,
                                        'position': position,
                                        'waiting_time': waiting_time,
                                        'exit_direction': exit_direction,
                                        'from_agent': self.communicator.agent_id,
                                        'to_agent': destination_agent,
                                        'timestamp': time.time()
                                    }
                                    
                                    # Send state update with vehicle transfer data
                                    self.communicator.send_state(None, self._step, {
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

    @property
    def queue_length_episode(self):
        return self._queue_length_episode

    @property
    def reward_episode(self):
        return self._reward_episode

    def cleanup(self):
        if self.communicator:
            self.communicator.update_status("test_terminated")
            self.communicator.stop_background_sync()
            self.communicator.sync_with_server()  # Final sync



