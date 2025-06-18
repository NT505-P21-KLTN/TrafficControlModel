class LatLngPosition {
  final double latitude;
  final double longitude;

  LatLngPosition({
    required this.latitude,
    required this.longitude,
  });

  factory LatLngPosition.fromJson(Map<String, dynamic> json) {
    return LatLngPosition(
      latitude: (json['latitude'] ?? 0.0).toDouble(),
      longitude: (json['longitude'] ?? 0.0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'latitude': latitude,
      'longitude': longitude,
    };
  }

  @override
  String toString() {
    return '${latitude.toStringAsFixed(6)}, ${longitude.toStringAsFixed(6)}';
  }
}

class Camera {
  final String id;
  final String direction;
  final double latitude;
  final double longitude;
  final double range;
  final bool active;

  Camera({
    required this.id,
    required this.direction,
    required this.latitude,
    required this.longitude,
    required this.range,
    required this.active,
  });

  factory Camera.fromJson(Map<String, dynamic> json) {
    return Camera(
      id: json['id'] ?? '',
      direction: json['direction'] ?? '',
      latitude: (json['latitude'] ?? 0.0).toDouble(),
      longitude: (json['longitude'] ?? 0.0).toDouble(),
      range: (json['range'] ?? 200.0).toDouble(),
      active: json['active'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'direction': direction,
      'latitude': latitude,
      'longitude': longitude,
      'range': range,
      'active': active,
    };
  }

  Camera copyWith({
    String? id,
    String? direction,
    double? latitude,
    double? longitude,
    double? range,
    bool? active,
  }) {
    return Camera(
      id: id ?? this.id,
      direction: direction ?? this.direction,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      range: range ?? this.range,
      active: active ?? this.active,
    );
  }

  LatLngPosition get position => LatLngPosition(latitude: latitude, longitude: longitude);
}

class IntersectionData {
  final String id;
  final String name;
  final double latitude;
  final double longitude;
  final String status;
  final DateTime lastUpdate;
  final Map<String, dynamic> configuration;
  final IntersectionMetrics metrics;
  final List<TrafficPhase> phases;
  final List<String> connectedIntersections;
  final List<Camera> cameras;

  IntersectionData({
    required this.id,
    required this.name,
    required this.latitude,
    required this.longitude,
    required this.status,
    required this.lastUpdate,
    required this.configuration,
    required this.metrics,
    required this.phases,
    required this.connectedIntersections,
    required this.cameras,
  });

  // Add convenience getter for location
  LatLngPosition get location => LatLngPosition(latitude: latitude, longitude: longitude);

  factory IntersectionData.fromJson(Map<String, dynamic> json) {
    return IntersectionData(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      latitude: (json['latitude'] ?? 0.0).toDouble(),
      longitude: (json['longitude'] ?? 0.0).toDouble(),
      status: json['status'] ?? 'offline',
      lastUpdate: DateTime.tryParse(json['lastUpdate'] ?? '') ?? DateTime.now(),
      configuration: Map<String, dynamic>.from(json['configuration'] ?? {}),
      metrics: IntersectionMetrics.fromJson(json['metrics'] ?? {}),
      phases: (json['phases'] as List<dynamic>? ?? [])
          .map((phase) => TrafficPhase.fromJson(phase))
          .toList(),
      connectedIntersections: List<String>.from(json['connectedIntersections'] ?? []),
      cameras: (json['cameras'] as List<dynamic>? ?? [])
          .map((camera) => Camera.fromJson(camera))
          .toList(),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'latitude': latitude,
      'longitude': longitude,
      'status': status,
      'lastUpdate': lastUpdate.toIso8601String(),
      'configuration': configuration,
      'metrics': metrics.toJson(),
      'phases': phases.map((phase) => phase.toJson()).toList(),
      'connectedIntersections': connectedIntersections,
      'cameras': cameras.map((camera) => camera.toJson()).toList(),
    };
  }

  IntersectionData copyWith({
    String? id,
    String? name,
    double? latitude,
    double? longitude,
    String? status,
    DateTime? lastUpdate,
    Map<String, dynamic>? configuration,
    IntersectionMetrics? metrics,
    List<TrafficPhase>? phases,
    List<String>? connectedIntersections,
    List<Camera>? cameras,
  }) {
    return IntersectionData(
      id: id ?? this.id,
      name: name ?? this.name,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      status: status ?? this.status,
      lastUpdate: lastUpdate ?? this.lastUpdate,
      configuration: configuration ?? this.configuration,
      metrics: metrics ?? this.metrics,
      phases: phases ?? this.phases,
      connectedIntersections: connectedIntersections ?? this.connectedIntersections,
      cameras: cameras ?? this.cameras,
    );
  }

  bool get isOnline => status == 'online';
  bool get isOffline => status == 'offline';
  bool get isTraining => status == 'training';
  bool get hasIssues => status == 'error' || status == 'warning';
  
  // Convenience getters for UI
  double get currentQueueLength => metrics.averageQueueLength;
  double get averageWaitTime => metrics.averageWaitTime;
  double get performanceScore => metrics.efficiency;
  int get totalEpisodes => configuration['totalEpisodes'] ?? 0;
  DateTime get lastUpdated => lastUpdate;
}

class IntersectionMetrics {
  final double averageWaitTime;
  final double averageQueueLength;
  final int vehicleCount;
  final double throughput;
  final double efficiency;
  final List<double> waitTimes;
  final List<double> queueLengths;
  final DateTime timestamp;

  IntersectionMetrics({
    required this.averageWaitTime,
    required this.averageQueueLength,
    required this.vehicleCount,
    required this.throughput,
    required this.efficiency,
    required this.waitTimes,
    required this.queueLengths,
    required this.timestamp,
  });

  factory IntersectionMetrics.fromJson(Map<String, dynamic> json) {
    return IntersectionMetrics(
      averageWaitTime: (json['averageWaitTime'] ?? 0.0).toDouble(),
      averageQueueLength: (json['averageQueueLength'] ?? 0.0).toDouble(),
      vehicleCount: json['vehicleCount'] ?? 0,
      throughput: (json['throughput'] ?? 0.0).toDouble(),
      efficiency: (json['efficiency'] ?? 0.0).toDouble(),
      waitTimes: List<double>.from(json['waitTimes'] ?? []),
      queueLengths: List<double>.from(json['queueLengths'] ?? []),
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'averageWaitTime': averageWaitTime,
      'averageQueueLength': averageQueueLength,
      'vehicleCount': vehicleCount,
      'throughput': throughput,
      'efficiency': efficiency,
      'waitTimes': waitTimes,
      'queueLengths': queueLengths,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  IntersectionMetrics copyWith({
    double? averageWaitTime,
    double? averageQueueLength,
    int? vehicleCount,
    double? throughput,
    double? efficiency,
    List<double>? waitTimes,
    List<double>? queueLengths,
    DateTime? timestamp,
  }) {
    return IntersectionMetrics(
      averageWaitTime: averageWaitTime ?? this.averageWaitTime,
      averageQueueLength: averageQueueLength ?? this.averageQueueLength,
      vehicleCount: vehicleCount ?? this.vehicleCount,
      throughput: throughput ?? this.throughput,
      efficiency: efficiency ?? this.efficiency,
      waitTimes: waitTimes ?? this.waitTimes,
      queueLengths: queueLengths ?? this.queueLengths,
      timestamp: timestamp ?? this.timestamp,
    );
  }
}

class TrafficPhase {
  final String id;
  final String name;
  final List<String> directions;
  final int duration;
  final bool isActive;
  final int yellowTime;
  final int redTime;
  final Map<String, dynamic> configuration;

  TrafficPhase({
    required this.id,
    required this.name,
    required this.directions,
    required this.duration,
    required this.isActive,
    required this.yellowTime,
    required this.redTime,
    required this.configuration,
  });

  factory TrafficPhase.fromJson(Map<String, dynamic> json) {
    return TrafficPhase(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      directions: List<String>.from(json['directions'] ?? []),
      duration: json['duration'] ?? 30,
      isActive: json['isActive'] ?? false,
      yellowTime: json['yellowTime'] ?? 3,
      redTime: json['redTime'] ?? 2,
      configuration: Map<String, dynamic>.from(json['configuration'] ?? {}),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'directions': directions,
      'duration': duration,
      'isActive': isActive,
      'yellowTime': yellowTime,
      'redTime': redTime,
      'configuration': configuration,
    };
  }

  TrafficPhase copyWith({
    String? id,
    String? name,
    List<String>? directions,
    int? duration,
    bool? isActive,
    int? yellowTime,
    int? redTime,
    Map<String, dynamic>? configuration,
  }) {
    return TrafficPhase(
      id: id ?? this.id,
      name: name ?? this.name,
      directions: directions ?? this.directions,
      duration: duration ?? this.duration,
      isActive: isActive ?? this.isActive,
      yellowTime: yellowTime ?? this.yellowTime,
      redTime: redTime ?? this.redTime,
      configuration: configuration ?? this.configuration,
    );
  }
} 