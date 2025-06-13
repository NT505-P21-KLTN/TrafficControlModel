#!/usr/bin/env python3
"""
Validation script for multi-intersection training with vehicle transfer
This script validates that the enhanced training system works correctly
"""

import os
import sys
import json
import time
import requests
import subprocess
import signal
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingValidator:
    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url
        self.test_results = {}
        self.central_server_process = None
        
    def check_server_status(self) -> bool:
        """Check if the central server is running"""
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_central_server(self) -> bool:
        """Start the central server if it's not running"""
        if self.check_server_status():
            logger.info("Central server is already running")
            return True
        
        logger.info("Starting central server...")
        try:
            # Start central server in background
            self.central_server_process = subprocess.Popen(
                [sys.executable, "app.py"],
                cwd="central_server",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a bit for server to start
            time.sleep(3)
            
            if self.check_server_status():
                logger.info("Central server started successfully")
                return True
            else:
                logger.error("Failed to start central server")
                return False
                
        except Exception as e:
            logger.error(f"Error starting central server: {e}")
            return False
    
    def stop_central_server(self):
        """Stop the central server if we started it"""
        if self.central_server_process:
            logger.info("Stopping central server...")
            self.central_server_process.terminate()
            self.central_server_process.wait()
            self.central_server_process = None
    
    def validate_file_structure(self) -> bool:
        """Validate that all required files exist"""
        logger.info("Validating file structure...")
        
        required_files = [
            "training_simulation.py",
            "training_main_multi.py", 
            "run_multi_training.sh",
            "mapping_config_agent1.json",
            "mapping_config_agent2.json",
            "training_settings.ini",
            "central_server/app.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            self.test_results["file_structure"] = False
            return False
        
        logger.info("All required files found")
        self.test_results["file_structure"] = True
        return True
    
    def validate_mapping_configs(self) -> bool:
        """Validate mapping configuration files"""
        logger.info("Validating mapping configurations...")
        
        try:
            # Load agent1 config
            with open("mapping_config_agent1.json", 'r') as f:
                agent1_config = json.load(f)
            
            # Load agent2 config 
            with open("mapping_config_agent2.json", 'r') as f:
                agent2_config = json.load(f)
            
            # Validate required fields
            required_fields = ["agent_id", "map", "learning"]
            
            for config, name in [(agent1_config, "agent1"), (agent2_config, "agent2")]:
                for field in required_fields:
                    if field not in config:
                        logger.error(f"Missing field '{field}' in {name} config")
                        self.test_results["mapping_configs"] = False
                        return False
                
                # Check vehicle transfer enabled
                if not config["learning"].get("vehicle_transfer_enabled", False):
                    logger.error(f"Vehicle transfer not enabled in {name} config")
                    self.test_results["mapping_configs"] = False
                    return False
            
            # Check connections are bidirectional
            agent1_connections = agent1_config["map"]["connected_to"]
            agent2_connections = agent2_config["map"]["connected_to"]
            
            agent1_to_agent2 = any("agent2" in conn for conn in agent1_connections)
            agent2_to_agent1 = any("agent1" in conn for conn in agent2_connections)
            
            if not (agent1_to_agent2 and agent2_to_agent1):
                logger.error("Mapping configurations don't show bidirectional connections")
                self.test_results["mapping_configs"] = False
                return False
            
            logger.info("Mapping configurations validated successfully")
            self.test_results["mapping_configs"] = True
            return True
            
        except Exception as e:
            logger.error(f"Error validating mapping configs: {e}")
            self.test_results["mapping_configs"] = False
            return False
    
    def test_vehicle_transfer_api(self) -> bool:
        """Test the vehicle transfer API endpoints"""
        logger.info("Testing vehicle transfer API...")
        
        try:
            # Test sending a vehicle transfer
            transfer_data = {
                'vehicle_id': 'test_vehicle_001',
                'type': 'veh_passenger',
                'route': 'N_S',
                'speed': 5.0,
                'lane': 0,
                'position': [100, 200],
                'waiting_time': 10.5,
                'exit_direction': 'south',
                'from_agent': 'agent1',
                'to_agent': 'agent2',
                'timestamp': time.time()
            }
            
            # Send vehicle transfer
            response = requests.post(
                f"{self.server_url}/api/vehicle_transfer",
                json=transfer_data,
                timeout=5
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send vehicle transfer: {response.status_code}")
                self.test_results["vehicle_transfer_api"] = False
                return False
            
            # Retrieve vehicle transfers for agent2
            response = requests.get(
                f"{self.server_url}/api/vehicle_transfers?agent_id=agent2",
                timeout=5
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to retrieve vehicle transfers: {response.status_code}")
                self.test_results["vehicle_transfer_api"] = False
                return False
            
            transfers = response.json()
            if not transfers:
                logger.error("No vehicle transfers retrieved")
                self.test_results["vehicle_transfer_api"] = False
                return False
            
            # Check if our test vehicle is in the transfers
            test_vehicle_found = any(
                transfer.get('vehicle_id') == 'test_vehicle_001' 
                for transfer in transfers
            )
            
            if not test_vehicle_found:
                logger.error("Test vehicle not found in transfers")
                self.test_results["vehicle_transfer_api"] = False
                return False
            
            logger.info("Vehicle transfer API test passed")
            self.test_results["vehicle_transfer_api"] = True
            return True
            
        except Exception as e:
            logger.error(f"Error testing vehicle transfer API: {e}")
            self.test_results["vehicle_transfer_api"] = False
            return False
    
    def test_training_import(self) -> bool:
        """Test that the enhanced training simulation can be imported"""
        logger.info("Testing training simulation import...")
        
        try:
            # Test importing the enhanced training simulation
            from training_simulation import Simulation
            
            # Check if the new methods exist
            required_methods = ['_track_vehicles', '_check_incoming_vehicles']
            
            for method_name in required_methods:
                if not hasattr(Simulation, method_name):
                    logger.error(f"Method {method_name} not found in Simulation class")
                    self.test_results["training_import"] = False
                    return False
            
            logger.info("Training simulation import test passed")
            self.test_results["training_import"] = True
            return True
            
        except Exception as e:
            logger.error(f"Error importing training simulation: {e}")
            self.test_results["training_import"] = False
            return False
    
    def run_short_training_test(self) -> bool:
        """Run a very short training test to validate functionality"""
        logger.info("Running short training test...")
        
        try:
            # Create a minimal test configuration
            test_config = """
[simulation]
gui = False
total_episodes = 2
max_steps = 50
n_cars_generated = 10
green_duration = 10
yellow_duration = 2

[model]
num_layers = 2
width_layers = 32
batch_size = 16
learning_rate = 0.001
training_epochs = 5

[memory]
memory_size_min = 50
memory_size_max = 500

[agent]
num_states = 80
num_actions = 4
gamma = 0.9

[dir]
models_path_name = test_models
sumocfg_file_name = sumo_config.sumocfg
"""
            
            # Write test config
            with open("test_training.ini", "w") as f:
                f.write(test_config)
            
            # Run short training for agent1
            cmd = [
                sys.executable, "training_main_multi.py",
                "--agent-id", "agent1",
                "--server-url", self.server_url,
                "--mapping-config", "mapping_config_agent1.json",
                "--env-file", "sumo_config.sumocfg",
                "--config", "test_training.ini",
                "--episodes", "2",
                "--output-dir", "test_output"
            ]
            
            logger.info("Starting short training test...")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )
            
            # Clean up test files
            if os.path.exists("test_training.ini"):
                os.remove("test_training.ini")
            
            if process.returncode == 0:
                logger.info("Short training test completed successfully")
                self.test_results["short_training"] = True
                return True
            else:
                logger.error(f"Short training test failed: {process.stderr}")
                self.test_results["short_training"] = False
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Short training test timed out")
            self.test_results["short_training"] = False
            return False
        except Exception as e:
            logger.error(f"Error in short training test: {e}")
            self.test_results["short_training"] = False
            return False
    
    def run_validation(self) -> bool:
        """Run all validation tests"""
        logger.info("Starting multi-intersection training validation...")
        
        # Start central server
        if not self.start_central_server():
            return False
        
        try:
            # Run validation tests
            tests = [
                ("File Structure", self.validate_file_structure),
                ("Mapping Configurations", self.validate_mapping_configs),
                ("Vehicle Transfer API", self.test_vehicle_transfer_api),
                ("Training Import", self.test_training_import),
                ("Short Training Test", self.run_short_training_test)
            ]
            
            all_passed = True
            for test_name, test_func in tests:
                logger.info(f"Running {test_name} test...")
                result = test_func()
                if not result:
                    all_passed = False
                    logger.error(f"{test_name} test FAILED")
                else:
                    logger.info(f"{test_name} test PASSED")
            
            return all_passed
            
        finally:
            # Always stop the server
            self.stop_central_server()
    
    def print_summary(self):
        """Print validation summary"""
        logger.info("\n" + "="*50)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*50)
        
        for test_name, result in self.test_results.items():
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name:25}: {status}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        
        logger.info(f"\nTotal tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        
        if passed_tests == total_tests:
            logger.info("\n🎉 ALL TESTS PASSED! Multi-intersection training is ready!")
        else:
            logger.info(f"\n❌ {total_tests - passed_tests} test(s) failed. Please fix the issues above.")

def main():
    """Main validation function"""
    validator = TrainingValidator()
    
    try:
        success = validator.run_validation()
        validator.print_summary()
        
        if success:
            logger.info("\n✅ Validation completed successfully!")
            logger.info("You can now run multi-intersection training with:")
            logger.info("./run_multi_training.sh -e 100")
            return 0
        else:
            logger.error("\n❌ Validation failed! Please fix the issues above.")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\nValidation interrupted by user")
        validator.stop_central_server()
        return 130
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        validator.stop_central_server()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 