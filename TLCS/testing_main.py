from __future__ import absolute_import
from __future__ import print_function

import os
import asyncio
import websockets
import json
import argparse
import configparser
from shutil import copyfile
from datetime import datetime
import traci
import random

from testing_simulation import Simulation
from generator import TrafficGenerator
from model import TestModel
from visualization import Visualization
from utils import import_test_configuration, set_sumo, set_test_path

class WebSocketClient:
    def __init__(self, uri="ws://localhost:8765", agent_id=0):
        self.uri = uri
        self.websocket = None
        self.agent_id = agent_id
        self.connected = False
        self._lock = asyncio.Lock()  # Thêm lock để đồng bộ hóa việc gửi dữ liệu
        self.simulation = None  # Tham chiếu đến đối tượng Simulation

    def set_simulation(self, simulation):
        """Set reference to simulation object"""
        self.simulation = simulation

    async def connect(self):
        while not self.connected:
            try:
                self.websocket = await websockets.connect(
                    self.uri,
                    ping_interval=60,
                    ping_timeout=30,
                    max_size=None,  # Không giới hạn kích thước message
                    max_queue=32,   # Tăng kích thước queue
                    compression=None # Tắt nén để giảm độ trễ
                )
                # Gửi thông tin agent_id khi kết nối
                await self.websocket.send(json.dumps({"agent_id": self.agent_id}))
                self.connected = True
                print(f"Connected to WebSocket server at {self.uri}")
                
                # Bắt đầu lắng nghe tin nhắn từ server
                asyncio.create_task(self.listen_for_messages())
            except Exception as e:
                print(f"Failed to connect to WebSocket server: {e}")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def listen_for_messages(self):
        """Lắng nghe và xử lý tin nhắn từ server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    # Hiển thị thông tin xe nhận được từ agent khác
                    exit_time = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')
                    print(f"\nReceived vehicle from Agent {data['agent_id']}:")
                    print(f"Time: {exit_time}")
                    print(f"Vehicle ID: {data['vehicle_id']}")
                    print(f"Exit Edge: {data['edge_id']}")
                    print("-" * 50)

                    # Spawn xe mới dựa trên thông tin nhận được
                    if self.simulation:  # Chỉ kiểm tra simulation object
                        try:
                            if self.agent_id == 1 and data['agent_id'] == 2:
                                # Agent 1 spawn xe ở edge E2TL khi nhận thông tin từ agent 2
                                new_vehicle_id = f"from_agent2_{data['vehicle_id']}"
                                # Tạo route từ E2TL đến một edge khác
                                route_id = random.choice(['E_N','E_S','E_W'])
                                # Thêm xe với route đã tạo
                                traci.vehicle.add(new_vehicle_id, route_id, typeID="veh_passenger")
                                # Set màu đỏ cho xe mới
                                traci.vehicle.setColor(new_vehicle_id, (255, 0, 0, 255))  # RGBA: đỏ, không trong suốt
                            elif self.agent_id == 2 and data['agent_id'] == 1:
                                # Agent 2 spawn xe ở edge W2TL khi nhận thông tin từ agent 1
                                new_vehicle_id = f"from_agent1_{data['vehicle_id']}"
                                # Tạo route từ W2TL đến một edge khác
                                route_id = random.choice(['W_E','W_N','W_S'])
                                # Thêm xe với route đã tạo
                                traci.vehicle.add(new_vehicle_id, route_id, typeID="veh_passenger")
                                # Set màu đỏ cho xe mới
                                traci.vehicle.setColor(new_vehicle_id, (255, 0, 0, 255))  # RGBA: đỏ, không trong suốt
                        except Exception as e:
                            print(f"Error spawning vehicle: {e}")

                except json.JSONDecodeError as e:
                    print(f"Invalid JSON received: {e}")
                except Exception as e:
                    print(f"Error processing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            print("Connection to server closed")
            self.connected = False
        except Exception as e:
            print(f"Error in message listener: {e}")
            self.connected = False

    async def send_vehicle_exit(self, vehicle_id, edge_id):
        async with self._lock:  # Sử dụng lock để đảm bảo gửi tuần tự
            if not self.connected or not self.websocket:
                await self.connect()
            
            try:
                data = {
                    "vehicle_id": vehicle_id,
                    "edge_id": edge_id,
                    "agent_id": self.agent_id,
                    "timestamp": asyncio.get_event_loop().time()
                }
                # Gửi dữ liệu và đợi xác nhận
                await self.websocket.send(json.dumps(data))
                # Đợi một khoảng thời gian ngắn để đảm bảo dữ liệu được gửi
                await asyncio.sleep(0.001)
            except websockets.exceptions.ConnectionClosed:
                print("Connection lost. Attempting to reconnect...")
                self.connected = False
                await self.connect()
                # Thử gửi lại dữ liệu sau khi kết nối lại
                await self.send_vehicle_exit(vehicle_id, edge_id)
            except Exception as e:
                print(f"Error sending data: {e}")
                # Không retry nếu có lỗi khác

    async def close(self):
        if self.websocket:
            try:
                await self.websocket.close()
                self.connected = False
                print("Disconnected from WebSocket server")
            except Exception as e:
                print(f"Error while closing connection: {e}")

def get_agent_id_from_settings(config_file):
    """Lấy agent_id từ file cấu hình được chọn"""
    try:
        config = configparser.ConfigParser()
        config.read(config_file)
        if 'agent' in config:
            agent_id = config['agent'].get('agent_id')
            if agent_id:
                return int(agent_id)
    except Exception as e:
        print(f"Error reading {config_file}: {e}")
    return 0  # Giá trị mặc định nếu không đọc được

def get_traci_port_from_settings(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config.getint('agent', 'traci_port')

async def main(config_file='testing_settings.ini'):
    # Lấy agent_id từ file cấu hình được chọn
    agent_id = get_agent_id_from_settings(config_file)
    print(f"Using agent_id from {config_file}: {agent_id}")

    # Đọc traci_port từ file cấu hình
    traci_port = get_traci_port_from_settings(config_file)

    # Sử dụng file cấu hình được chọn cho các cấu hình khác
    config = import_test_configuration(config_file=config_file)
    sumo_cmd = set_sumo(config['gui'], config['sumocfg_file_name'], config['max_steps'])
    model_path, plot_path = set_test_path(config['models_path_name'], config['model_to_test'])

    # Initialize WebSocket client với agent_id từ file cấu hình
    ws_client = WebSocketClient(agent_id=agent_id)
    await ws_client.connect()

    model = TestModel(
        input_dim=config['num_states'],
        model_path=model_path
    )

    traffic_gen = TrafficGenerator(
        config['max_steps'], 
        config['n_cars_generated']
    )

    visualization = Visualization(
        plot_path, 
        dpi=96
    )
        
    simulation = Simulation(
        model,
        traffic_gen,
        sumo_cmd,
        config['max_steps'],
        config['green_duration'],
        config['yellow_duration'],
        config['num_states'],
        config['num_actions'],
        ws_client
    )

    # Set simulation reference in WebSocket client
    ws_client.set_simulation(simulation)

    print(f'\n----- Test episode for agent {agent_id}')
    simulation_time = await simulation.run(config['episode_seed'], traci_port=traci_port)
    print('Simulation time:', simulation_time, 's')

    print("----- Testing info saved at:", plot_path)

    # Lưu file cấu hình đã sử dụng
    copyfile(src=config_file, dst=os.path.join(plot_path, 'testing_settings.ini'))

    visualization.save_data_and_plot(data=simulation.reward_episode, filename='reward', xlabel='Action step', ylabel='Reward')
    visualization.save_data_and_plot_2(data1=simulation.queue_length_episode, data2=simulation._current_vehicle_episode, 
                                     filename='queue', xlabel='Step', ylabel='Queue lenght (vehicles)', y2label='Current Vehicels')

    # Close WebSocket connection
    await ws_client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run traffic signal control simulation')
    parser.add_argument('--test-setting', type=str, default='testing_settings.ini',
                      help='Path to the configuration file (default: testing_settings.ini)')
    args = parser.parse_args()
    
    asyncio.run(main(args.test_setting))
