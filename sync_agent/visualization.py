import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SyncAgentVisualizer:
    def __init__(self, log_dir="sync_agent/logs"):
        """Initialize the visualizer with a directory for logs and plots"""
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize data storage
        self.metrics = {
            'waiting_times': [],
            'queue_lengths': [],
            'avg_speeds': [],
            'rewards': [],
            'sync_quality': [],
            'timestamps': []
        }
        
        # Create log file
        self.log_file = os.path.join(log_dir, f"sync_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
    def log_metrics(self, metrics_data):
        """Log metrics data to file and store in memory"""
        timestamp = datetime.now().isoformat()
        
        # Extract metrics
        waiting_time = metrics_data.get('avg_waiting_time', 0)
        queue_length = metrics_data.get('avg_queue_length', 0)
        avg_speed = metrics_data.get('avg_speed', 0)
        reward = metrics_data.get('reward', 0)
        sync_quality = metrics_data.get('sync_quality', 0)
        
        # Store in memory
        self.metrics['waiting_times'].append(waiting_time)
        self.metrics['queue_lengths'].append(queue_length)
        self.metrics['avg_speeds'].append(avg_speed)
        self.metrics['rewards'].append(reward)
        self.metrics['sync_quality'].append(sync_quality)
        self.metrics['timestamps'].append(timestamp)
        
        # Log to file
        log_entry = {
            'timestamp': timestamp,
            'waiting_time': waiting_time,
            'queue_length': queue_length,
            'avg_speed': avg_speed,
            'reward': reward,
            'sync_quality': sync_quality
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
        logger.info(f"Logged metrics: waiting_time={waiting_time:.2f}, queue_length={queue_length:.2f}, "
                   f"avg_speed={avg_speed:.2f}, reward={reward:.2f}, sync_quality={sync_quality:.2f}")
    
    def plot_metrics(self, save=True):
        """Create plots of all metrics"""
        # Create figure with subplots
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('Sync Agent Performance Metrics', fontsize=16)
        
        # Convert timestamps to relative time in minutes
        timestamps = pd.to_datetime(self.metrics['timestamps'])
        relative_time = (timestamps - timestamps[0]).total_seconds() / 60
        
        # Plot waiting times
        axes[0, 0].plot(relative_time, self.metrics['waiting_times'], 'b-', label='Waiting Time')
        axes[0, 0].set_title('Average Waiting Time')
        axes[0, 0].set_xlabel('Time (minutes)')
        axes[0, 0].set_ylabel('Seconds')
        axes[0, 0].grid(True)
        
        # Plot queue lengths
        axes[0, 1].plot(relative_time, self.metrics['queue_lengths'], 'r-', label='Queue Length')
        axes[0, 1].set_title('Average Queue Length')
        axes[0, 1].set_xlabel('Time (minutes)')
        axes[0, 1].set_ylabel('Vehicles')
        axes[0, 1].grid(True)
        
        # Plot average speeds
        axes[1, 0].plot(relative_time, self.metrics['avg_speeds'], 'g-', label='Average Speed')
        axes[1, 0].set_title('Average Vehicle Speed')
        axes[1, 0].set_xlabel('Time (minutes)')
        axes[1, 0].set_ylabel('km/h')
        axes[1, 0].grid(True)
        
        # Plot rewards
        axes[1, 1].plot(relative_time, self.metrics['rewards'], 'y-', label='Reward')
        axes[1, 1].set_title('Global Reward')
        axes[1, 1].set_xlabel('Time (minutes)')
        axes[1, 1].set_ylabel('Reward Value')
        axes[1, 1].grid(True)
        
        # Plot sync quality
        axes[2, 0].plot(relative_time, self.metrics['sync_quality'], 'm-', label='Sync Quality')
        axes[2, 0].set_title('Synchronization Quality')
        axes[2, 0].set_xlabel('Time (minutes)')
        axes[2, 0].set_ylabel('Quality Score')
        axes[2, 0].grid(True)
        
        # Plot correlation between waiting time and sync quality
        axes[2, 1].scatter(self.metrics['waiting_times'], self.metrics['sync_quality'], 
                          alpha=0.5, label='Data Points')
        axes[2, 1].set_title('Waiting Time vs Sync Quality')
        axes[2, 1].set_xlabel('Waiting Time (seconds)')
        axes[2, 1].set_ylabel('Sync Quality')
        axes[2, 1].grid(True)
        
        # Add trend line
        z = np.polyfit(self.metrics['waiting_times'], self.metrics['sync_quality'], 1)
        p = np.poly1d(z)
        axes[2, 1].plot(self.metrics['waiting_times'], 
                       p(self.metrics['waiting_times']), 
                       "r--", label='Trend Line')
        axes[2, 1].legend()
        
        # Adjust layout
        plt.tight_layout()
        
        # Save plot if requested
        if save:
            plot_file = os.path.join(self.log_dir, f"sync_metrics_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(plot_file)
            logger.info(f"Saved plot to {plot_file}")
        
        plt.close()
    
    def generate_summary(self):
        """Generate a summary of the metrics"""
        summary = {
            'total_time_minutes': (pd.to_datetime(self.metrics['timestamps'][-1]) - 
                                 pd.to_datetime(self.metrics['timestamps'][0])).total_seconds() / 60,
            'avg_waiting_time': np.mean(self.metrics['waiting_times']),
            'avg_queue_length': np.mean(self.metrics['queue_lengths']),
            'avg_speed': np.mean(self.metrics['avg_speeds']),
            'avg_reward': np.mean(self.metrics['rewards']),
            'avg_sync_quality': np.mean(self.metrics['sync_quality']),
            'improvement_waiting_time': (self.metrics['waiting_times'][0] - 
                                      self.metrics['waiting_times'][-1]) / self.metrics['waiting_times'][0] * 100,
            'improvement_queue_length': (self.metrics['queue_lengths'][0] - 
                                       self.metrics['queue_lengths'][-1]) / self.metrics['queue_lengths'][0] * 100
        }
        
        # Save summary to file
        summary_file = os.path.join(self.log_dir, f"sync_metrics_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("Generated performance summary:")
        logger.info(f"Total time: {summary['total_time_minutes']:.2f} minutes")
        logger.info(f"Average waiting time: {summary['avg_waiting_time']:.2f} seconds")
        logger.info(f"Average queue length: {summary['avg_queue_length']:.2f} vehicles")
        logger.info(f"Average speed: {summary['avg_speed']:.2f} km/h")
        logger.info(f"Average reward: {summary['avg_reward']:.2f}")
        logger.info(f"Average sync quality: {summary['avg_sync_quality']:.2f}")
        logger.info(f"Waiting time improvement: {summary['improvement_waiting_time']:.2f}%")
        logger.info(f"Queue length improvement: {summary['improvement_queue_length']:.2f}%")
        
        return summary 