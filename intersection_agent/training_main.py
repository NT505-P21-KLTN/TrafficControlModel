from __future__ import absolute_import
from __future__ import print_function

import matplotlib.pyplot as plt
import os
import sys
import datetime
import numpy as np
import argparse
import json

from training_simulation import Simulation
from generator import TrafficGenerator
from memory import Memory
from model import TrainModel
from utils import import_train_configuration, set_sumo, set_train_path

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare the environment variable 'SUMO_HOME'")

def plot_training_results(simulation, loss_history, path):
    """Plot and save training results"""
    
    # Create plots directory
    plots_dir = os.path.join(path, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Plot rewards
    rewards = simulation.reward_store
    ax1.plot(rewards)
    ax1.set_title('Episode Rewards')
    ax1.set_xlabel('Episode')
    ax1.set_ylabel('Total Reward')
    ax1.grid(True)
    
    # Plot loss
    ax2.plot(loss_history)
    ax2.set_title('Training Loss')
    ax2.set_xlabel('Episode')
    ax2.set_ylabel('Average Loss')
    ax2.grid(True)
    
    # Plot waiting times
    waiting_times = simulation.cumulative_wait_store
    ax3.plot(waiting_times)
    ax3.set_title('Cumulative Waiting Time')
    ax3.set_xlabel('Episode')
    ax3.set_ylabel('Waiting Time (s)')
    ax3.grid(True)
    
    # Plot queue lengths
    queue_lengths = simulation.avg_queue_length_store
    ax4.plot(queue_lengths)
    ax4.set_title('Average Queue Length')
    ax4.set_xlabel('Episode')
    ax4.set_ylabel('Queue Length')
    ax4.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'training_results.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Training plots saved to: {plots_dir}")

def save_training_history(simulation, loss_history, path):
    """Save training history to JSON file"""
    
    history = {
        'rewards': [float(r) for r in simulation.reward_store],
        'loss': [float(l) for l in loss_history],
        'waiting_times': [float(w) for w in simulation.cumulative_wait_store],
        'queue_lengths': [float(q) for q in simulation.avg_queue_length_store]
    }
    
    history_file = os.path.join(path, 'training_history.json')
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"Training history saved to: {history_file}")

