import numpy as np
import math
import os
import xml.etree.ElementTree as ET

class TrafficGenerator:
    def __init__(self, max_steps, n_cars_generated, intersection_id=None, no_route_file=False, disable_external_filtering=False):
        self._n_cars_generated = n_cars_generated  # how many cars per episode
        self._max_steps = max_steps
        self._intersection_id = intersection_id
        self._no_route_file = no_route_file
        self._disable_external_filtering = disable_external_filtering
        
        # Create intersection folder if it doesn't exist
        if intersection_id is not None:
            os.makedirs(f"intersection_{intersection_id}", exist_ok=True)
        
        # Vehicle type distribution (matching the N-S Dominant preset)
        self.vehicle_types = {
            "veh_passenger": 45,
            "veh_bus": 10,
            "veh_truck": 2,
            "veh_emergency": 3,
            "veh_motorcycle": 40
        }

    def _get_valid_routes(self):
        """Read routes from current intersection's config file and add external routes from connected agents"""
        if self._intersection_id is None:
            return []
            
        # Read server config to get connected agents
        server_config = f"server_config_{self._intersection_id}.ini"
        connected_agents = []
        if os.path.exists(server_config):
            with open(server_config, 'r') as f:
                for line in f:
                    if line.startswith('connected_to'):
                        connected_agents = [agent.strip() for agent in line.split('=')[1].split(',')]
                        break

        config_file = f"intersection_{self._intersection_id}/sumo_config.sumocfg"
        if not os.path.exists(config_file):
            print(f"Config file not found: {config_file}")
            return []
            
        try:
            tree = ET.parse(config_file)
            root = tree.getroot()
            
            # Get the route file path from config
            route_file = None
            for input_elem in root.findall('.//input'):
                for child in input_elem:
                    if child.tag == 'route-files':
                        route_file = child.get('value')
                        break
                    
            if not route_file:
                print("No route file specified in config")
                return []
                
            # Read the route file
            route_file_path = f"intersection_{self._intersection_id}/{route_file}"
            if not os.path.exists(route_file_path):
                print(f"Route file not found: {route_file_path}")
                return []
                
            route_tree = ET.parse(route_file_path)
            route_root = route_tree.getroot()
            
            # Get all route definitions
            routes = {}
            for route in route_root.findall('.//route'):
                route_id = route.get('id')
                edges = route.get('edges')
                if route_id and edges:
                    routes[route_id] = edges

            if not routes:
                print(f"No <route> definitions found in {route_file_path}. Please add <route> elements for valid random spawn routes.")
                return []

            # Add external routes based on connected agents
            for agent in connected_agents:
                agent_id, direction = agent.split('_')
                if direction == 'east':
                    routes[f'ext_{agent_id}_E'] = 'E2TL'  # External route from east
                elif direction == 'south':
                    routes[f'ext_{agent_id}_S'] = 'S2TL'  # External route from south
                elif direction == 'west':
                    routes[f'ext_{agent_id}_W'] = 'W2TL'  # External route from west
                elif direction == 'north':
                    routes[f'ext_{agent_id}_N'] = 'N2TL'  # External route from north
                    
            print("\nAvailable Routes:")
            print("---------------")
            print("Local Routes:")
            for route_id, edges in sorted(routes.items()):
                if not route_id.startswith('ext_'):
                    print(f"  - {route_id}: {edges}")
            print("\nExternal Routes (from connected agents):")
            for route_id, edges in sorted(routes.items()):
                if route_id.startswith('ext_'):
                    print(f"  - {route_id}: {edges}")
            print("---------------\n")
                
            return list(routes.keys())
            
        except Exception as e:
            print(f"Error reading config/route files: {e}")
            return []

    def generate_routefile(self, seed):
        """
        Generation of the route of every car for one episode
        """
        if self._intersection_id is None:
            print("No intersection ID provided")
            return  # Skip route file generation if no intersection ID is provided
        print(f"Generating route file for intersection {self._intersection_id}")

        np.random.seed(seed)  # make tests reproducible

        # Read server config to get connected agents and determine excluded directions
        server_config = f"server_config_{self._intersection_id}.ini"
        excluded_directions = set()
        
        # Only filter external connections if not disabled
        if not self._disable_external_filtering and os.path.exists(server_config):
            with open(server_config, 'r') as f:
                for line in f:
                    if line.startswith('connected_to'):
                        connected_agents = [agent.strip() for agent in line.split('=')[1].split(',')]
                        for agent in connected_agents:
                            if '_' in agent:
                                agent_id, direction = agent.split('_')
                                if direction == 'east':
                                    excluded_directions.add('E')
                                elif direction == 'south':
                                    excluded_directions.add('S')
                                elif direction == 'west':
                                    excluded_directions.add('W')
                                elif direction == 'north':
                                    excluded_directions.add('N')
                        break
        
        if self._disable_external_filtering:
            print("External connection filtering DISABLED - using all directions for training comparison")
        else:
            print(f"Excluded directions (have external connections): {list(excluded_directions)}")

        # Get valid routes from config/route file
        valid_routes = self._get_valid_routes()
        # Only use random spawn routes (not external/transfer)
        random_spawn_routes = [r for r in valid_routes if not r.startswith('ext_')]
        print(f"Random spawn routes found from config: {random_spawn_routes}")

        route_file = f"intersection_{self._intersection_id}/episode_routes.rou.xml"
        os.makedirs(os.path.dirname(route_file), exist_ok=True)
        
        # Always write a well-formed XML file
        with open(route_file, "w") as routes:
            print("""<routes>
            <vType accel=\"1.0\" decel=\"4.5\" id=\"veh_passenger\" length=\"5.0\" minGap=\"2.5\" maxSpeed=\"25\" sigma=\"0.5\" guiShape=\"passenger\" width=\"1.8\" height=\"1.5\" />
            <vType accel=\"0.8\" decel=\"3.0\" id=\"veh_bus\" length=\"12.0\" minGap=\"3.0\" maxSpeed=\"20\" sigma=\"0.5\" guiShape=\"bus\" width=\"2.5\" height=\"3.0\" />
            <vType accel=\"0.7\" decel=\"2.5\" id=\"veh_truck\" length=\"10.0\" minGap=\"3.0\" maxSpeed=\"18\" sigma=\"0.5\" guiShape=\"truck\" width=\"2.5\" height=\"3.5\" />
            <vType accel=\"1.2\" decel=\"5.0\" id=\"veh_emergency\" length=\"6.0\" minGap=\"2.0\" maxSpeed=\"30\" sigma=\"0.5\" guiShape=\"emergency\" width=\"2.0\" height=\"2.0\" />
            <vType accel=\"1.5\" decel=\"6.0\" id=\"veh_motorcycle\" length=\"2.0\" minGap=\"1.5\" maxSpeed=\"35\" sigma=\"0.5\" guiShape=\"motorcycle\" width=\"1.0\" height=\"1.5\" />
            """, file=routes)

            # Define all possible random spawn routes
            all_routes = {
                'W_N': 'W2TL TL2N',
                'W_E': 'W2TL TL2E',
                'W_S': 'W2TL TL2S',
                'N_W': 'N2TL TL2W',
                'N_E': 'N2TL TL2E',
                'N_S': 'N2TL TL2S',
                'E_W': 'E2TL TL2W',
                'E_N': 'E2TL TL2N',
                'E_S': 'E2TL TL2S',
                'S_W': 'S2TL TL2W',
                'S_N': 'S2TL TL2N',
                'S_E': 'S2TL TL2E'
            }

            # Filter out routes from excluded directions
            filtered_routes = {}
            for route_id, edges in all_routes.items():
                # Check if route starts from an excluded direction
                start_direction = route_id.split('_')[0]  # Get first letter (W, N, E, S)
                if start_direction not in excluded_directions:
                    filtered_routes[route_id] = edges

            # Always write ALL route definitions (so server can spawn on any route)
            print("            <!-- All possible random spawn routes -->")
            for route_id, edges in all_routes.items():
                print(f'            <route id="{route_id}" edges="{edges}"/>', file=routes)

            # Determine which routes to use for vehicle generation (exclude external connections)
            routes_for_generation = list(filtered_routes.keys())
            print(f"Routes available for random spawn (excluding external connections): {routes_for_generation}")

            if not routes_for_generation:
                print("[WARNING] No routes available for random spawn after filtering external connections.")
            elif not self._no_route_file:
                timings = np.random.weibull(2, self._n_cars_generated)
                timings = np.sort(timings)

                car_gen_steps = []
                min_old = math.floor(timings[1])
                max_old = math.ceil(timings[-1])
                min_new = 0
                max_new = self._max_steps
                for value in timings:
                    car_gen_steps = np.append(car_gen_steps, ((max_new - min_new) / (max_old - min_old)) * (value - max_old) + max_new)

                car_gen_steps = np.rint(car_gen_steps)

                for car_counter, step in enumerate(car_gen_steps):
                    vehicle_type = np.random.choice(
                        list(self.vehicle_types.keys()),
                        p=[v/100 for v in self.vehicle_types.values()]
                    )

                    # Randomly select a route for generation (excluding external connections)
                    route_id = np.random.choice(routes_for_generation)
                    print(f'    <vehicle id="{route_id}_{car_counter}" type="{vehicle_type}" route="{route_id}" depart="{step}" departLane="random" departSpeed="10" />', file=routes)

            print("</routes>", file=routes)

    def generate_empty_routefile(self, seed):
        """
        Generate an empty route file with only vehicle types and routes, but no vehicles
        """
        if self._intersection_id is None:
            print("No intersection ID provided")
            return  # Skip route file generation if no intersection ID is provided
        print(f"Generating empty route file for intersection {self._intersection_id}")
            
        np.random.seed(seed)  # make tests reproducible

        # Get valid routes from network file
        valid_routes = self._get_valid_routes()
        print(f"Valid routes found: {valid_routes}")

        # produce the file for cars generation, one car per line
        route_file = f"intersection_{self._intersection_id}/episode_routes.rou.xml"
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(route_file), exist_ok=True)
        with open(route_file, "w") as routes:
            print("""<routes>
            <vType accel=\"1.0\" decel=\"4.5\" id=\"veh_passenger\" length=\"5.0\" minGap=\"2.5\" maxSpeed=\"25\" sigma=\"0.5\" guiShape=\"passenger\" width=\"1.8\" height=\"1.5\" />
            <vType accel=\"0.8\" decel=\"3.0\" id=\"veh_bus\" length=\"12.0\" minGap=\"3.0\" maxSpeed=\"20\" sigma=\"0.5\" guiShape=\"bus\" width=\"2.5\" height=\"3.0\" />
            <vType accel=\"0.7\" decel=\"2.5\" id=\"veh_truck\" length=\"10.0\" minGap=\"3.0\" maxSpeed=\"18\" sigma=\"0.5\" guiShape=\"truck\" width=\"2.5\" height=\"3.5\" />
            <vType accel=\"1.2\" decel=\"5.0\" id=\"veh_emergency\" length=\"6.0\" minGap=\"2.0\" maxSpeed=\"30\" sigma=\"0.5\" guiShape=\"emergency\" width=\"2.0\" height=\"2.0\" />
            <vType accel=\"1.5\" decel=\"6.0\" id=\"veh_motorcycle\" length=\"2.0\" minGap=\"1.5\" maxSpeed=\"35\" sigma=\"0.5\" guiShape=\"motorcycle\" width=\"1.0\" height=\"1.5\" />
            """, file=routes)

            # Define all possible routes
            all_routes = {
                'W_N': 'W2TL TL2N',
                'W_E': 'W2TL TL2E',
                'W_S': 'W2TL TL2S',
                'N_W': 'N2TL TL2W',
                'N_E': 'N2TL TL2E',
                'N_S': 'N2TL TL2S',
                'E_W': 'E2TL TL2W',
                'E_N': 'E2TL TL2N',
                'E_S': 'E2TL TL2S',
                'S_W': 'S2TL TL2W',
                'S_N': 'S2TL TL2N',
                'S_E': 'S2TL TL2E'
            }

            # Only write route definitions for valid routes
            for route_id in valid_routes:
                if route_id in all_routes:
                    print(f'            <route id=\"{route_id}\" edges=\"{all_routes[route_id]}\"/>', file=routes)

            print("</routes>", file=routes)
