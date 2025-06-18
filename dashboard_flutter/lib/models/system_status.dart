class SystemStatus {
  final bool isOnline;
  final int activeIntersections;
  final int totalIntersections;
  final double systemHealth;
  final String version;
  final DateTime lastUpdate;
  final Map<String, dynamic> serverInfo;
  final List<SystemAlert> alerts;

  SystemStatus({
    required this.isOnline,
    required this.activeIntersections,
    required this.totalIntersections,
    required this.systemHealth,
    required this.version,
    required this.lastUpdate,
    required this.serverInfo,
    required this.alerts,
  });

  factory SystemStatus.fromJson(Map<String, dynamic> json) {
    return SystemStatus(
      isOnline: json['isOnline'] ?? false,
      activeIntersections: json['activeIntersections'] ?? 0,
      totalIntersections: json['totalIntersections'] ?? 0,
      systemHealth: (json['systemHealth'] ?? 0.0).toDouble(),
      version: json['version'] ?? '1.0.0',
      lastUpdate: DateTime.tryParse(json['lastUpdate'] ?? '') ?? DateTime.now(),
      serverInfo: Map<String, dynamic>.from(json['serverInfo'] ?? {}),
      alerts: (json['alerts'] as List<dynamic>? ?? [])
          .map((alert) => SystemAlert.fromJson(alert))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'isOnline': isOnline,
      'activeIntersections': activeIntersections,
      'totalIntersections': totalIntersections,
      'systemHealth': systemHealth,
      'version': version,
      'lastUpdate': lastUpdate.toIso8601String(),
      'serverInfo': serverInfo,
      'alerts': alerts.map((alert) => alert.toJson()).toList(),
    };
  }

  SystemStatus copyWith({
    bool? isOnline,
    int? activeIntersections,
    int? totalIntersections,
    double? systemHealth,
    String? version,
    DateTime? lastUpdate,
    Map<String, dynamic>? serverInfo,
    List<SystemAlert>? alerts,
  }) {
    return SystemStatus(
      isOnline: isOnline ?? this.isOnline,
      activeIntersections: activeIntersections ?? this.activeIntersections,
      totalIntersections: totalIntersections ?? this.totalIntersections,
      systemHealth: systemHealth ?? this.systemHealth,
      version: version ?? this.version,
      lastUpdate: lastUpdate ?? this.lastUpdate,
      serverInfo: serverInfo ?? this.serverInfo,
      alerts: alerts ?? this.alerts,
    );
  }

  double get healthPercentage => systemHealth * 100;
  bool get hasAlerts => alerts.isNotEmpty;
  bool get hasCriticalAlerts => alerts.any((alert) => alert.severity == 'critical');
}

class SystemAlert {
  final String id;
  final String title;
  final String message;
  final String severity;
  final DateTime timestamp;
  final String? intersectionId;
  final bool isRead;

  SystemAlert({
    required this.id,
    required this.title,
    required this.message,
    required this.severity,
    required this.timestamp,
    this.intersectionId,
    required this.isRead,
  });

  factory SystemAlert.fromJson(Map<String, dynamic> json) {
    return SystemAlert(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      message: json['message'] ?? '',
      severity: json['severity'] ?? 'info',
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
      intersectionId: json['intersectionId'],
      isRead: json['isRead'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'message': message,
      'severity': severity,
      'timestamp': timestamp.toIso8601String(),
      'intersectionId': intersectionId,
      'isRead': isRead,
    };
  }

  SystemAlert copyWith({
    String? id,
    String? title,
    String? message,
    String? severity,
    DateTime? timestamp,
    String? intersectionId,
    bool? isRead,
  }) {
    return SystemAlert(
      id: id ?? this.id,
      title: title ?? this.title,
      message: message ?? this.message,
      severity: severity ?? this.severity,
      timestamp: timestamp ?? this.timestamp,
      intersectionId: intersectionId ?? this.intersectionId,
      isRead: isRead ?? this.isRead,
    );
  }

  bool get isInfo => severity == 'info';
  bool get isWarning => severity == 'warning';
  bool get isError => severity == 'error';
  bool get isCritical => severity == 'critical';
} 