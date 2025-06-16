import asyncio
import websockets
import json
from datetime import datetime

class VehicleExitServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = {}  # Lưu trữ client theo agent_id

    async def register(self, websocket, agent_id):
        self.clients[agent_id] = websocket
        print(f"Agent {agent_id} connected. Total agents: {len(self.clients)}")

    async def unregister(self, agent_id):
        if agent_id in self.clients:
            del self.clients[agent_id]
            print(f"Agent {agent_id} disconnected. Total agents: {len(self.clients)}")

    async def handle_client(self, websocket, path=None):
        try:
            # Đợi thông tin agent_id từ client
            message = await websocket.recv()
            data = json.loads(message)
            agent_id = data.get('agent_id')
            
            if agent_id is None:
                print("Error: No agent_id provided")
                return
                
            await self.register(websocket, agent_id)
            print(f"Waiting for messages from Agent {agent_id}...")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    source_agent = data['agent_id']
                    edge_id = data['edge_id']
                    
                    # Nếu xe từ agent 1 có exit edge TL2E, gửi thông tin đến agent 2
                    if source_agent == 1 and edge_id == 'TL2E' and 2 in self.clients:
                        exit_time = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')
                        print(f"\nVehicle from Agent 1 to Agent 2:")
                        print(f"Time: {exit_time}")
                        print(f"Vehicle ID: {data['vehicle_id']}")
                        print(f"Exit Edge: {edge_id}")
                        print("-" * 50)
                        await self.clients[2].send(json.dumps(data))
                    
                    # Nếu xe từ agent 2 có exit edge TL2W, gửi thông tin đến agent 1
                    elif source_agent == 2 and edge_id == 'TL2W' and 1 in self.clients:
                        exit_time = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')
                        print(f"\nVehicle from Agent 2 to Agent 1:")
                        print(f"Time: {exit_time}")
                        print(f"Vehicle ID: {data['vehicle_id']}")
                        print(f"Exit Edge: {edge_id}")
                        print("-" * 50)
                        await self.clients[1].send(json.dumps(data))
                        
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON received: {e}")
                except Exception as e:
                    print(f"Error processing message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if 'agent_id' in locals():
                await self.unregister(agent_id)

    async def start(self):
        server = await websockets.serve(
            self.handle_client, 
            self.host, 
            self.port,
            ping_interval=60,
            ping_timeout=30
        )
        print(f"WebSocket server started on ws://{self.host}:{self.port}")
        print("Waiting for agents to connect...")
        await server.wait_closed()

if __name__ == "__main__":
    server = VehicleExitServer()
    asyncio.run(server.start()) 