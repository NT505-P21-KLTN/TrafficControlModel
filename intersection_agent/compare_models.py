import os
import json
import numpy as np
import matplotlib.pyplot as plt
from training_simulation import Simulation
from utils import import_train_configuration, set_sumo
from generator import TrafficGenerator
from memory import Memory
from model import TrainModel
import datetime
import time
import gc
import psutil
import signal
import sys
from collections import defaultdict

# Global variables for saving state
current_results = {}
current_metrics = defaultdict(list)
current_histories = []
current_model_names = []
comparison_dir = None

def signal_handler(signum, frame):
    """Handle interrupt signals to save results before exit"""
    print("\nReceived interrupt signal. Saving current results...")
    if comparison_dir and current_histories:
        try:
            # Save current results
            comparison_results = {
                name: {
                    'avg_reward': float(np.mean(res['rewards'])),
                    'avg_waiting_time': float(np.mean(res['waiting_times'])),
                    'avg_queue_length': float(np.mean(res['queue_lengths']))
                }
                for name, res in zip(current_model_names, current_results.values())
            }
            
            results_file = os.path.join(comparison_dir, 'model_comparison_results_interrupted.json')
            with open(results_file, 'w') as f:
                json.dump(comparison_results, f, indent=4)
            
            # Save current histories
            for history, model_name in zip(current_histories, current_model_names):
                history_file = os.path.join(comparison_dir, f"training_history_{model_name}_interrupted.json")
                with open(history_file, 'w') as f:
                    json.dump(convert_numpy_types(history), f)
            
            print(f"Results saved to {comparison_dir}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

def create_comparison_dir():
    """Create a directory for comparison results with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_dir = os.path.join(os.getcwd(), 'comparison_results', f'comparison_{timestamp}')
    os.makedirs(comparison_dir, exist_ok=True)
    return comparison_dir

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def cleanup_resources():
    """Clean up resources and force garbage collection"""
    gc.collect()
    plt.close('all')
    # Clear any remaining matplotlib figures
    for i in plt.get_fignums():
        plt.close(i)

def get_system_metrics():
    """Get current system metrics"""
    process = psutil.Process(os.getpid())
    return {
        'memory_mb': process.memory_info().rss / 1024 / 1024,
        'cpu_percent': process.cpu_percent(),
        'timestamp': time.time()
    }

def plot_system_usage(metrics_history, model_names, comparison_dir):
    """Plot system resource usage for each model"""
    plt.figure(figsize=(15, 10))
    
    # Plot memory usage
    plt.subplot(2, 1, 1)
    for model_name, metrics in metrics_history.items():
        timestamps = [m['timestamp'] - metrics[0]['timestamp'] for m in metrics]  # Relative time
        memory_usage = [m['memory_mb'] for m in metrics]
        plt.plot(timestamps, memory_usage, label=model_name)
    plt.title('Memory Usage During Training')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Memory Usage (MB)')
    plt.legend()
    plt.grid(True)
    
    # Plot CPU usage
    plt.subplot(2, 1, 2)
    for model_name, metrics in metrics_history.items():
        timestamps = [m['timestamp'] - metrics[0]['timestamp'] for m in metrics]  # Relative time
        cpu_usage = [m['cpu_percent'] for m in metrics]
        plt.plot(timestamps, cpu_usage, label=model_name)
    plt.title('CPU Usage During Training')
    plt.xlabel('Time (seconds)')
    plt.ylabel('CPU Usage (%)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(comparison_dir, 'system_usage_comparison.png'))
    plt.close()

def train_and_evaluate(config_file, model_name, comparison_dir):
    try:
        start_time = time.time()
        metrics_history = []
        
        # Load configuration
        config = import_train_configuration(config_file)
        print(f"\nStarting training with config file: {config_file}")

        # Initialize required objects
        Model = TrainModel(
            config['num_layers'],
            config['width_layers'],
            config['batch_size'],
            config['learning_rate'],
            config['num_states'],
            config['num_actions']
        )
        MemoryObj = Memory(
            config['memory_size_max'],
            config['memory_size_min']
        )
        TrafficGen = TrafficGenerator(
            config['max_steps'],
            config['n_cars_generated']
        )
        sumo_cmd = set_sumo(
            config['gui'],
            config['sumocfg_file_name'],
            config['max_steps'],
            'server_config_1.ini'
        )

        sim = Simulation(
            Model,
            MemoryObj,
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

        # Simulate training process
        training_history = {
            'loss': [],
            'reward': [],
            'waiting_time': [],
            'queue_length': []
        }
        
        for episode in range(config['total_episodes']):
            print(f"\nEpisode {episode + 1}/{config['total_episodes']} - Using config: {config_file}")
            epsilon = 1.0
            sim_time, train_time, loss = sim.run(episode, epsilon)
            training_history['reward'].append(float(sim.reward_store[-1]))
            training_history['loss'].append(float(loss))
            training_history['waiting_time'].append(float(np.mean(sim.cumulative_wait_store)))
            training_history['queue_length'].append(float(np.mean(sim.avg_queue_length_store)))
            
            # Record system metrics
            metrics_history.append(get_system_metrics())
            
            # Save intermediate results every 10 episodes
            if episode % 10 == 0:
                intermediate_file = os.path.join(comparison_dir, f"training_history_{model_name}_intermediate.json")
                with open(intermediate_file, 'w') as f:
                    json.dump(convert_numpy_types(training_history), f)
                
                metrics_file = os.path.join(comparison_dir, f"system_metrics_{model_name}_intermediate.json")
                with open(metrics_file, 'w') as f:
                    json.dump(convert_numpy_types(metrics_history), f)
            
            # Clean up after each episode
            cleanup_resources()
            
            # Print memory usage every 10 episodes
            if episode % 10 == 0:
                print(f"Memory usage for {model_name} at episode {episode}: {metrics_history[-1]['memory_mb']:.2f} MB")
                print(f"CPU usage for {model_name} at episode {episode}: {metrics_history[-1]['cpu_percent']:.2f}%")

        # Calculate total training time
        training_time = time.time() - start_time
        training_history['training_time'] = training_time

        # Save training history
        history_file = os.path.join(comparison_dir, f"training_history_{model_name}.json")
        with open(history_file, 'w') as f:
            json.dump(convert_numpy_types(training_history), f)

        # Save system metrics
        metrics_file = os.path.join(comparison_dir, f"system_metrics_{model_name}.json")
        with open(metrics_file, 'w') as f:
            json.dump(convert_numpy_types(metrics_history), f)

        evaluation_results = {
            'rewards': [float(x) for x in training_history['reward']],
            'waiting_times': [float(x) for x in training_history['waiting_time']],
            'queue_lengths': [float(x) for x in training_history['queue_length']],
            'training_time': training_time
        }

        Model.save_model(comparison_dir, phase=model_name)

        return training_history, evaluation_results, metrics_history
        
    except Exception as e:
        print(f"Error training model {model_name}: {str(e)}")
        return None, None, None
    finally:
        # Clean up resources
        cleanup_resources()

def moving_average(data, window_size=5):
    if len(data) < window_size:
        return data
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')

def plot_comparison(histories, model_names, comparison_dir, smooth_window=10):
    plt.figure(figsize=(15, 12))
    
    # Plot training loss
    plt.subplot(3, 2, 1)
    for history, name in zip(histories, model_names):
        plt.plot(moving_average(history['loss'], smooth_window), label=name)
    plt.title('Training Loss Comparison')
    plt.xlabel('Episode')
    plt.ylabel('Loss')
    plt.legend()
    
    # Plot reward
    plt.subplot(3, 2, 2)
    for history, name in zip(histories, model_names):
        plt.plot(moving_average(history['reward'], smooth_window), label=name)
    plt.title('Reward Comparison')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.legend()
    
    # Plot waiting time
    plt.subplot(3, 2, 3)
    for history, name in zip(histories, model_names):
        plt.plot(moving_average(history['waiting_time'], smooth_window), label=name)
    plt.title('Waiting Time Comparison')
    plt.xlabel('Episode')
    plt.ylabel('Waiting Time (s)')
    plt.legend()
    
    # Plot queue length
    plt.subplot(3, 2, 4)
    for history, name in zip(histories, model_names):
        plt.plot(moving_average(history['queue_length'], smooth_window), label=name)
    plt.title('Queue Length Comparison')
    plt.xlabel('Episode')
    plt.ylabel('Queue Length')
    plt.legend()
    
    # Plot training time
    plt.subplot(3, 2, 5)
    training_times = [history['training_time'] for history in histories]
    plt.bar(model_names, training_times)
    plt.title('Training Time Comparison')
    plt.xlabel('Model')
    plt.ylabel('Time (seconds)')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(os.path.join(comparison_dir, 'model_comparison.png'))
    plt.close()

def regenerate_results(comparison_dir):
    """Regenerate comparison results from existing training history and system metric files"""
    try:
        print(f"Regenerating results from directory: {comparison_dir}")
        
        # Find all training history files
        history_files = [f for f in os.listdir(comparison_dir) if f.startswith('training_history_') and f.endswith('.json') and '_intermediate' not in f]
        model_names = [f.replace('training_history_', '').replace('.json', '') for f in history_files]
        
        histories = []
        results = []
        system_metrics = defaultdict(list)
        
        for history_file, model_name in zip(history_files, model_names):
            print(f"\nProcessing {model_name}")
            
            # Load training history
            with open(os.path.join(comparison_dir, history_file), 'r') as f:
                history = json.load(f)
            histories.append(history)
            
            # Create results dictionary
            result = {
                'rewards': history.get('reward', []),
                'waiting_times': history.get('waiting_time', []),
                'queue_lengths': history.get('queue_length', []),
                'training_time': history.get('training_time', 0)
            }
            results.append(result)
            
            # Load system metrics if available
            metrics_file = f"system_metrics_{model_name}.json"
            if os.path.exists(os.path.join(comparison_dir, metrics_file)):
                with open(os.path.join(comparison_dir, metrics_file), 'r') as f:
                    metrics = json.load(f)
                system_metrics[model_name] = metrics
        
        if histories and results:
            # Plot comparison
            plot_comparison(histories, model_names, comparison_dir)
            
            # Plot system usage if metrics exist
            if any(system_metrics.values()):
                plot_system_usage(system_metrics, model_names, comparison_dir)
            
            # Save detailed results
            comparison_results = {
                name: {
                    'avg_reward': float(np.mean(res['rewards'])),
                    'avg_waiting_time': float(np.mean(res['waiting_times'])),
                    'avg_queue_length': float(np.mean(res['queue_lengths']))
                }
                for name, res in zip(model_names, results)
            }
            
            results_file = os.path.join(comparison_dir, 'model_comparison_results_regenerated.json')
            with open(results_file, 'w') as f:
                json.dump(comparison_results, f, indent=4)
            
            print(f"\nRegenerated results have been saved to: {comparison_dir}")
            return True
        else:
            print("No training history files found to regenerate results.")
            return False
            
    except Exception as e:
        print(f"Error regenerating results: {str(e)}")
        return False

def main():
    global current_results, current_metrics, current_histories, current_model_names, comparison_dir
    try:
        # Check if we need to regenerate results
        if len(sys.argv) > 1 and sys.argv[1] == '--regenerate':
            # Use the most recent comparison directory
            comparison_dirs = sorted([d for d in os.listdir('comparison_results') if d.startswith('comparison_')])
            if comparison_dirs:
                latest_dir = os.path.join('comparison_results', comparison_dirs[-1])
                print(f"Regenerating results from existing directory: {latest_dir}")
                regenerate_results(latest_dir)
                return
            else:
                print("No comparison directories found to regenerate results.")
                return

        # Create new comparison directory only for new training
        comparison_dir = create_comparison_dir()
        print(f"Created new comparison directory: {comparison_dir}")

        config_files = [
            'training_settings.ini',    # Baseline
            'training_settings_1.ini',  # Conservative
            'training_settings_2.ini',  # Aggressive
            'training_settings_3.ini',  # Balanced
            'training_settings_4.ini',  # High Traffic
            'training_settings_5.ini'   # Low Traffic
        ]
        
        model_names = [
            'baseline',
            'conservative',
            'aggressive',
            'balanced',
            'high_traffic',
            'low_traffic'
        ]
        current_model_names = model_names
        histories = []
        results = []
        system_metrics = defaultdict(list)
        
        for config_file, model_name in zip(config_files, model_names):
            print(f"\nTraining model: {model_name}")
            print(f"Initial memory usage: {get_memory_usage():.2f} MB")
            
            history, result, metrics = train_and_evaluate(config_file, model_name, comparison_dir)
            
            if history is not None and result is not None and metrics is not None:
                histories.append(history)
                current_histories = histories
                results.append(result)
                current_results[model_name] = result
                system_metrics[model_name] = metrics
                current_metrics = system_metrics
                
                print(f"\nResults for {model_name}:")
                print(f"Average reward: {np.mean(result['rewards']):.2f}")
                print(f"Average waiting time: {np.mean(result['waiting_times']):.2f}")
                print(f"Average queue length: {np.mean(result['queue_lengths']):.2f}")
            
            # Clean up after each model
            cleanup_resources()
            print(f"Memory usage after {model_name}: {get_memory_usage():.2f} MB")
        
        if histories and results:
            # Plot comparison
            plot_comparison(histories, model_names, comparison_dir)
            
            # Plot system usage
            plot_system_usage(system_metrics, model_names, comparison_dir)
            
            # Save detailed results
            comparison_results = {
                name: {
                    'avg_reward': float(np.mean(res['rewards'])),
                    'avg_waiting_time': float(np.mean(res['waiting_times'])),
                    'avg_queue_length': float(np.mean(res['queue_lengths']))
                }
                for name, res in zip(model_names, results)
            }
            
            results_file = os.path.join(comparison_dir, 'model_comparison_results.json')
            with open(results_file, 'w') as f:
                json.dump(comparison_results, f, indent=4)

            print(f"\nAll comparison results have been saved to: {comparison_dir}")
        else:
            print("No successful model training results to save.")
            
    except Exception as e:
        print(f"Error in main: {str(e)}")
    finally:
        cleanup_resources()

if __name__ == "__main__":
    main()  