def train_base_model(config, continue_from=None):
    """
    Train the base model without server/sync
    
    Args:
        config: training configuration
        continue_from: path to previous model to continue training from (optional)
    """
    print("\n" + "="*50)
    print("STARTING BASE TRAINING")
    print("="*50)
    
    if continue_from:
        print(f"\nAttempting to continue training from: {continue_from}")
    else:
        print("\nStarting training from scratch (no previous model)")
    
    # Set up SUMO
    sumo_cmd = set_sumo(config['gui'], config['sumocfg_file_name'], config['max_steps'], 'server_config_1.ini')
    path = set_train_path(config['models_path_name'])

    # Create model
    Model = TrainModel(
        config['num_layers'], 
        config['width_layers'], 
        config['batch_size'], 
        config['learning_rate'], 
        config['num_states'], 
        config['num_actions']
    )
    
    # Try to load previous model if specified
    if continue_from:
        if os.path.exists(continue_from):
            print(f"Found previous model at: {continue_from}")
            if Model.load_base_model(continue_from):
                print("✓ Successfully loaded previous model")
            else:
                print("✗ Failed to load previous model, starting from scratch")
        else:
            print(f"✗ Previous model not found at: {continue_from}, starting from scratch")
    
    # Create memory and traffic generator
    memory = Memory(
        config['memory_size_max'], 
        config['memory_size_min']
    )

    TrafficGen = TrafficGenerator(
        config['max_steps'], 
        config['n_cars_generated']
    )

    # Create simulation (without server connection)
    simulation = Simulation(
        Model,
        memory,
        TrafficGen,
        sumo_cmd,
        config['gamma'],
        config['max_steps'],
        config['green_duration'],
        config['yellow_duration'],
        config['num_states'],
        config['num_actions'],
        config['training_epochs']
    )
    
    # Training loop
    episode = 0
    timestamp_start = datetime.datetime.now()
    loss_history = []  # Track loss for each episode
    
    # Create backup directory
    backup_dir = os.path.join(path, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    while episode < config['total_episodes']:
        print('\n----- Base Training: Episode', str(episode+1), 'of', str(config['total_episodes']))
        epsilon = 1.0 - (episode / config['total_episodes'])
        simulation_time, training_time, avg_loss = simulation.run(episode, epsilon)
        
        # Store loss for plotting
        loss_history.append(avg_loss)
        
        print('Simulation time:', simulation_time, 's - Training time:', training_time, 's - Avg Loss:', 
              round(avg_loss, 4), '- Total:', round(simulation_time+training_time, 1), 's')
        
        # Backup model and results every 25 episodes
        if episode != 0 and episode % 25 == 0:
            backup_episode_dir = os.path.join(backup_dir, f'episode_{episode}')
            os.makedirs(backup_episode_dir, exist_ok=True)
            
            # Save model backup
            backup_model_name = f"base_model_episode_{episode}.h5"
            Model.save_model(backup_episode_dir, phase='base', model_name=backup_model_name, 
                           intersection_id='1', config_file='training_settings.ini')
            
            # Save current training results
            current_rewards = simulation.reward_store.copy()
            current_delays = simulation.cumulative_wait_store.copy()
            current_queues = simulation.avg_queue_length_store.copy()
            current_losses = loss_history.copy()
            
            # Save training data backup
            training_backup = {
                'episode': episode,
                'rewards': [float(r) for r in current_rewards],
                'delays': [float(d) for d in current_delays],
                'queue_lengths': [float(q) for q in current_queues],
                'losses': [float(l) for l in current_losses],
                'timestamp': datetime.datetime.now().isoformat(),
                'config': {
                    'total_episodes': config['total_episodes'],
                    'max_steps': config['max_steps'],
                    'green_duration': config['green_duration'],
                    'yellow_duration': config['yellow_duration'],
                    'learning_rate': config['learning_rate'],
                    'batch_size': config['batch_size']
                }
            }
            
            backup_data_file = os.path.join(backup_episode_dir, f'training_data_episode_{episode}.json')
            with open(backup_data_file, 'w') as f:
                json.dump(training_backup, f, indent=2)
            
            # Save plots backup
            backup_plots_dir = os.path.join(backup_episode_dir, 'plots')
            os.makedirs(backup_plots_dir, exist_ok=True)
            
            # Generate backup plots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # Plot rewards
            ax1.plot(current_rewards)
            ax1.set_title(f'Episode Rewards (Episode {episode})')
            ax1.set_xlabel('Episode')
            ax1.set_ylabel('Total Reward')
            ax1.grid(True)
            
            # Plot loss
            ax2.plot(current_losses)
            ax2.set_title(f'Training Loss (Episode {episode})')
            ax2.set_xlabel('Episode')
            ax2.set_ylabel('Average Loss')
            ax2.grid(True)
            
            # Plot waiting times
            ax3.plot(current_delays)
            ax3.set_title(f'Cumulative Waiting Time (Episode {episode})')
            ax3.set_xlabel('Episode')
            ax3.set_ylabel('Waiting Time (s)')
            ax3.grid(True)
            
            # Plot queue lengths
            ax4.plot(current_queues)
            ax4.set_title(f'Average Queue Length (Episode {episode})')
            ax4.set_xlabel('Episode')
            ax4.set_ylabel('Queue Length')
            ax4.grid(True)
            
            plt.tight_layout()
            plt.savefig(os.path.join(backup_plots_dir, f'training_results_episode_{episode}.png'), 
                       dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✓ Backup created at episode {episode}: {backup_episode_dir}")
            print(f"  - Model: {backup_model_name}")
            print(f"  - Data: training_data_episode_{episode}.json")
            print(f"  - Plots: comprehensive training results")
        
        episode += 1

    print("\n" + "="*50)
    print("BASE TRAINING FINISHED")
    print("="*50)
    print("Starting time:", timestamp_start)
    print("Ending time:", datetime.datetime.now())
    print("Session info saved at:", path)

    # Save base model
    model_path = os.path.join(path, 'trained_model_base.h5')
    print(f"\nSaving base model to: {model_path}")
    Model.save_model(path, phase='base', intersection_id='1', config_file='training_settings.ini')
    
    # Plot and save training results
    print("\nGenerating training plots...")
    plot_training_results(simulation, loss_history, path)
    save_training_history(simulation, loss_history, path)
    
    # Cleanup
    simulation.cleanup()
    
    return path

def main():
    parser = argparse.ArgumentParser(description='Train base traffic light control model')
    parser.add_argument('--continue-from', type=str, default=None,
                       help='Path to previous model to continue training from (optional)')
    args = parser.parse_args()
    
    # Load training configuration
    config = import_train_configuration(config_file='training_settings.ini')
    
    # Run base training
    train_base_model(config, continue_from=args.continue_from)

if __name__ == "__main__":
    main()