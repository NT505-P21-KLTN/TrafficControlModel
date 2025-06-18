import 'package:get/get.dart';
import '../models/analytics_data.dart';
import 'api_controller.dart';

class AnalyticsController extends GetxController {
  final ApiController _apiController = Get.find<ApiController>();
  
  final RxBool isLoading = false.obs;
  final Rx<AnalyticsData?> currentAnalytics = Rx<AnalyticsData?>(null);
  final RxString selectedTimeRange = '24h'.obs;
  final RxString selectedIntersection = 'all'.obs;
  final RxList<String> availableMetrics = <String>[].obs;
  
  // KPI properties
  final RxDouble avgPerformanceScore = RxDouble(0.85);
  final RxInt totalVehiclesProcessed = RxInt(1250);
  final RxDouble avgWaitTime = RxDouble(32.5);
  final RxDouble queueEfficiency = RxDouble(0.78);
  final RxDouble performanceTrend = RxDouble(5.2);
  final RxDouble vehiclesTrend = RxDouble(12.3);
  final RxDouble waitTimeTrend = RxDouble(-8.1);
  final RxDouble queueTrend = RxDouble(15.4);
  
  // Chart data
  final RxList<Map<String, dynamic>> performanceData = <Map<String, dynamic>>[].obs;

  @override
  void onInit() {
    super.onInit();
    _initializeMetrics();
    loadAnalytics();
  }

  void _initializeMetrics() {
    availableMetrics.value = [
      'Average Wait Time',
      'Queue Length',
      'Throughput',
      'System Efficiency',
      'Vehicle Count',
      'Phase Duration',
    ];
    
    // Initialize mock chart data
    _initializeMockData();
  }
  
  void _initializeMockData() {
    // Mock performance data for the last 24 hours
    performanceData.value = List.generate(24, (index) {
      return {
        'time': index,
        'value': 0.75 + (0.15 * (index / 24)) + (0.05 * (1 - (index % 3) / 3)),
        'timestamp': DateTime.now().subtract(Duration(hours: 23 - index)).toIso8601String(),
      };
    });
  }

  Future<void> loadAnalytics({
    DateTime? startDate,
    DateTime? endDate,
    String? intersectionId,
  }) async {
    isLoading.value = true;
    try {
      // Calculate date range based on selected time range
      final now = DateTime.now();
      DateTime calculatedStartDate = startDate ?? _getStartDateFromRange(now);
      DateTime calculatedEndDate = endDate ?? now;
      String? targetIntersection = intersectionId ?? 
          (selectedIntersection.value == 'all' ? null : selectedIntersection.value);

      final analytics = await _apiController.getAnalytics(
        startDate: calculatedStartDate,
        endDate: calculatedEndDate,
        intersectionId: targetIntersection,
      );

      currentAnalytics.value = analytics;
    } catch (e) {
      Get.snackbar('Error', 'Failed to load analytics: $e');
      // print('[Analytics] Error loading analytics: $e');
    } finally {
      isLoading.value = false;
    }
  }

  DateTime _getStartDateFromRange(DateTime endDate) {
    switch (selectedTimeRange.value) {
      case '1h':
        return endDate.subtract(const Duration(hours: 1));
      case '6h':
        return endDate.subtract(const Duration(hours: 6));
      case '24h':
        return endDate.subtract(const Duration(hours: 24));
      case '7d':
        return endDate.subtract(const Duration(days: 7));
      case '30d':
        return endDate.subtract(const Duration(days: 30));
      default:
        return endDate.subtract(const Duration(hours: 24));
    }
  }

  void setTimeRange(String range) {
    selectedTimeRange.value = range;
    loadAnalytics();
  }

  void setSelectedIntersection(String intersectionId) {
    selectedIntersection.value = intersectionId;
    loadAnalytics();
  }

  Future<void> exportAnalytics(String format) async {
    try {
      if (currentAnalytics.value == null) {
        Get.snackbar('Warning', 'No analytics data to export');
        return;
      }

      // In a real app, this would generate and download the file
      Get.snackbar(
        'Export Started', 
        'Analytics data export in $format format has been initiated',
        snackPosition: SnackPosition.BOTTOM,
      );
      
      // Simulate export process
      await Future.delayed(const Duration(seconds: 2));
      
      Get.snackbar(
        'Export Complete', 
        'Analytics data has been exported successfully',
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar('Error', 'Failed to export analytics: $e');
    }
  }

  Map<String, dynamic> getPerformanceSummary() {
    final analytics = currentAnalytics.value;
    if (analytics == null) return {};

    final summary = <String, dynamic>{};
    
    // Calculate average metrics
    if (analytics.waitTimeSeries.isNotEmpty) {
      final avgWaitTime = analytics.waitTimeSeries
          .map((e) => e.value)
          .reduce((a, b) => a + b) / analytics.waitTimeSeries.length;
      summary['averageWaitTime'] = avgWaitTime;
    }

    if (analytics.queueLengthSeries.isNotEmpty) {
      final avgQueue = analytics.queueLengthSeries
          .map((e) => e.value)
          .reduce((a, b) => a + b) / analytics.queueLengthSeries.length;
      summary['averageQueueLength'] = avgQueue;
    }

    if (analytics.throughputSeries.isNotEmpty) {
      final avgThroughput = analytics.throughputSeries
          .map((e) => e.value)
          .reduce((a, b) => a + b) / analytics.throughputSeries.length;
      summary['averageThroughput'] = avgThroughput;
    }

    // Add comparison data
    summary['comparisons'] = analytics.comparisons;
    summary['timeRange'] = selectedTimeRange.value;
    summary['intersection'] = selectedIntersection.value;

    return summary;
  }

  List<Map<String, dynamic>> getChartData(String metricType) {
    final analytics = currentAnalytics.value;
    if (analytics == null) return [];

    List<TimeSeriesData> series = [];
    
    switch (metricType.toLowerCase()) {
      case 'wait_time':
        series = analytics.waitTimeSeries;
        break;
      case 'queue_length':
        series = analytics.queueLengthSeries;
        break;
      case 'throughput':
        series = analytics.throughputSeries;
        break;
    }

    return series.map((data) => {
      'timestamp': data.timestamp.millisecondsSinceEpoch,
      'value': data.value,
      'label': data.label,
    }).toList();
  }

  double getMetricImprovement(String metricName) {
    final analytics = currentAnalytics.value;
    if (analytics == null) return 0.0;

    final comparison = analytics.comparisons.firstWhereOrNull(
      (comp) => comp.name.toLowerCase() == metricName.toLowerCase(),
    );

    return comparison?.improvementPercentage ?? 0.0;
  }

  bool hasData() {
    return currentAnalytics.value != null;
  }

  Future<void> refreshAnalytics() async {
    await loadAnalytics();
  }
} 