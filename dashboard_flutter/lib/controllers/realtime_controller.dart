import 'package:get/get.dart';
import 'dart:async';
import 'dart:math' as math;
import 'api_controller.dart';

class RealtimeController extends GetxController {
  final ApiController _apiController = Get.find<ApiController>();
  
  final RxBool isConnected = false.obs;
  final RxList<Map<String, dynamic>> realtimeEvents = <Map<String, dynamic>>[].obs;
  final RxMap<String, dynamic> liveMetrics = <String, dynamic>{}.obs;
  
  // Training properties
  final RxBool isTrainingActive = false.obs;
  final RxDouble trainingProgress = 0.0.obs;
  final RxInt currentEpisode = 0.obs;
  final RxInt maxEpisodes = 1000.obs;
  final RxDouble currentReward = 0.0.obs;
  final RxDouble bestReward = 0.0.obs;
  final RxInt bestRewardEpisode = 0.obs;
  final RxDouble learningRate = 0.001.obs;
  final RxString currentModel = 'DQN'.obs;
  final RxString modelVersion = '1.0.0'.obs;
  final RxInt modelParameters = 0.obs;
  final RxString inputShape = '[84, 84, 4]'.obs;
  final RxString outputShape = '[4]'.obs;
  final RxString algorithm = 'DQN'.obs;
  final RxInt batchSize = 32.obs;
  final RxInt memorySize = 10000.obs;
  final RxInt targetUpdate = 100.obs;
  final RxString trainingDuration = '00:00:00'.obs;
  final RxDouble rewardTrend = 0.0.obs;
  final RxDouble avgQueueLength = 0.0.obs;
  final RxDouble avgWaitTime = 0.0.obs;
  final RxDouble throughput = 0.0.obs;
  
  // Training history
  final RxList<Map<String, dynamic>> rewardHistory = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> lossHistory = <Map<String, dynamic>>[].obs;
  final RxList<Map<String, dynamic>> epsilonHistory = <Map<String, dynamic>>[].obs;
  final RxList<String> trainingLogs = <String>[].obs;
  
  StreamSubscription? _dataStreamSubscription;

  @override
  void onInit() {
    super.onInit();
    _startRealtimeUpdates();
  }

  @override
  void onClose() {
    _dataStreamSubscription?.cancel();
    super.onClose();
  }

  void _startRealtimeUpdates() {
    _dataStreamSubscription = _apiController.dataStream.listen(
      (data) => _handleRealtimeData(data),
      onError: (error) => _handleConnectionError(error),
    );

    // Update connection status based on API controller
    ever(_apiController.isConnected, (connected) {
      isConnected.value = connected;
    });
  }

