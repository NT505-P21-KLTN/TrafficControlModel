import 'package:get/get.dart';
import 'package:dio/dio.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';
import 'dart:async';

import '../models/intersection_data.dart';
import '../models/system_status.dart';
import '../models/analytics_data.dart';

class ApiController extends GetxController {
  late Dio _dio;
  WebSocketChannel? _wsChannel;
  Timer? _heartbeatTimer;
  
  // Reactive variables for real-time data
  final RxBool isConnected = false.obs;
  final RxString baseUrl = 'http://localhost:5001'.obs;
  final RxMap<String, IntersectionData> intersections = <String, IntersectionData>{}.obs;
  final RxMap<String, dynamic> systemStatus = <String, dynamic>{}.obs;
  final RxList<dynamic> realtimeEvents = <dynamic>[].obs;
  
  // Emergency disable option for WebSocket
  final bool _enableWebSocket = false; // Set to false to disable WebSocket entirely
  
  // Data streams
  final StreamController<Map<String, dynamic>> _dataStreamController = 
      StreamController<Map<String, dynamic>>.broadcast();
  
  Stream<Map<String, dynamic>> get dataStream => _dataStreamController.stream;

  int _reconnectAttempts = 0;

  @override
  void onInit() {
    super.onInit();
    _initializeDio();
    if (_enableWebSocket) {
      _connectWebSocket();
    } else {
      // Work in offline mode
      isConnected.value = false;
    }
    _startHeartbeat();
  }

  @override
  void onClose() {
    _heartbeatTimer?.cancel();
    _wsChannel?.sink.close();
    _dataStreamController.close();
    super.onClose();
  }

