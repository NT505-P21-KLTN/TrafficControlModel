import 'package:get/get.dart';
import 'dart:async';
import '../models/intersection_data.dart';
import '../models/system_status.dart';
import 'api_controller.dart';

class DashboardController extends GetxController {
  final ApiController _apiController = Get.find<ApiController>();
  
  // Reactive variables
  final RxBool isLoading = false.obs;
  final RxString selectedIntersection = ''.obs;
  final RxString dashboardView = 'overview'.obs; // overview, detailed, analytics
  final RxMap<String, dynamic> dashboardData = <String, dynamic>{}.obs;
  final RxList<IntersectionData> intersections = <IntersectionData>[].obs;
  final Rx<SystemStatus?> systemStatus = Rx<SystemStatus?>(null);
  
  // Timers for periodic updates
  Timer? _dataRefreshTimer;
  Timer? _statusRefreshTimer;

  @override
  void onInit() {
    super.onInit();
    _initializeDashboard();
    _startPeriodicUpdates();
    
    // Add timeout mechanism
    Timer(const Duration(seconds: 10), () {
      if (isLoading.value) {
        isLoading.value = false;
        // Set some default data if loading fails
        dashboardData.value = {
          'summary': {
            'activeIntersections': 0,
            'avgWaitTime': 0,
            'totalVehicles': 0,
            'efficiency': 0.0,
          },
          'charts': {},
        };
      }
    });
  }

  @override
  void onClose() {
    _dataRefreshTimer?.cancel();
    _statusRefreshTimer?.cancel();
    super.onClose();
  }

  Future<void> _initializeDashboard() async {
    isLoading.value = true;
    try {
      await Future.wait([
        refreshIntersections(),
        refreshSystemStatus(),
      ]);
    } catch (e) {
      // print('[Dashboard] Error initializing: $e');
      Get.snackbar(
        'Dashboard Error',
        'Failed to initialize dashboard: $e',
        snackPosition: SnackPosition.BOTTOM,
      );
    } finally {
      isLoading.value = false;
    }
  }