  void _handleRealtimeData(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'intersection_update':
        _updateIntersectionMetrics(data['data']);
        break;
      case 'system_alert':
        _addRealtimeEvent(data);
        break;
      case 'performance_update':
        _updatePerformanceMetrics(data['data']);
        break;
      case 'training_progress':
        _updateTrainingProgress(data['data']);
        break;
    }
  }

  void _updateIntersectionMetrics(Map<String, dynamic> data) {
    final intersectionId = data['id'];
    liveMetrics['intersections'] ??= <String, dynamic>{};
    liveMetrics['intersections'][intersectionId] = data;
    
    _addRealtimeEvent({
      'type': 'metric_update',
      'title': 'Intersection Update',
      'message': 'Metrics updated for intersection $intersectionId',
      'timestamp': DateTime.now().toIso8601String(),
      'data': data,
    });
  }

  void _updatePerformanceMetrics(Map<String, dynamic> data) {
    liveMetrics['system'] = data;
    
    _addRealtimeEvent({
      'type': 'performance_update',
      'title': 'System Performance',
      'message': 'System performance metrics updated',
      'timestamp': DateTime.now().toIso8601String(),
      'data': data,
    });
  }

  void _updateTrainingProgress(Map<String, dynamic> data) {
    final intersectionId = data['intersection_id'];
    liveMetrics['training'] ??= <String, dynamic>{};
    liveMetrics['training'][intersectionId] = data;
    
    _addRealtimeEvent({
      'type': 'training_update',
      'title': 'Training Progress',
      'message': 'Training progress for intersection $intersectionId: ${data['progress']}%',
      'timestamp': DateTime.now().toIso8601String(),
      'data': data,
    });
  }

  void _addRealtimeEvent(Map<String, dynamic> event) {
    realtimeEvents.insert(0, event);
    
    // Keep only the last 100 events
    if (realtimeEvents.length > 100) {
      realtimeEvents.removeRange(100, realtimeEvents.length);
    }
  }

  void _handleConnectionError(dynamic error) {
    isConnected.value = false;
    _addRealtimeEvent({
      'type': 'connection_error',
      'title': 'Connection Error',
      'message': 'Lost connection to server: $error',
      'timestamp': DateTime.now().toIso8601String(),
      'severity': 'error',
    });
  }

  void clearEvents() {
    realtimeEvents.clear();
  }

  List<Map<String, dynamic>> getEventsByType(String type) {
    return realtimeEvents.where((event) => event['type'] == type).toList();
  }

  Map<String, dynamic>? getLiveMetrics(String intersectionId) {
    final intersections = liveMetrics['intersections'] as Map<String, dynamic>?;
    return intersections?[intersectionId];
  }

  Map<String, dynamic>? getSystemMetrics() {
    return liveMetrics['system'] as Map<String, dynamic>?;
  }

  Map<String, dynamic>? getTrainingProgress(String intersectionId) {
    final training = liveMetrics['training'] as Map<String, dynamic>?;
    return training?[intersectionId];
  }

  void sendRealtimeCommand(String command, Map<String, dynamic> data) {
    _apiController.sendWebSocketMessage({
      'command': command,
      'data': data,
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  // Training control methods
  Future<void> startTraining() async {
    try {
      isTrainingActive.value = true;
      currentEpisode.value = 0;
      trainingProgress.value = 0.0;
      
      // Start mock training data updates
      _startTrainingSimulation();
      
      _addRealtimeEvent({
        'type': 'training_start',
        'title': 'Training Started',
        'message': 'DRL training session started',
        'timestamp': DateTime.now().toIso8601String(),
      });
      
    } catch (e) {
      // print('[Training] Error starting training: $e');
      isTrainingActive.value = false;
    }
  }

  Future<void> stopTraining() async {
    try {
      isTrainingActive.value = false;
      
      _addRealtimeEvent({
        'type': 'training_stop',
        'title': 'Training Stopped',
        'message': 'DRL training session stopped',
        'timestamp': DateTime.now().toIso8601String(),
      });
      
    } catch (e) {
      // print('[Training] Error stopping training: $e');
    }
  }

  Future<void> saveModel() async {
    try {
      // Mock save model functionality
      await Future.delayed(const Duration(seconds: 1));
      
      _addRealtimeEvent({
        'type': 'model_save',
        'title': 'Model Saved',
        'message': 'Model saved successfully as ${currentModel.value}_${modelVersion.value}',
        'timestamp': DateTime.now().toIso8601String(),
      });
      
    } catch (e) {
      // print('[Training] Error saving model: $e');
    }
  }

  Future<void> loadModel(String modelPath) async {
    try {
      // Mock load model functionality
      await Future.delayed(const Duration(seconds: 1));
      
      currentModel.value = modelPath.split('/').last;
      
      _addRealtimeEvent({
        'type': 'model_load',
        'title': 'Model Loaded',
        'message': 'Model loaded successfully: ${currentModel.value}',
        'timestamp': DateTime.now().toIso8601String(),
      });
      
    } catch (e) {
      // print('[Training] Error loading model: $e');
    }
  }

  void _startTrainingSimulation() {
    // Mock training progress simulation
    Timer.periodic(const Duration(seconds: 2), (timer) {
      if (!isTrainingActive.value) {
        timer.cancel();
        return;
      }
      
      // Update episode and progress
      if (currentEpisode.value < maxEpisodes.value) {
        currentEpisode.value++;
        trainingProgress.value = currentEpisode.value / maxEpisodes.value;
        
        // Simulate training metrics
        final episode = currentEpisode.value;
        final reward = -2000 + (episode * 1.2) + (math.Random().nextDouble() * 200 - 100);
        currentReward.value = reward;
        
        if (reward > bestReward.value) {
          bestReward.value = reward;
          bestRewardEpisode.value = episode;
        }
        
        // Update history
        rewardHistory.add({
          'episode': episode,
          'reward': reward,
          'timestamp': DateTime.now().toIso8601String(),
        });
        
        lossHistory.add({
          'episode': episode,
          'loss': math.max(0, 800 - (episode * 0.8) + (math.Random().nextDouble() * 50 - 25)),
          'timestamp': DateTime.now().toIso8601String(),
        });
        
        epsilonHistory.add({
          'episode': episode,
          'epsilon': math.max(0.01, 1.0 - (episode * 0.001)),
          'timestamp': DateTime.now().toIso8601String(),
        });
        
        // Add training log
        trainingLogs.add(
          '[${DateTime.now().toString().substring(11, 19)}] Episode $episode - Reward: ${reward.toStringAsFixed(2)} - Loss: ${lossHistory.last['loss']?.toStringAsFixed(4)}'
        );
        
        if (trainingLogs.length > 100) {
          trainingLogs.removeAt(0);
        }
        
        // Keep history manageable
        if (rewardHistory.length > 1000) {
          rewardHistory.removeAt(0);
          lossHistory.removeAt(0);
          epsilonHistory.removeAt(0);
        }
      } else {
        // Training completed
        isTrainingActive.value = false;
        timer.cancel();
        
        _addRealtimeEvent({
          'type': 'training_complete',
          'title': 'Training Complete',
          'message': 'Training completed successfully after ${maxEpisodes.value} episodes',
          'timestamp': DateTime.now().toIso8601String(),
        });
      }
    });
  }
} 