  void _initializeDio() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl.value,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {
        'Content-Type': 'application/json',
      },
    ));

    // Add interceptors for logging and error handling
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      // logPrint: (object) => print('[API] $object'),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onError: (error, handler) {
        // print('[API ERROR] ${error.message}');
        _handleApiError(error);
        handler.next(error);
      },
    ));
  }

  void _connectWebSocket() {
    // Skip WebSocket connection if we're in demo mode or backend is unavailable
    if (!isConnected.value && _reconnectAttempts > 2) {
      // print('[WebSocket] Max reconnect attempts reached, working in offline mode');
      return;
    }

    // Make WebSocket connection completely async and non-blocking
    Future.delayed(Duration.zero, () async {
      try {
        final wsUrl = baseUrl.value.replaceFirst('http', 'ws') + '/ws';
        _wsChannel = WebSocketChannel.connect(
          Uri.parse(wsUrl),
          protocols: ['echo-protocol'],
        );
        
        _wsChannel!.stream.listen(
          (data) {
            if (data != null) {
              try {
                final parsed = json.decode(data);
                _handleWebSocketMessage(parsed);
                _reconnectAttempts = 0; // Reset attempts on successful connection
                isConnected.value = true;
              } catch (e) {
                // Ignore JSON parsing errors
              }
            }
          },
          onError: (error) {
            // print('[WebSocket Error] $error');
            isConnected.value = false;
            _wsChannel?.sink.close();
            _reconnectAttempts++;
            if (_reconnectAttempts <= 2) {
              _scheduleReconnect();
            }
          },
          onDone: () {
            // print('[WebSocket] Connection closed');
            isConnected.value = false;
            _reconnectAttempts++;
            if (_reconnectAttempts <= 2) {
              _scheduleReconnect();
            }
          },
          cancelOnError: true,
        );
        
        // Test connection with a small timeout
        Timer(const Duration(seconds: 3), () {
          if (_wsChannel != null) {
            isConnected.value = true;
            _reconnectAttempts = 0;
            // print('[WebSocket] Connected successfully');
          }
        });
        
      } catch (e) {
        // print('[WebSocket] Connection failed: $e');
        isConnected.value = false;
        _reconnectAttempts++;
        if (_reconnectAttempts <= 2) {
          _scheduleReconnect();
        }
      }
    });
  }

  void _scheduleReconnect() {
    // Use exponential backoff for reconnection but don't block UI
    final delay = Duration(seconds: 10 + (_reconnectAttempts * 10));
    Timer(delay, () {
      if (!isConnected.value && _reconnectAttempts <= 2) {
        _connectWebSocket();
      }
    });
  }

  void _handleWebSocketMessage(Map<String, dynamic> message) {
    switch (message['type']) {
      case 'intersection_update':
        _updateIntersectionData(message['data']);
        break;
      case 'system_status':
        systemStatus.value = message['data'];
        break;
      case 'realtime_event':
        realtimeEvents.add(message['data']);
        if (realtimeEvents.length > 100) {
          realtimeEvents.removeAt(0);
        }
        break;
    }
    
    _dataStreamController.add(message);
  }

  void _updateIntersectionData(Map<String, dynamic> data) {
    final intersection = IntersectionData.fromJson(data);
    intersections[intersection.id] = intersection;
  }

  void _startHeartbeat() {
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      checkConnection();
    });
  }

  void _handleApiError(DioException error) {
    String message = 'Unknown error occurred';
    
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        message = 'Connection timeout';
        break;
      case DioExceptionType.receiveTimeout:
        message = 'Receive timeout';
        break;
      case DioExceptionType.badResponse:
        message = 'Server error: ${error.response?.statusCode}';
        break;
      case DioExceptionType.connectionError:
        message = 'Connection error';
        isConnected.value = false;
        break;
      default:
        message = error.message ?? 'Unknown error';
    }
    
    Get.snackbar(
      'API Error',
      message,
      snackPosition: SnackPosition.BOTTOM,
      duration: const Duration(seconds: 3),
    );
  }

  // API Methods
  Future<SystemStatus?> getSystemStatus() async {
    try {
      final response = await _dio.get('/api/status');
      return SystemStatus.fromJson(response.data);
    } catch (e) {
      // print('[API] Error getting system status: $e');
      return null;
    }
  }

  Future<List<IntersectionData>> getIntersections() async {
    try {
      final response = await _dio.get('/api/data');
      final List<dynamic> data = response.data['intersections'] ?? [];
      return data.map((json) => IntersectionData.fromJson(json)).toList();
    } catch (e) {
      // print('[API] Error getting intersections: $e');
      return [];
    }
  }

  Future<IntersectionData?> getIntersection(String id) async {
    try {
      final response = await _dio.get('/api/agent/$id');
      return IntersectionData.fromJson(response.data);
    } catch (e) {
      // print('[API] Error getting intersection $id: $e');
      return null;
    }
  }

  Future<bool> updateIntersectionConfig(String id, Map<String, dynamic> config) async {
    try {
      await _dio.post('/api/agent/$id/config', data: config);
      return true;
    } catch (e) {
      // print('[API] Error updating intersection config: $e');
      return false;
    }
  }

  Future<bool> addIntersection(Map<String, dynamic> intersectionData) async {
    try {
      await _dio.post('/api/intersections', data: intersectionData);
      return true;
    } catch (e) {
      // print('[API] Error adding intersection: $e');
      return false;
    }
  }

  Future<bool> removeIntersection(String id) async {
    try {
      await _dio.delete('/api/agent/$id');
      return true;
    } catch (e) {
      // print('[API] Error removing intersection: $e');
      return false;
    }
  }

  Future<AnalyticsData?> getAnalytics({
    DateTime? startDate,
    DateTime? endDate,
    String? intersectionId,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (startDate != null) queryParams['start'] = startDate.toIso8601String();
      if (endDate != null) queryParams['end'] = endDate.toIso8601String();
      if (intersectionId != null) queryParams['intersection'] = intersectionId;

      final response = await _dio.get('/api/analytics', queryParameters: queryParams);
      return AnalyticsData.fromJson(response.data);
    } catch (e) {
      // print('[API] Error getting analytics: $e');
      return null;
    }
  }

  Future<List<Map<String, dynamic>>> getLogs({
    String? level,
    String? intersectionId,
    int limit = 100,
  }) async {
    try {
      final queryParams = <String, dynamic>{'limit': limit};
      if (level != null) queryParams['level'] = level;
      if (intersectionId != null) queryParams['intersection'] = intersectionId;

      final response = await _dio.get('/api/logs', queryParameters: queryParams);
      return List<Map<String, dynamic>>.from(response.data['logs'] ?? []);
    } catch (e) {
      // print('[API] Error getting logs: $e');
      return [];
    }
  }

  Future<bool> startTraining(String intersectionId, Map<String, dynamic> params) async {
    try {
      await _dio.post('/api/training/start', data: {
        'intersection_id': intersectionId,
        'parameters': params,
      });
      return true;
    } catch (e) {
      // print('[API] Error starting training: $e');
      return false;
    }
  }

  Future<bool> stopTraining(String intersectionId) async {
    try {
      await _dio.post('/api/training/stop', data: {
        'intersection_id': intersectionId,
      });
      return true;
    } catch (e) {
      // print('[API] Error stopping training: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getTrainingStatus(String intersectionId) async {
    try {
      final response = await _dio.get('/api/training/status/$intersectionId');
      return response.data;
    } catch (e) {
      // print('[API] Error getting training status: $e');
      return null;
    }
  }

  Future<bool> resetSystem() async {
    try {
      await _dio.post('/api/reset');
      return true;
    } catch (e) {
      // print('[API] Error resetting system: $e');
      return false;
    }
  }

  Future<bool> checkConnection() async {
    try {
      final response = await _dio.get('/api/status');
      isConnected.value = response.statusCode == 200;
      return isConnected.value;
    } catch (e) {
      isConnected.value = false;
      return false;
    }
  }

  void updateBaseUrl(String newUrl) {
    baseUrl.value = newUrl;
    _dio.options.baseUrl = newUrl;
    _wsChannel?.sink.close();
    _connectWebSocket();
  }

  void sendWebSocketMessage(Map<String, dynamic> message) {
    if (_wsChannel != null && isConnected.value) {
      _wsChannel!.sink.add(json.encode(message));
    }
  }

  // New methods for intersection position and connection management
  Future<bool> updateIntersectionPosition(String intersectionId, double latitude, double longitude) async {
    try {
      await _dio.put('/api/intersections/$intersectionId/position', data: {
        'latitude': latitude,
        'longitude': longitude,
      });
      return true;
    } catch (e) {
      // print('[API] Error updating intersection position: $e');
      return false;
    }
  }

  Future<bool> updateIntersectionConnection(String sourceId, String targetId) async {
    try {
      await _dio.post('/api/intersections/$sourceId/connections', data: {
        'target_id': targetId,
      });
      return true;
    } catch (e) {
      // print('[API] Error updating intersection connection: $e');
      return false;
    }
  }

  Future<bool> removeIntersectionConnection(String sourceId, String targetId) async {
    try {
      await _dio.delete('/api/intersections/$sourceId/connections/$targetId');
      return true;
    } catch (e) {
      // print('[API] Error removing intersection connection: $e');
      return false;
    }
  }
} 