  void _startPeriodicUpdates() {
    // Refresh intersection data every 30 seconds
    _dataRefreshTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      refreshIntersections();
    });

    // Refresh system status every 10 seconds
    _statusRefreshTimer = Timer.periodic(const Duration(seconds: 10), (timer) {
      refreshSystemStatus();
    });
  }

  Future<void> refreshIntersections() async {
    try {
      final data = await _apiController.getIntersections();
      intersections.value = data;
      
      // Update dashboard metrics
      _updateDashboardMetrics();
    } catch (e) {
      // print('[Dashboard] Error refreshing intersections: $e');
    }
  }

  Future<void> refreshSystemStatus() async {
    try {
      final status = await _apiController.getSystemStatus();
      systemStatus.value = status;
    } catch (e) {
      // print('[Dashboard] Error refreshing system status: $e');
    }
  }

  void _updateDashboardMetrics() {
    if (intersections.isEmpty) return;

    final onlineCount = intersections.where((i) => i.isOnline).length;
    final totalWaitTime = intersections.fold<double>(
      0.0,
      (sum, i) => sum + i.metrics.averageWaitTime,
    );
    final averageWaitTime = totalWaitTime / intersections.length;
    
    final totalQueueLength = intersections.fold<double>(
      0.0,
      (sum, i) => sum + i.metrics.averageQueueLength,
    );
    final averageQueueLength = totalQueueLength / intersections.length;

    final totalVehicles = intersections.fold<int>(
      0,
      (sum, i) => sum + i.metrics.vehicleCount,
    );

    final averageEfficiency = intersections.fold<double>(
      0.0,
      (sum, i) => sum + i.metrics.efficiency,
    ) / intersections.length;

    dashboardData.value = {
      'summary': {
        'totalIntersections': intersections.length,
        'onlineIntersections': onlineCount,
        'offlineIntersections': intersections.length - onlineCount,
        'averageWaitTime': averageWaitTime,
        'averageQueueLength': averageQueueLength,
        'totalVehicles': totalVehicles,
        'systemEfficiency': averageEfficiency,
      },
      'recentAlerts': _getRecentAlerts(),
      'performanceTrends': _calculatePerformanceTrends(),
      'lastUpdate': DateTime.now(),
    };
  }

  List<Map<String, dynamic>> _getRecentAlerts() {
    // Extract recent alerts from intersections
    final alerts = <Map<String, dynamic>>[];
    
    for (final intersection in intersections) {
      if (intersection.hasIssues) {
        alerts.add({
          'id': '${intersection.id}_status',
          'title': 'Intersection Issue',
          'message': '${intersection.name} has status: ${intersection.status}',
          'severity': intersection.status == 'error' ? 'critical' : 'warning',
          'timestamp': intersection.lastUpdate,
          'intersectionId': intersection.id,
        });
      }

      // Check for performance issues
      if (intersection.metrics.averageWaitTime > 60) {
        alerts.add({
          'id': '${intersection.id}_wait',
          'title': 'High Wait Time',
          'message': '${intersection.name} has high wait time: ${intersection.metrics.averageWaitTime.toStringAsFixed(1)}s',
          'severity': 'warning',
          'timestamp': intersection.metrics.timestamp,
          'intersectionId': intersection.id,
        });
      }

      if (intersection.metrics.averageQueueLength > 10) {
        alerts.add({
          'id': '${intersection.id}_queue',
          'title': 'Long Queue',
          'message': '${intersection.name} has long queue: ${intersection.metrics.averageQueueLength.toStringAsFixed(1)} vehicles',
          'severity': 'warning',
          'timestamp': intersection.metrics.timestamp,
          'intersectionId': intersection.id,
        });
      }
    }

    // Sort by timestamp (newest first) and take only recent ones
    alerts.sort((a, b) => (b['timestamp'] as DateTime).compareTo(a['timestamp'] as DateTime));
    return alerts.take(10).toList();
  }

  Map<String, List<double>> _calculatePerformanceTrends() {
    // Calculate simple trends from current data
    // In a real app, this would use historical data
    final trends = <String, List<double>>{};
    
    final waitTimes = intersections.map((i) => i.metrics.averageWaitTime).toList();
    final queueLengths = intersections.map((i) => i.metrics.averageQueueLength).toList();
    final efficiencies = intersections.map((i) => i.metrics.efficiency).toList();
    
    trends['waitTimes'] = waitTimes;
    trends['queueLengths'] = queueLengths;
    trends['efficiencies'] = efficiencies;
    
    return trends;
  }

  void selectIntersection(String intersectionId) {
    selectedIntersection.value = intersectionId;
  }

  void setDashboardView(String view) {
    dashboardView.value = view;
  }

  IntersectionData? getSelectedIntersection() {
    if (selectedIntersection.value.isEmpty) return null;
    
    try {
      return intersections.firstWhere(
        (intersection) => intersection.id == selectedIntersection.value,
      );
    } catch (e) {
      return null;
    }
  }

  List<IntersectionData> getOnlineIntersections() {
    return intersections.where((i) => i.isOnline).toList();
  }

  List<IntersectionData> getOfflineIntersections() {
    return intersections.where((i) => i.isOffline).toList();
  }

  List<IntersectionData> getTrainingIntersections() {
    return intersections.where((i) => i.isTraining).toList();
  }

  double getSystemHealthScore() {
    if (intersections.isEmpty) return 0.0;
    
    final onlineCount = getOnlineIntersections().length;
    final healthScore = (onlineCount / intersections.length) * 100;
    
    return healthScore;
  }

  Future<void> forceRefresh() async {
    isLoading.value = true;
    await _initializeDashboard();
    isLoading.value = false;
  }

  // Real-time event handling
  void handleRealtimeUpdate(Map<String, dynamic> update) {
    switch (update['type']) {
      case 'intersection_update':
        final data = IntersectionData.fromJson(update['data']);
        final index = intersections.indexWhere((i) => i.id == data.id);
        if (index != -1) {
          intersections[index] = data;
          _updateDashboardMetrics();
        }
        break;
      case 'system_alert':
        // Handle new system alerts
        Get.snackbar(
          update['title'] ?? 'System Alert',
          update['message'] ?? 'New system event',
          snackPosition: SnackPosition.TOP,
          duration: const Duration(seconds: 5),
        );
        break;
    }
  }
} 