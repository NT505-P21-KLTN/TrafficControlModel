import os
import sys
import json
import argparse
import configparser
from sumolib import checkBinary
import traci
from training_simulation import Simulation
from generator import TrafficGenerator
from memory import Memory
from model import TestModel
from visualization import Visualization
from utils import import_train_configuration, set_sumo, set_train_path

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Multi-Intersection DRL Traffic Control Training')
    parser.add_argument('--config', type=str, default='training_settings.ini',
                        help='Path to training configuration file')
    parser.add_argument('--agent-id', type=str, required=True,
                        help='Unique agent ID for this intersection')
    parser.add_argument('--server-url', type=str, default='http://localhost:5000',
                        help='Central server URL for coordination')
    parser.add_argument('--mapping-config', type=str, required=True,
                        help='Path to mapping configuration JSON file')
    parser.add_argument('--env-file', type=str, required=True,
                        help='Path to SUMO environment configuration file')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Output directory for models and results')
    parser.add_argument('--episodes', type=int, default=None,
                        help='Override number of training episodes')
    parser.add_argument('--gui', action='store_true',
                        help='Enable SUMO GUI')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    return parser.parse_args()

def load_mapping_config(mapping_file):
    """Load mapping configuration from JSON file"""
    try:
        with open(mapping_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading mapping config: {e}")
        return None

def setup_paths(args, config):
    """Setup paths for this agent"""
    if args.output_dir:
        models_path = os.path.join(args.output_dir, f"agent_{args.agent_id}", "models")
    else:
        models_path = os.path.join("models", f"agent_{args.agent_id}")
    
    os.makedirs(models_path, exist_ok=True)
    
    # Set environment variable for this agent
    os.environ['SUMO_HOME'] = '/usr/share/sumo'  # Adjust if needed
    
    return models_path

def main():
    """Main training function for multi-intersection system"""
    args = parse_arguments()
    
    print(f"Starting multi-intersection training for agent {args.agent_id}")
    print(f"Configuration file: {args.config}")
    print(f"Mapping config: {args.mapping_config}")
    print(f"Environment file: {args.env_file}")
    print(f"Server URL: {args.server_url}")
    
    # Load configurations
    config = import_train_configuration(args.config)
    mapping_config = load_mapping_config(args.mapping_config)
    
    if not mapping_config:
        print("Failed to load mapping configuration")
        return
    
    # Override episodes if specified
    if args.episodes:
        config['total_episodes'] = args.episodes
    
    # Setup paths
    models_path = setup_paths(args, config)
    
    # SUMO configuration
    if args.gui:
        config['gui'] = True
    
    sumo_cmd = set_sumo(config['gui'], config['sumocfg_file_name'], config['max_steps'])
    
    # Initialize model path
    path = set_train_path(models_path)
    
    # Create TrafficGenerator
    TrafficGen = TrafficGenerator(
        config['max_steps'], 
        config['n_cars_generated'],
        intersection_id=args.agent_id,
        no_route_file=False,
        disable_external_filtering=False
    )
    
    # Create model and memory
    Model = TestModel(
        config['num_layers'], 
        config['width_layers'], 
        config['batch_size'], 
        config['learning_rate'], 
        input_dim=config['num_states'], 
        output_dim=config['num_actions']
    )
    
    Memory = Memory(
        config['memory_size_max'], 
        config['memory_size_min']
    )
    
    # Initialize visualization
    Visualization = Visualization(
        path, 
        dpi=96
    )
    
    # Create simulation with multi-intersection support
    Simulation = Simulation(
        Model,
        Memory,
        TrafficGen,
        sumo_cmd,
        config['gamma'],
        config['max_steps'],
        config['green_duration'],
        config['yellow_duration'],
        config['num_states'],
        config['num_actions'],
        config['training_epochs'],
        server_url=args.server_url,
        agent_id=args.agent_id,
        mapping_config=mapping_config,
        env_file_path=args.env_file
    )
    
    print(f"\n----- Multi-Intersection Training for Agent {args.agent_id} -----")
    print(f"Total episodes: {config['total_episodes']}")
    print(f"Max steps per episode: {config['max_steps']}")
    print(f"Green duration: {config['green_duration']}s")
    print(f"Yellow duration: {config['yellow_duration']}s")
    print(f"Connected intersections: {mapping_config.get('map', {}).get('connected_to', [])}")
    print("Training with vehicle transfer coordination enabled\n")
    
    # Training loop
    episode = 0
    timestamp_start = Visualization._save_date_and_time()
    
    # Create backup directory
    backup_dir = os.path.join(path, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    while episode < config['total_episodes']:
        print(f'\n----- Episode {episode+1}/{config["total_episodes"]} for Agent {args.agent_id} -----')
        
        # Decrease epsilon exponentially
        epsilon = 1.0 - (episode / config['total_episodes'])
        
        # Run simulation episode
        simulation_time, training_time, avg_loss = Simulation.run(episode, epsilon)
        
        print(f"Simulation time: {simulation_time}s, Training time: {training_time}s")
        if avg_loss > 0:
            print(f"Average training loss: {avg_loss:.6f}")
        
        # Save model periodically (original 20-episode save)
        if episode != 0 and episode % 20 == 0:
            Model.save_model(path, episode)
            print(f"Model saved at episode {episode}")
        
        # Backup model and results every 25 episodes
        if episode != 0 and episode % 25 == 0:
            backup_episode_dir = os.path.join(backup_dir, f'episode_{episode}')
            os.makedirs(backup_episode_dir, exist_ok=True)
            
            # Save model backup
            backup_model_name = f"intersection_{args.agent_id}_model_episode_{episode}.h5"
            Model.save_model(backup_episode_dir, model_name=backup_model_name)
            
            # Save current training results
            current_rewards = Simulation.reward_store.copy()
            current_delays = Simulation.cumulative_wait_store.copy()
            current_queues = Simulation.avg_queue_length_store.copy()
            
            # Save training data backup
            training_backup = {
                'episode': episode,
                'agent_id': args.agent_id,
                'rewards': [float(r) for r in current_rewards],
                'delays': [float(d) for d in current_delays],
                'queue_lengths': [float(q) for q in current_queues],
                'timestamp': Visualization._save_date_and_time(),
                'config': {
                    'total_episodes': config['total_episodes'],
                    'max_steps': config['max_steps'],
                    'green_duration': config['green_duration'],
                    'yellow_duration': config['yellow_duration']
                }
            }
            
            backup_data_file = os.path.join(backup_episode_dir, f'training_data_episode_{episode}.json')
            with open(backup_data_file, 'w') as f:
                json.dump(training_backup, f, indent=2)
            
            # Save plots backup
            backup_plots_dir = os.path.join(backup_episode_dir, 'plots')
            os.makedirs(backup_plots_dir, exist_ok=True)
            
            # Generate backup plots
            import matplotlib.pyplot as plt
            
            # Plot rewards
            plt.figure(figsize=(10, 6))
            plt.plot(current_rewards)
            plt.title(f'Episode Rewards - Agent {args.agent_id} (Episode {episode})')
            plt.xlabel('Episode')
            plt.ylabel('Cumulative Reward')
            plt.grid(True)
            plt.savefig(os.path.join(backup_plots_dir, f'rewards_episode_{episode}.png'), dpi=150, bbox_inches='tight')
            plt.close()
            
            # Plot delays
            plt.figure(figsize=(10, 6))
            plt.plot(current_delays)
            plt.title(f'Cumulative Delays - Agent {args.agent_id} (Episode {episode})')
            plt.xlabel('Episode')
            plt.ylabel('Cumulative Delay (s)')
            plt.grid(True)
            plt.savefig(os.path.join(backup_plots_dir, f'delays_episode_{episode}.png'), dpi=150, bbox_inches='tight')
            plt.close()
            
            # Plot queue lengths
            plt.figure(figsize=(10, 6))
            plt.plot(current_queues)
            plt.title(f'Average Queue Length - Agent {args.agent_id} (Episode {episode})')
            plt.xlabel('Episode')
            plt.ylabel('Queue Length')
            plt.grid(True)
            plt.savefig(os.path.join(backup_plots_dir, f'queues_episode_{episode}.png'), dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✓ Backup created at episode {episode}: {backup_episode_dir}")
            print(f"  - Model: {backup_model_name}")
            print(f"  - Data: training_data_episode_{episode}.json")
            print(f"  - Plots: rewards, delays, queues")
        
        episode += 1
    
    # Final cleanup and save
    print(f"\n----- Training completed for Agent {args.agent_id} -----")
    Model.save_model(path, config['total_episodes'])
    
    # Save training results
    timestamp_end = Visualization._save_date_and_time()
    Visualization.save_data_and_plot(data=Simulation.reward_store, filename=f'reward_{args.agent_id}', 
                                   xlabel='Episode', ylabel='Cumulative negative reward')
    Visualization.save_data_and_plot(data=Simulation.cumulative_wait_store, filename=f'delay_{args.agent_id}', 
                                   xlabel='Episode', ylabel='Cumulative delay (s)')
    Visualization.save_data_and_plot(data=Simulation.avg_queue_length_store, filename=f'queue_{args.agent_id}', 
                                   xlabel='Episode', ylabel='Average queue length')
    
    # Save training metadata
    training_metadata = {
        'agent_id': args.agent_id,
        'total_episodes': config['total_episodes'],
        'max_steps': config['max_steps'],
        'final_reward': Simulation.reward_store[-1] if Simulation.reward_store else 0,
        'final_delay': Simulation.cumulative_wait_store[-1] if Simulation.cumulative_wait_store else 0,
        'final_queue': Simulation.avg_queue_length_store[-1] if Simulation.avg_queue_length_store else 0,
        'connected_agents': mapping_config.get('map', {}).get('connected_to', []),
        'training_start': timestamp_start,
        'training_end': timestamp_end,
        'model_path': path
    }
    
    metadata_file = os.path.join(path, f'training_metadata_{args.agent_id}.json')
    with open(metadata_file, 'w') as f:
        json.dump(training_metadata, f, indent=2)
    
    print(f"Training metadata saved to: {metadata_file}")
    print(f"Model saved to: {path}")
    print(f"Training plots saved for agent {args.agent_id}")
    
    # Cleanup
    Simulation.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        if 'Simulation' in locals():
            Simulation.cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"Error during training: {e}")
        if 'Simulation' in locals():
            Simulation.cleanup()
        sys.exit(1) 