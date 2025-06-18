import "package:flutter/material.dart";
import 'package:get/get.dart';
import 'package:responsive_framework/responsive_framework.dart';
import '../../controllers/realtime_controller.dart';
import '../../widgets/dashboard_widgets.dart';
import '../../widgets/chart_widgets.dart';

class TrainingScreen extends StatelessWidget {
  const TrainingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final realtimeController = Get.put(RealtimeController());
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;

    return Scaffold(
      appBar: AppBar(
        title: const Text('DRL Training Management'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showTrainingConfiguration(context),
          ),
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => _showTrainingHistory(context),
          ),
        ],
      ),
      body: Obx(() => Column(
        children: [
          // Training Status Header
          Container(
            padding: EdgeInsets.all(isMobile ? 12 : 16),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          realtimeController.isTrainingActive.value ? Icons.play_circle : Icons.pause_circle,
                          size: 32,
                          color: realtimeController.isTrainingActive.value ? Colors.green : Colors.orange,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                realtimeController.isTrainingActive.value ? 'Training Active' : 'Training Paused',
                                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: realtimeController.isTrainingActive.value ? Colors.green : Colors.orange,
                                ),
                              ),
                              Text(
                                'Model: ${realtimeController.currentModel.value}',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (realtimeController.isTrainingActive.value)
                          ElevatedButton.icon(
                            onPressed: () => _stopTraining(realtimeController),
                            icon: const Icon(Icons.stop),
                            label: const Text('Stop'),
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                          )
                        else
                          ElevatedButton.icon(
                            onPressed: () => _startTraining(context, realtimeController),
                            icon: const Icon(Icons.play_arrow),
                            label: const Text('Start'),
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                          ),
                      ],
                    ),
                    if (realtimeController.isTrainingActive.value) ...[
                      const SizedBox(height: 16),
                      LinearProgressIndicator(
                        value: realtimeController.trainingProgress.value / 100,
                        backgroundColor: Colors.grey.withOpacity(0.3),
                        valueColor: AlwaysStoppedAnimation<Color>(
                          Theme.of(context).colorScheme.primary,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Episode ${realtimeController.currentEpisode.value}/${realtimeController.maxEpisodes.value}'),
                          Text('${realtimeController.trainingProgress.value.toStringAsFixed(1)}%'),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),

          // Training Metrics
          Container(
            padding: EdgeInsets.symmetric(horizontal: isMobile ? 12 : 16),
            child: ResponsiveRowColumn(
              layout: isMobile ? ResponsiveRowColumnType.COLUMN : ResponsiveRowColumnType.ROW,
              rowSpacing: 16,
              columnSpacing: 16,
              children: [
                ResponsiveRowColumnItem(
                  child: KPICard(
                    title: 'Current Reward',
                    value: realtimeController.currentReward.value.toStringAsFixed(2),
                    icon: Icons.star,
                    color: Colors.amber,
                                          trend: '+${realtimeController.rewardTrend.value.toStringAsFixed(1)}%',
                  ),
                ),
                ResponsiveRowColumnItem(
                  child: KPICard(
                    title: 'Best Reward',
                    value: realtimeController.bestReward.value.toStringAsFixed(2),
                    icon: Icons.emoji_events,
                                            color: Colors.amber,
                    subtitle: 'Episode ${realtimeController.bestRewardEpisode.value}',
                  ),
                ),
                ResponsiveRowColumnItem(
                  child: KPICard(
                    title: 'Training Time',
                    value: realtimeController.trainingDuration.value,
                    icon: Icons.timer,
                    color: Colors.blue,
                    subtitle: 'Elapsed time',
                  ),
                ),
                ResponsiveRowColumnItem(
                  child: KPICard(
                    title: 'Learning Rate',
                    value: realtimeController.learningRate.value.toStringAsExponential(2),
                    icon: Icons.trending_up,
                    color: Colors.purple,
                    subtitle: 'Current LR',
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Training Charts
          Expanded(
            child: SingleChildScrollView(
              padding: EdgeInsets.symmetric(horizontal: isMobile ? 12 : 16),
              child: Column(
                children: [
                  // Reward Progress Chart
                  RealTimePerformanceMonitor(
                    data: realtimeController.rewardHistory,
                    title: 'Episode Rewards',
                    isLive: realtimeController.isTrainingActive.value,
                  ),

                  const SizedBox(height: 16),

                  // Loss and Learning Charts
                  Row(
                    children: [
                      Expanded(
                        child: PerformanceLineChart(
                          data: realtimeController.lossHistory,
                          title: 'Training Loss',
                          lineColor: Colors.red,
                          yAxisLabel: 'Loss',
                          xAxisLabel: 'Episode',
                        ),
                      ),
                      if (!isMobile) ...[
                        const SizedBox(width: 16),
                        Expanded(
                          child: PerformanceLineChart(
                            data: realtimeController.epsilonHistory,
                            title: 'Exploration Rate (ε)',
                            lineColor: Colors.orange,
                            yAxisLabel: 'Epsilon',
                            xAxisLabel: 'Episode',
                          ),
                        ),
                      ],
                    ],
                  ),

                  const SizedBox(height: 16),

                  // Performance Metrics
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Performance Metrics',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: MetricCard(
                                  label: 'Average Queue Length',
                                  value: realtimeController.avgQueueLength.value.toStringAsFixed(2),
                                  icon: Icons.linear_scale,
                                  color: Colors.blue,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: MetricCard(
                                  label: 'Average Wait Time',
                                  value: '${realtimeController.avgWaitTime.value.toStringAsFixed(1)}s',
                                  icon: Icons.timer,
                                  color: Colors.orange,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: MetricCard(
                                  label: 'Throughput',
                                  value: '${realtimeController.throughput.value.toStringAsFixed(0)} veh/h',
                                  icon: Icons.speed,
                                  color: Colors.green,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Training Configuration and Model Info
                  Row(
                    children: [
                      Expanded(
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Current Configuration',
                                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                _buildConfigRow('Algorithm', realtimeController.algorithm.value),
                                _buildConfigRow('Learning Rate', realtimeController.learningRate.value.toString()),
                                _buildConfigRow('Batch Size', realtimeController.batchSize.value.toString()),
                                _buildConfigRow('Memory Size', realtimeController.memorySize.value.toString()),
                                _buildConfigRow('Target Update', realtimeController.targetUpdate.value.toString()),
                                const SizedBox(height: 12),
                                ElevatedButton(
                                  onPressed: () => _showTrainingConfiguration(context),
                                  child: const Text('Configure'),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      if (!isMobile) ...[
                        const SizedBox(width: 16),
                        Expanded(
                          child: Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Model Information',
                                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  _buildConfigRow('Model Name', realtimeController.currentModel.value),
                                  _buildConfigRow('Version', realtimeController.modelVersion.value),
                                  _buildConfigRow('Parameters', realtimeController.modelParameters.value.toString()),
                                  _buildConfigRow('Input Shape', realtimeController.inputShape.value),
                                  _buildConfigRow('Output Shape', realtimeController.outputShape.value),
                                  const SizedBox(height: 12),
                                  Row(
                                    children: [
                                      ElevatedButton(
                                        onPressed: () => _saveModel(realtimeController),
                                        child: const Text('Save Model'),
                                      ),
                                      const SizedBox(width: 8),
                                      OutlinedButton(
                                        onPressed: () => _loadModel(context, realtimeController),
                                        child: const Text('Load Model'),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),

                  const SizedBox(height: 16),

                  // Recent Training Logs
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                'Training Logs',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const Spacer(),
                              TextButton(
                                onPressed: () => _showFullLogs(context, realtimeController),
                                child: const Text('View All'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Container(
                            height: 200,
                            decoration: BoxDecoration(
                              color: Colors.black87,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.grey.withOpacity(0.3)),
                            ),
                            child: ListView.builder(
                              padding: const EdgeInsets.all(8),
                              itemCount: realtimeController.trainingLogs.length,
                              itemBuilder: (context, index) {
                                final log = realtimeController.trainingLogs[index];
                                return Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 2),
                                  child: Text(
                                    log,
                                    style: const TextStyle(
                                      color: Colors.green,
                                      fontFamily: 'monospace',
                                      fontSize: 12,
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ],
      )),
    );
  }

  Widget _buildConfigRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
        ],
      ),
    );
  }

  void _startTraining(BuildContext context, RealtimeController controller) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Start Training'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Are you sure you want to start training?'),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              decoration: const InputDecoration(
                labelText: 'Training Mode',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'single', child: Text('Single Intersection')),
                DropdownMenuItem(value: 'multi', child: Text('Multi Intersection')),
                DropdownMenuItem(value: 'synchronized', child: Text('Synchronized Network')),
              ],
              onChanged: (value) {},
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              controller.startTraining();
              Navigator.of(context).pop();
            },
            child: const Text('Start'),
          ),
        ],
      ),
    );
  }

  void _stopTraining(RealtimeController controller) {
    Get.dialog(
      AlertDialog(
        title: const Text('Stop Training'),
        content: const Text('Are you sure you want to stop the current training session? Progress will be saved.'),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              controller.stopTraining();
              Get.back();
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Stop'),
          ),
        ],
      ),
    );
  }

  void _showTrainingConfiguration(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Training Configuration',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              const Text('Training configuration interface would be implemented here with:'),
              const SizedBox(height: 8),
              const Text('• Algorithm selection (DQN, A2C, PPO)'),
              const Text('• Hyperparameters (learning rate, batch size, etc.)'),
              const Text('• Network architecture'),
              const Text('• Reward function parameters'),
              const Text('• Training schedule'),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Save Configuration'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showTrainingHistory(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 800,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Training History',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.check_circle, color: Colors.green),
                      title: const Text('Training Session #142'),
                      subtitle: const Text('Completed: 1000 episodes, Best reward: 156.7'),
                      trailing: const Text('2 hours ago'),
                    ),
                    ListTile(
                      leading: const Icon(Icons.check_circle, color: Colors.green),
                      title: const Text('Training Session #141'),
                      subtitle: const Text('Completed: 800 episodes, Best reward: 145.2'),
                      trailing: const Text('1 day ago'),
                    ),
                    ListTile(
                      leading: const Icon(Icons.error, color: Colors.red),
                      title: const Text('Training Session #140'),
                      subtitle: const Text('Failed: Connection lost at episode 456'),
                      trailing: const Text('2 days ago'),
                    ),
                  ],
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Close'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _saveModel(RealtimeController controller) {
    Get.dialog(
      AlertDialog(
        title: const Text('Save Model'),
        content: const TextField(
          decoration: InputDecoration(
            labelText: 'Model Name',
            hintText: 'Enter model name',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              controller.saveModel();
              Get.back();
              Get.snackbar('Success', 'Model saved successfully');
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _loadModel(BuildContext context, RealtimeController controller) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Load Model'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('model_142.h5'),
              subtitle: const Text('Best reward: 156.7, 1000 episodes'),
              trailing: const Icon(Icons.download),
              onTap: () {
                controller.loadModel('model_142.h5');
                Navigator.of(context).pop();
              },
            ),
            ListTile(
              title: const Text('model_141.h5'),
              subtitle: const Text('Best reward: 145.2, 800 episodes'),
              trailing: const Icon(Icons.download),
              onTap: () {
                controller.loadModel('model_141.h5');
                Navigator.of(context).pop();
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  void _showFullLogs(BuildContext context, RealtimeController controller) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 800,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Training Logs',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey.withOpacity(0.3)),
                  ),
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: controller.trainingLogs.length,
                    itemBuilder: (context, index) {
                      final log = controller.trainingLogs[index];
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Text(
                          log,
                          style: const TextStyle(
                            color: Colors.green,
                            fontFamily: 'monospace',
                            fontSize: 12,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
