import traci
import numpy as np
import random
import timeit
import os
import time
import requests
from agent_communicator import AgentCommunicatorTraining

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
    def __init__(self, Model, Memory, TrafficGen, sumo_cmd, gamma, max_steps, green_duration, yellow_duration, num_states, num_actions, training_epochs, server_url=None, agent_id=None, mapping_config=None, env_file_path=None):
        self._Model = Model
        self._Memory = Memory
        self._TrafficGen = TrafficGen
        self._gamma = gamma
        self._step = 0
        self._sumo_cmd = sumo_cmd
        self._max_steps = max_steps
        self._green_duration = green_duration
        self._yellow_duration = yellow_duration
        self._num_states = num_states
        self._num_actions = num_actions
        self._reward_store = []
        self._cumulative_wait_store = []
        self._avg_queue_length_store = []
        self._training_epochs = training_epochs
        
        # Multi-intersection vehicle tracking
        self._agent_id = agent_id
        self._mapping_config = mapping_config
        self._active_vehicles = set()  # Track vehicles currently in simulation
        self._exited_vehicles = {}  # Track vehicles that have exited and their destinations
        self._incoming_vehicles = []  # Track vehicles that should be spawned
        self._vehicle_counter = 0
        
        # Add persistent tracking to prevent duplicate vehicle processing across episodes
        self._processed_transfer_ids = set()  # Track vehicles we've already processed
        self._spawn_attempts = {}  # Track spawn attempts per vehicle to prevent infinite retries
        
        # Road connections for vehicle transfers
        self.road_connections = {}
        if mapping_config and 'map' in mapping_config:
            connected_to = mapping_config['map'].get('connected_to', [])
            for connection in connected_to:
                if '_' in connection:
                    parts = connection.split('_')
                    if len(parts) >= 2:
                        direction = parts[1].lower()
                        connected_agent_id = parts[0]
                        
                        # Map directions to roads
                        road_map = {
                            'north': 'TL2N',
                            'south': 'TL2S', 
                            'east': 'TL2E',
                            'west': 'TL2W'
                        }
                        
                        if direction in road_map:
                            self.road_connections[road_map[direction]] = connected_agent_id
        
        print(f"Training agent {agent_id} road connections: {self.road_connections}")
        
        # Initialize server communication if URL is provided
        self.server_url = server_url
        if server_url:
            self.communicator = AgentCommunicatorTraining(server_url, agent_id, mapping_config, env_file_path)
            self.communicator.update_status("initialized")
            self.communicator.update_config({
                "max_steps": max_steps,
                "green_duration": green_duration,
                "yellow_duration": yellow_duration,
                "gamma": gamma,
                "num_states": num_states,
                "num_actions": num_actions
            })
            self.communicator.update_model_info({
                "batch_size": self._Model.batch_size,
                "input_dim": self._Model.input_dim,
                "output_dim": self._Model.output_dim
            })
            self.communicator.start_background_sync()
        else:
            self.communicator = None


    def run(self, episode, epsilon):
        """
        Runs an episode of simulation, then starts a training session
        """
        start_time = timeit.default_timer()

        # Get sync timing data if communicator is available
        if self.communicator:
            sync_data = self.communicator.get_sync_timing()
            if sync_data:
                self._adjust_timing(sync_data)
            self.communicator.update_status("simulating")

        # first, generate the route file for this simulation and set up sumo
        self._TrafficGen.generate_routefile(seed=episode)
        traci.start(self._sumo_cmd)
        
        print("Simulating...")

        # inits
        self._step = 0
        self._waiting_times = {}
        self._sum_neg_reward = 0
        self._sum_queue_length = 0
        self._sum_waiting_time = 0
        old_total_wait = 0
        old_state = -1
        old_action = -1

        while self._step < self._max_steps:
            try:
                # Track vehicles and check for incoming vehicles from other intersections
                if self.communicator:
                    self._track_vehicles()
                    self._check_incoming_vehicles()

                # get current state of the intersection
                current_state = self._get_state()

                # calculate reward of previous action: (change in cumulative waiting time between actions)
                # waiting time = seconds waited by a car since the spawn in the environment, cumulated for every car in incoming lanes
                current_total_wait = self._collect_waiting_times()
                reward = old_total_wait - current_total_wait

                # saving the data into the memory
                if self._step != 0:
                    self._Memory.add_sample((old_state, old_action, reward, current_state))

                # choose the light phase to activate, based on the current state of the intersection
                action = self._choose_action(current_state, epsilon)

                # if the chosen phase is different from the last phase, activate the yellow phase
                if self._step != 0 and old_action != action:
                    self._set_yellow_phase(old_action)
                    self._simulate(self._yellow_duration)

                # execute the phase selected before
                self._set_green_phase(action)
                self._simulate(self._green_duration)

                # saving variables for later & accumulate reward
                old_state = current_state
                old_action = action
                old_total_wait = current_total_wait

                # saving only the meaningful reward to better see if the agent is behaving correctly
                if reward < 0:
                    self._sum_neg_reward += reward
                    
            except Exception as step_error:
                print(f"[TRAINING] Error in simulation step {self._step}: {step_error}")
                print(f"[TRAINING] Continuing to next step to prevent crash...")
                # Continue with next step instead of crashing
                continue

        self._save_episode_stats()
        avg_queue_length = self._sum_queue_length / self._max_steps
        
        print("Total reward:", self._sum_neg_reward, "- Epsilon:", round(epsilon, 2))
        traci.close()
        simulation_time = round(timeit.default_timer() - start_time, 1)

        # Report to server if enabled
        if self.communicator:
            self.communicator.update_status("training")
            self.communicator.update_episode_result(
                episode, 
                self._sum_neg_reward,
                avg_queue_length,
                self._sum_waiting_time
            )

        print("Training...")
        start_time = timeit.default_timer()
        losses = []
        for _ in range(self._training_epochs):
            loss = self._replay()
            if loss is not None:
                losses.append(loss)
        training_time = round(timeit.default_timer() - start_time, 1)
        avg_loss = float(np.mean(losses)) if losses else 0.0
        if self.communicator:
            self.communicator.update_status("idle")
        return simulation_time, training_time, avg_loss


    def _simulate(self, steps_todo):
        """
        Execute steps in sumo while gathering statistics
        """
        if (self._step + steps_todo) >= self._max_steps:  # do not do more steps than the maximum allowed number of steps
            steps_todo = self._max_steps - self._step

        while steps_todo > 0:
            traci.simulationStep()  # simulate 1 step in sumo
            self._step += 1 # update the step counter
            steps_todo -= 1
            queue_length = self._get_queue_length()
            self._sum_queue_length += queue_length
            self._sum_waiting_time += queue_length # 1 step while wating in queue means 1 second waited, for each car, therefore queue_lenght == waited_seconds

  
    def _collect_waiting_times(self):
        """
        Retrieve the waiting time of every car in the incoming roads
        """
        incoming_roads = ["E2TL", "N2TL", "W2TL", "S2TL"]
        car_list = traci.vehicle.getIDList()
        for car_id in car_list:
            wait_time = traci.vehicle.getAccumulatedWaitingTime(car_id)
            road_id = traci.vehicle.getRoadID(car_id)  # get the road id where the car is located
            if road_id in incoming_roads:  # consider only the waiting times of cars in incoming roads
                self._waiting_times[car_id] = wait_time
            else:
                if car_id in self._waiting_times: # a car that was tracked has cleared the intersection
                    del self._waiting_times[car_id] 
        total_waiting_time = sum(self._waiting_times.values())
        return total_waiting_time


    def _choose_action(self, state, epsilon):
        """
        Decide wheter to perform an explorative or exploitative action, according to an epsilon-greedy policy
        """
        if random.random() < epsilon:
            return random.randint(0, self._num_actions - 1) # random action
        else:
            return np.argmax(self._Model.predict_one(state)) # the best action given the current state


    def _set_yellow_phase(self, old_action):
        """
        Activate the correct yellow light combination in sumo
        """
        yellow_phase_code = old_action * 2 + 1 # obtain the yellow phase code, based on the old action (ref on environment.net.xml)
        traci.trafficlight.setPhase("TL", yellow_phase_code)


    def _set_green_phase(self, action_number):
        """
        Activate the correct green light combination in sumo
        """
        if action_number == 0:
            traci.trafficlight.setPhase("TL", PHASE_NS_GREEN)
        elif action_number == 1:
            traci.trafficlight.setPhase("TL", PHASE_NSL_GREEN)
        elif action_number == 2:
            traci.trafficlight.setPhase("TL", PHASE_EW_GREEN)
        elif action_number == 3:
            traci.trafficlight.setPhase("TL", PHASE_EWL_GREEN)


    def _get_queue_length(self):
        """
        Retrieve the number of cars with speed = 0 in every incoming lane
        """
        halt_N = traci.edge.getLastStepHaltingNumber("N2TL")
        halt_S = traci.edge.getLastStepHaltingNumber("S2TL")
        halt_E = traci.edge.getLastStepHaltingNumber("E2TL")
        halt_W = traci.edge.getLastStepHaltingNumber("W2TL")
        queue_length = halt_N + halt_S + halt_E + halt_W
        return queue_length


    def _get_state(self):
        """
        Retrieve the state of the intersection from sumo, in the form of cell occupancy
        """
        state = np.zeros(self._num_states)
        car_list = traci.vehicle.getIDList()

        # Additional traffic data for inter-intersection coordination
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
            },
            'waiting_time': sum(self._waiting_times.values()) if hasattr(self, '_waiting_times') else 0
        }

        for car_id in car_list:
            lane_pos = traci.vehicle.getLanePosition(car_id)
            lane_id = traci.vehicle.getLaneID(car_id)
            lane_pos = 750 - lane_pos  # inversion of lane pos, so if the car is close to the traffic light -> lane_pos = 0 --- 750 = max len of a road

            # distance in meters from the traffic light -> mapping into cells
            if lane_pos < 7:
                lane_cell = 0
            elif lane_pos < 14:
                lane_cell = 1
            elif lane_pos < 21:
                lane_cell = 2
            elif lane_pos < 28:
                lane_cell = 3
            elif lane_pos < 40:
                lane_cell = 4
            elif lane_pos < 60:
                lane_cell = 5
            elif lane_pos < 100:
                lane_cell = 6
            elif lane_pos < 160:
                lane_cell = 7
            elif lane_pos < 400:
                lane_cell = 8
            elif lane_pos <= 750:
                lane_cell = 9

            # finding the lane where the car is located 
            # x2TL_3 are the "turn left only" lanes
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

            if lane_group >= 1 and lane_group <= 7:
                car_position = int(str(lane_group) + str(lane_cell))  # composition of the two postion ID to create a number in interval 0-79
                valid_car = True
            elif lane_group == 0:
                car_position = lane_cell
                valid_car = True
            else:
                valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it

            if valid_car:
                state[car_position] = 1  # write the position of the car car_id in the state array in the form of "cell occupied"

        if self.communicator:
            self.communicator.send_state(state.tolist(), self._step, traffic_data)
            
        return state


    def _replay(self):
        """
        Retrieve a group of samples from the memory and for each of them update the learning equation, then train
        """
        batch = self._Memory.get_samples(self._Model.batch_size)
        if len(batch) > 0:  # if the memory is full enough
            states = np.array([val[0] for val in batch])  # extract states from the batch
            next_states = np.array([val[3] for val in batch])  # extract next states from the batch
            q_s_a = self._Model.predict_batch(states)  # predict Q(state), for every sample
            q_s_a_d = self._Model.predict_batch(next_states)  # predict Q(next_state), for every sample
            x = np.zeros((len(batch), self._num_states))
            y = np.zeros((len(batch), self._num_actions))
            for i, b in enumerate(batch):
                state, action, reward, _ = b[0], b[1], b[2], b[3]
                current_q = q_s_a[i]
                current_q[action] = reward + self._gamma * np.amax(q_s_a_d[i])
                x[i] = state
                y[i] = current_q
            loss = self._Model.train_batch(x, y)
            return loss
        return None


    def _save_episode_stats(self):
        """
        Save the stats of the episode to plot the graphs at the end of the session
        """
        self._reward_store.append(self._sum_neg_reward)  # how much negative reward in this episode
        self._cumulative_wait_store.append(self._sum_waiting_time)  # total number of seconds waited by cars in this episode
        self._avg_queue_length_store.append(self._sum_queue_length / self._max_steps)  # average number of queued cars per step, in this episode

        # Update model metrics for plotting
        self._Model.update_metrics(
            reward=self._sum_neg_reward,
            delay=self._sum_waiting_time,
            queue=self._sum_queue_length / self._max_steps
        )


    @property
    def reward_store(self):
        return self._reward_store


    @property
    def cumulative_wait_store(self):
        return self._cumulative_wait_store


    @property
    def avg_queue_length_store(self):
        return self._avg_queue_length_store


    def cleanup(self):
        """Clean up when done"""
        if self.communicator:
            self.communicator.update_status("terminated")
            self.communicator.stop_background_sync()
            self.communicator.sync_with_server()  # Final sync


    def _adjust_timing(self, sync_data):
        """
        Adjust timing based on sync data from the server
        
        Args:
            sync_data: Dictionary containing sync timing data for this intersection
        """
        if not sync_data:
            return
            
        # Get the optimal offset for each connected intersection
        for target_id, timing in sync_data.items():
            if 'optimal_offset_sec' in timing:
                offset = timing['optimal_offset_sec']
                cycle_time = timing.get('cycle_time_sec', self._green_duration * 2)
                
                # Adjust green duration based on sync timing
                # This is a simple adjustment - you might want to make this more sophisticated
                if offset > 0:
                    # Extend green duration to accommodate offset
                    self._green_duration = min(self._green_duration + offset, cycle_time - self._yellow_duration)
                else:
                    # Reduce green duration to accommodate offset
                    self._green_duration = max(self._green_duration + offset, self._yellow_duration + 5)
                
                print(f"Adjusted timing for sync with {target_id}: offset={offset}s, cycle={cycle_time}s, green={self._green_duration}s")
                break  # For now, just use the first sync timing we find


    def _track_vehicles(self):
        """Track vehicles that enter and exit the simulation for multi-intersection coordination"""
        if not traci.isLoaded():
            return

        try:
            # Get current vehicles WITH ERROR HANDLING
            try:
                current_vehicles = set(traci.vehicle.getIDList())
            except traci.exceptions.TraCIException as e:
                print(f"[TRAINING] TraCI error getting vehicle list: {e}")
                return
            except Exception as e:
                print(f"[TRAINING] Error getting vehicle list: {e}")
                return
            
            # Define boundary detection points (in meters from intersection)
            boundary_distance = 20.0  # 20 meters from intersection
            
            # Check each vehicle's position for potential transfers
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
                                destination_agent = self.road_connections.get('TL2N')
                            elif current_road == 'TL2S':
                                exit_direction = 'south'
                                destination_agent = self.road_connections.get('TL2S')
                            elif current_road == 'TL2E':
                                exit_direction = 'east'
                                destination_agent = self.road_connections.get('TL2E')
                            elif current_road == 'TL2W':
                                exit_direction = 'west'
                                destination_agent = self.road_connections.get('TL2W')
                                
                            # Only transfer vehicle if there's a destination agent
                            if destination_agent and self.communicator:
                                # Mark vehicle as exited to prevent duplicate processing
                                self._exited_vehicles[vehicle_id] = {
                                    'destination': destination_agent,
                                    'exit_direction': exit_direction,
                                    'timestamp': time.time()
                                }
                                
                                # Prepare transfer data
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
                                
                                # Send vehicle transfer data via traffic data in state update
                                traffic_data_with_transfer = {
                                    'vehicle_transfer': transfer_data,
                                    'queue_length': self._get_queue_length(),
                                    'current_phase': traci.trafficlight.getPhase("TL"),
                                    'training_mode': True
                                }
                                
                                # Get current state for better sync agent coordination
                                current_state = self._get_state()
                                
                                self.communicator.send_state(current_state.tolist(), self._step, traffic_data_with_transfer)
                                print(f"[TRAINING] Sent vehicle {vehicle_id} to agent {destination_agent} via {exit_direction} (with state data)")
                                
                except traci.exceptions.TraCIException:
                    # Vehicle is no longer in simulation, skip it
                    continue
                except Exception as e:
                    print(f"Error tracking vehicle {vehicle_id}: {e}")
            
            # Find vehicles that have actually exited
            exited = self._active_vehicles - current_vehicles
            for vehicle_id in exited:
                # Remove from active vehicles and exited tracking
                self._active_vehicles.discard(vehicle_id)
                if vehicle_id in self._exited_vehicles:
                    del self._exited_vehicles[vehicle_id]
            
            # Update active vehicles
            self._active_vehicles = current_vehicles
            
        except Exception as e:
            print(f"Error in _track_vehicles: {e}")

    def _check_incoming_vehicles(self):
        """Check for and spawn incoming vehicles from other intersections during training"""
        if not traci.isLoaded():
            return
        if not self.server_url:
            return

        try:
            # Periodic cleanup of old tracking data to prevent memory buildup
            if self._step % 1000 == 0:  # Every 1000 steps
                print(f"[TRAINING] Periodic cleanup: {len(self._processed_transfer_ids)} processed vehicles, {len(self._spawn_attempts)} spawn attempts tracked")
                # Keep only recent failed attempts, clear very old processed IDs
                if len(self._processed_transfer_ids) > 10000:
                    # Keep only the most recent 5000 processed IDs
                    recent_ids = list(self._processed_transfer_ids)[-5000:]
                    self._processed_transfer_ids = set(recent_ids)
                    print(f"[TRAINING] Cleaned up old processed IDs, now tracking {len(self._processed_transfer_ids)}")
                
                # Clear old spawn attempts (keep only those from last few minutes)
                current_time = time.time()
                if hasattr(self, '_last_cleanup_time'):
                    if current_time - self._last_cleanup_time > 300:  # 5 minutes
                        self._spawn_attempts.clear()
                        self._last_cleanup_time = current_time
                else:
                    self._last_cleanup_time = current_time

            # Get vehicle transfers from the server WITH ENHANCED ERROR HANDLING
            try:
                response = requests.get(f"{self.server_url}/api/vehicle_transfers?agent_id={self._agent_id}", timeout=5)
                if response.status_code != 200:
                    print(f"[TRAINING] Server returned status {response.status_code}, skipping vehicle transfers")
                    return
                    
                vehicle_transfers = response.json()
                if not vehicle_transfers:
                    return
                    
            except requests.exceptions.Timeout:
                print(f"[TRAINING] Server request timeout, skipping vehicle transfers this step")
                return
            except requests.exceptions.ConnectionError:
                print(f"[TRAINING] Server connection error, skipping vehicle transfers this step")
                return
            except requests.exceptions.RequestException as e:
                print(f"[TRAINING] Server request failed: {e}, skipping vehicle transfers this step")
                return
            except Exception as e:
                print(f"[TRAINING] Unexpected error getting transfers: {e}, skipping vehicle transfers this step")
                return
                
            print(f"[TRAINING] Received {len(vehicle_transfers)} vehicles to spawn in episode")
            
            # Track which vehicles we've already processed to avoid duplicates
            processed_vehicles = set()
            
            for vehicle_data in vehicle_transfers:
                try:
                    vehicle_id = vehicle_data.get('vehicle_id')
                    if not vehicle_id:
                        continue
                        
                    # Skip if we've already processed this vehicle in any episode
                    if vehicle_id in self._processed_transfer_ids:
                        print(f"[TRAINING] Vehicle {vehicle_id} already processed in previous episode, skipping")
                        # Safe delete with error handling
                        try:
                            requests.delete(f"{self.server_url}/api/vehicle_transfer/{vehicle_id}", timeout=2)
                        except:
                            pass  # Ignore delete errors to prevent crash
                        continue
                        
                    # Skip if we've already processed this vehicle in this batch
                    if vehicle_id in processed_vehicles:
                        continue
                        
                    # Track spawn attempts to prevent infinite retries
                    if vehicle_id in self._spawn_attempts and self._spawn_attempts[vehicle_id] >= 3:
                        print(f"[TRAINING] Vehicle {vehicle_id} has failed spawn attempts 3 times, removing from queue")
                        try:
                            requests.delete(f"{self.server_url}/api/vehicle_transfer/{vehicle_id}", timeout=2)
                        except:
                            pass  # Ignore delete errors
                        self._processed_transfer_ids.add(vehicle_id)
                        continue
                        
                    # Check if vehicle already exists in simulation WITH ERROR HANDLING
                    try:
                        current_vehicles = set(traci.vehicle.getIDList())
                        if vehicle_id in current_vehicles:
                            print(f"[TRAINING] Vehicle {vehicle_id} already exists, skipping spawn")
                            # Delete this transfer since vehicle is already spawned
                            try:
                                requests.delete(f"{self.server_url}/api/vehicle_transfer/{vehicle_id}", timeout=2)
                            except:
                                pass  # Ignore delete errors
                            processed_vehicles.add(vehicle_id)
                            self._processed_transfer_ids.add(vehicle_id)
                            continue
                    except traci.exceptions.TraCIException as e:
                        print(f"[TRAINING] TraCI error checking vehicles: {e}")
                        continue  # Skip this vehicle to prevent crash
                    except Exception as e:
                        print(f"[TRAINING] Error checking existing vehicles: {e}")
                        continue  # Continue to prevent crash
                    
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
                        # Get the road length WITH ERROR HANDLING
                        try:
                            road_length = traci.edge.getLength(entry_road)
                        except traci.exceptions.TraCIException:
                            road_length = 100.0  # Default length if we can't get it
                        except Exception:
                            road_length = 100.0  # Default length for any other error
                            
                        # Add spawn information to vehicle data
                        vehicle_data['spawn_road'] = entry_road
                        vehicle_data['spawn_lane'] = entry_lane
                        vehicle_data['road_length'] = road_length
                        
                        # Add to incoming vehicles list
                        self._incoming_vehicles.append(vehicle_data)
                        processed_vehicles.add(vehicle_id)
                        
                except Exception as e:
                    print(f"[TRAINING] Error processing vehicle transfer: {e}")
                    # Continue processing other vehicles instead of crashing

            # Spawn any incoming vehicles WITH ENHANCED ERROR HANDLING
            spawned_count = 0
            max_spawn_per_step = 5  # Limit spawning to prevent overload
            
            while self._incoming_vehicles and spawned_count < max_spawn_per_step:
                vehicle_data = self._incoming_vehicles.pop(0)
                try:
                    original_vehicle_id = vehicle_data['vehicle_id']
                    
                    # Generate a unique vehicle ID to prevent conflicts across intersections
                    unique_vehicle_id = f"{self._agent_id}_{original_vehicle_id}_{self._step}_{int(time.time() * 1000000) % 1000000}"
                    
                    # Double-check vehicle doesn't exist before spawning WITH ERROR HANDLING
                    try:
                        current_vehicles = set(traci.vehicle.getIDList())
                        if original_vehicle_id in current_vehicles or unique_vehicle_id in current_vehicles:
                            print(f"[TRAINING] Vehicle {original_vehicle_id} already exists, skipping spawn")
                            # Delete this transfer since vehicle is already spawned
                            try:
                                requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                            except:
                                pass  # Ignore delete errors
                            processed_vehicles.add(original_vehicle_id)
                            self._processed_transfer_ids.add(original_vehicle_id)
                            continue
                    except Exception as check_error:
                        print(f"[TRAINING] Warning: Could not check existing vehicles: {check_error}")
                        # Continue with spawning but be more careful
                    
                    # Create route for the vehicle WITH ERROR HANDLING
                    route_id = f"training_route_{unique_vehicle_id}"
                    
                    # Determine the route edges based on the original route and entry road
                    route_edges = [vehicle_data['spawn_road']]
                    
                    # Add destination edge based on original route
                    if 'route' in vehicle_data:
                        route_parts = vehicle_data['route'].split('_')
                        if len(route_parts) >= 2:
                            # Map the route parts to actual edge names
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
                                print(f"[TRAINING] Created route {route_id} with edges: {route_edges}")
                    
                    # Add the route WITH COMPREHENSIVE ERROR HANDLING
                    try:
                        existing_routes = traci.route.getIDList()
                        if route_id not in existing_routes:
                            traci.route.add(route_id, route_edges)
                        else:
                            # Create even more unique route ID
                            route_id = f"training_route_fallback_{self._vehicle_counter}_{int(time.time() * 1000000)}"
                            traci.route.add(route_id, route_edges)
                            self._vehicle_counter += 1
                    except traci.exceptions.TraCIException as route_error:
                        print(f"[TRAINING] TraCI error creating route {route_id}: {route_error}")
                        # Try to create a completely unique route ID
                        try:
                            route_id = f"emergency_route_{self._agent_id}_{self._vehicle_counter}_{int(time.time() * 1000000)}"
                            traci.route.add(route_id, route_edges)
                            self._vehicle_counter += 1
                        except Exception as unique_error:
                            print(f"[TRAINING] Failed to create any training route: {unique_error}")
                            # Delete the transfer and continue instead of crashing
                            try:
                                requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                            except:
                                pass
                            continue
                    except Exception as route_error:
                        print(f"[TRAINING] Unexpected error creating route: {route_error}")
                        try:
                            requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                        except:
                            pass
                        continue

                    # Attempt to spawn the vehicle with enhanced error handling
                    try:
                        traci.vehicle.add(
                            vehID=unique_vehicle_id,
                            routeID=route_id,
                            typeID=vehicle_data['type'],
                            departLane=str(vehicle_data['spawn_lane']),
                            departSpeed=str(vehicle_data['speed']),
                            departPos="0"
                        )
                        print(f"[TRAINING] Spawned transferred vehicle {unique_vehicle_id} (original: {original_vehicle_id}) of type {vehicle_data['type']} on {vehicle_data['spawn_road']}")
                        
                        # Mark as successfully processed
                        self._processed_transfer_ids.add(original_vehicle_id)
                        
                        # Delete the transfer from server after successful spawn
                        try:
                            requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                            print(f"[TRAINING] Deleted transfer record for {original_vehicle_id}")
                        except Exception as delete_error:
                            print(f"[TRAINING] Warning: Could not delete transfer record for {original_vehicle_id}: {delete_error}")
                        
                        spawned_count += 1
                        
                    except traci.exceptions.TraCIException as traci_error:
                        # Track the spawn attempt
                        self._spawn_attempts[original_vehicle_id] = self._spawn_attempts.get(original_vehicle_id, 0) + 1
                        
                        error_msg = str(traci_error)
                        if "exists" in error_msg.lower():
                            print(f"[TRAINING] Vehicle ID conflict detected for {unique_vehicle_id}: {traci_error}")
                            # Try with an even more unique ID
                            try:
                                emergency_id = f"emergency_{self._agent_id}_{int(time.time() * 1000000)}_{spawned_count}"
                                traci.vehicle.add(
                                    vehID=emergency_id,
                                    routeID=route_id,
                                    typeID=vehicle_data['type'],
                                    departLane=str(vehicle_data['spawn_lane']),
                                    departSpeed=str(vehicle_data['speed']),
                                    departPos="0"
                                )
                                print(f"[TRAINING] Emergency spawn successful with ID {emergency_id}")
                                self._processed_transfer_ids.add(original_vehicle_id)
                                spawned_count += 1
                                
                                # Delete the transfer from server after successful emergency spawn
                                try:
                                    requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                                except:
                                    pass
                                    
                            except Exception as emergency_error:
                                print(f"[TRAINING] Emergency spawn also failed: {emergency_error}")
                                # Skip this vehicle entirely to prevent crash
                                try:
                                    requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)  
                                except:
                                    pass
                        else:
                            print(f"[TRAINING] TraCI spawn error: {traci_error}")
                            # Skip this vehicle to prevent crash
                            try:
                                requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                            except:
                                pass
                                
                    except Exception as spawn_error:
                        print(f"[TRAINING] Unexpected error spawning vehicle: {spawn_error}")
                        # Clean up and continue to prevent crash
                        try:
                            requests.delete(f"{self.server_url}/api/vehicle_transfer/{original_vehicle_id}", timeout=2)
                        except:
                            pass
                
                except Exception as vehicle_error:
                    print(f"[TRAINING] Error processing vehicle for spawning: {vehicle_error}")
                    # Continue with next vehicle to prevent crash
                    continue
                    
        except Exception as e:
            print(f"[TRAINING] Critical error in _check_incoming_vehicles: {e}")
            print(f"[TRAINING] Continuing simulation to prevent crash...")
            # Don't re-raise the exception to prevent crash

