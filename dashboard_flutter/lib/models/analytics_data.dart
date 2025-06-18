class AnalyticsData {
  final DateTime startDate;
  final DateTime endDate;
  final String? intersectionId;
  final List<PerformanceMetric> metrics;
  final List<TimeSeriesData> waitTimeSeries;
  final List<TimeSeriesData> queueLengthSeries;
  final List<TimeSeriesData> throughputSeries;
  final Map<String, double> aggregatedMetrics;
  final List<ComparisonData> comparisons;

  AnalyticsData({
    required this.startDate,
    required this.endDate,
    this.intersectionId,
    required this.metrics,
    required this.waitTimeSeries,
    required this.queueLengthSeries,
    required this.throughputSeries,
    required this.aggregatedMetrics,
    required this.comparisons,
  });

  factory AnalyticsData.fromJson(Map<String, dynamic> json) {
    return AnalyticsData(
      startDate: DateTime.tryParse(json['startDate'] ?? '') ?? DateTime.now(),
      endDate: DateTime.tryParse(json['endDate'] ?? '') ?? DateTime.now(),
      intersectionId: json['intersectionId'],
      metrics: (json['metrics'] as List<dynamic>? ?? [])
          .map((metric) => PerformanceMetric.fromJson(metric))
          .toList(),
      waitTimeSeries: (json['waitTimeSeries'] as List<dynamic>? ?? [])
          .map((data) => TimeSeriesData.fromJson(data))
          .toList(),
      queueLengthSeries: (json['queueLengthSeries'] as List<dynamic>? ?? [])
          .map((data) => TimeSeriesData.fromJson(data))
          .toList(),
      throughputSeries: (json['throughputSeries'] as List<dynamic>? ?? [])
          .map((data) => TimeSeriesData.fromJson(data))
          .toList(),
      aggregatedMetrics: Map<String, double>.from(json['aggregatedMetrics'] ?? {}),
      comparisons: (json['comparisons'] as List<dynamic>? ?? [])
          .map((comp) => ComparisonData.fromJson(comp))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'startDate': startDate.toIso8601String(),
      'endDate': endDate.toIso8601String(),
      'intersectionId': intersectionId,
      'metrics': metrics.map((metric) => metric.toJson()).toList(),
      'waitTimeSeries': waitTimeSeries.map((data) => data.toJson()).toList(),
      'queueLengthSeries': queueLengthSeries.map((data) => data.toJson()).toList(),
      'throughputSeries': throughputSeries.map((data) => data.toJson()).toList(),
      'aggregatedMetrics': aggregatedMetrics,
      'comparisons': comparisons.map((comp) => comp.toJson()).toList(),
    };
  }

  AnalyticsData copyWith({
    DateTime? startDate,
    DateTime? endDate,
    String? intersectionId,
    List<PerformanceMetric>? metrics,
    List<TimeSeriesData>? waitTimeSeries,
    List<TimeSeriesData>? queueLengthSeries,
    List<TimeSeriesData>? throughputSeries,
    Map<String, double>? aggregatedMetrics,
    List<ComparisonData>? comparisons,
  }) {
    return AnalyticsData(
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      intersectionId: intersectionId ?? this.intersectionId,
      metrics: metrics ?? this.metrics,
      waitTimeSeries: waitTimeSeries ?? this.waitTimeSeries,
      queueLengthSeries: queueLengthSeries ?? this.queueLengthSeries,
      throughputSeries: throughputSeries ?? this.throughputSeries,
      aggregatedMetrics: aggregatedMetrics ?? this.aggregatedMetrics,
      comparisons: comparisons ?? this.comparisons,
    );
  }
}

class PerformanceMetric {
  final String name;
  final double value;
  final String unit;
  final double? previousValue;
  final String? trend;
  final DateTime timestamp;

  PerformanceMetric({
    required this.name,
    required this.value,
    required this.unit,
    this.previousValue,
    this.trend,
    required this.timestamp,
  });

  factory PerformanceMetric.fromJson(Map<String, dynamic> json) {
    return PerformanceMetric(
      name: json['name'] ?? '',
      value: (json['value'] ?? 0.0).toDouble(),
      unit: json['unit'] ?? '',
      previousValue: json['previousValue']?.toDouble(),
      trend: json['trend'],
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'value': value,
      'unit': unit,
      'previousValue': previousValue,
      'trend': trend,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  double? get changePercentage {
    if (previousValue == null || previousValue == 0) return null;
    return ((value - previousValue!) / previousValue!) * 100;
  }

  bool get isImproving => trend == 'up' && name.contains('efficiency') || 
                         trend == 'down' && (name.contains('wait') || name.contains('queue'));
}

class TimeSeriesData {
  final DateTime timestamp;
  final double value;
  final String? label;

  TimeSeriesData({
    required this.timestamp,
    required this.value,
    this.label,
  });

  factory TimeSeriesData.fromJson(Map<String, dynamic> json) {
    return TimeSeriesData(
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
      value: (json['value'] ?? 0.0).toDouble(),
      label: json['label'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toIso8601String(),
      'value': value,
      'label': label,
    };
  }
}

class ComparisonData {
  final String name;
  final double beforeValue;
  final double afterValue;
  final String unit;
  final double improvementPercentage;
  final DateTime comparisonDate;

  ComparisonData({
    required this.name,
    required this.beforeValue,
    required this.afterValue,
    required this.unit,
    required this.improvementPercentage,
    required this.comparisonDate,
  });

  factory ComparisonData.fromJson(Map<String, dynamic> json) {
    return ComparisonData(
      name: json['name'] ?? '',
      beforeValue: (json['beforeValue'] ?? 0.0).toDouble(),
      afterValue: (json['afterValue'] ?? 0.0).toDouble(),
      unit: json['unit'] ?? '',
      improvementPercentage: (json['improvementPercentage'] ?? 0.0).toDouble(),
      comparisonDate: DateTime.tryParse(json['comparisonDate'] ?? '') ?? DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'beforeValue': beforeValue,
      'afterValue': afterValue,
      'unit': unit,
      'improvementPercentage': improvementPercentage,
      'comparisonDate': comparisonDate.toIso8601String(),
    };
  }

  bool get isImprovement => improvementPercentage > 0;
  bool get isSignificantImprovement => improvementPercentage > 10;
} 