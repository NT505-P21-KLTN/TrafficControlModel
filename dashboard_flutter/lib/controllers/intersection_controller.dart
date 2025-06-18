import 'package:get/get.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../models/intersection_data.dart';
import '../services/api_service.dart';

class IntersectionController extends GetxController {
  final RxBool isLoading = false.obs;
  final RxList<IntersectionData> intersections = <IntersectionData>[].obs;
  final RxString selectedIntersectionId = ''.obs;
  final Rx<IntersectionData?> selectedIntersection = Rx<IntersectionData?>(null);
  
  // Filter properties
  final RxString searchQuery = ''.obs;
  final RxString selectedStatus = ''.obs;
  final RxBool showPerformanceIssues = false.obs;
  final RxBool showRecentlyUpdated = false.obs;
  final RxBool showHighTraffic = false.obs;

  @override
  void onInit() {
    super.onInit();
    loadIntersections();
  }

  Future<void> loadIntersections() async {
    isLoading.value = true;
    try {
      final data = await ApiService.getIntersections();
      intersections.value = data;
    } catch (e) {
      print('Error loading intersections: $e');
      Get.snackbar('Error', 'Failed to load intersections: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> addIntersection(Map<String, dynamic> intersectionData) async {
    isLoading.value = true;
    try {
      final success = await ApiService.addIntersection(intersectionData);
      if (success) {
        Get.snackbar('Success', 'Intersection added successfully');
        await loadIntersections();
      } else {
        Get.snackbar('Error', 'Failed to add intersection');
      }
    } catch (e) {
      Get.snackbar('Error', 'Error adding intersection: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> removeIntersection(String id) async {
    isLoading.value = true;
    try {
      final success = await ApiService.deleteIntersection(id);
      if (success) {
        Get.snackbar('Success', 'Intersection removed successfully');
        await loadIntersections();
        if (selectedIntersectionId.value == id) {
          selectedIntersectionId.value = '';
          selectedIntersection.value = null;
        }
      } else {
        Get.snackbar('Error', 'Failed to remove intersection');
      }
    } catch (e) {
      Get.snackbar('Error', 'Error removing intersection: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> updateIntersectionLocation(String id, LatLng newPosition) async {
    try {
      final success = await ApiService.updateIntersectionPosition(
        id, 
        newPosition.latitude, 
        newPosition.longitude
      );
      if (success) {
        Get.snackbar('Success', 'Intersection position updated successfully');
        await loadIntersections();
      } else {
        Get.snackbar('Error', 'Failed to update intersection position');
      }
    } catch (e) {
      Get.snackbar('Error', 'Error updating position: $e');
    }
  }

  Future<void> updateIntersectionConfig(String id, Map<String, dynamic> config) async {
    try {
      final success = await ApiService.updateIntersection(id, config);
      if (success) {
        Get.snackbar('Success', 'Configuration updated successfully');
        await loadIntersections();
      } else {
        Get.snackbar('Error', 'Failed to update configuration');
      }
    } catch (e) {
      Get.snackbar('Error', 'Error updating configuration: $e');
    }
  }

  Future<void> updateIntersectionCameras(String id, List<Camera> cameras) async {
    try {
      final cameraData = cameras.map((camera) => camera.toJson()).toList();
      final success = await ApiService.updateIntersectionCameras(id, cameraData);
      if (success) {
        Get.snackbar('Success', 'Camera configuration updated successfully');
        await loadIntersections();
      } else {
        Get.snackbar('Error', 'Failed to update camera configuration');
      }
    } catch (e) {
      Get.snackbar('Error', 'Error updating cameras: $e');
    }
  }

  void selectIntersection(String id) {
    selectedIntersectionId.value = id;
    selectedIntersection.value = intersections.firstWhereOrNull((i) => i.id == id);
  }

  List<IntersectionData> getFilteredIntersections(String status) {
    switch (status.toLowerCase()) {
      case 'online':
        return intersections.where((i) => i.isOnline).toList();
      case 'offline':
        return intersections.where((i) => i.isOffline).toList();
      case 'training':
        return intersections.where((i) => i.isTraining).toList();
      case 'issues':
        return intersections.where((i) => i.hasIssues).toList();
      default:
        return intersections.toList();
    }
  }

  // Computed filtered intersections
  List<IntersectionData> get filteredIntersections {
    var filtered = intersections.toList();
    
    // Apply search filter
    if (searchQuery.value.isNotEmpty) {
      filtered = filtered.where((i) => 
        i.name.toLowerCase().contains(searchQuery.value.toLowerCase()) ||
        i.id.toLowerCase().contains(searchQuery.value.toLowerCase())
      ).toList();
    }
    
    // Apply status filter
    if (selectedStatus.value.isNotEmpty) {
      filtered = getFilteredIntersections(selectedStatus.value);
    }
    
    // Apply other filters
    if (showPerformanceIssues.value) {
      filtered = filtered.where((i) => i.performanceScore < 0.7).toList();
    }
    
    if (showRecentlyUpdated.value) {
      final oneHourAgo = DateTime.now().subtract(const Duration(hours: 1));
      filtered = filtered.where((i) => i.lastUpdate.isAfter(oneHourAgo)).toList();
    }
    
    if (showHighTraffic.value) {
      filtered = filtered.where((i) => i.currentQueueLength > 5.0).toList();
    }
    
    return filtered;
  }

  // Filter methods
  void setSearchQuery(String query) => searchQuery.value = query;
  void setStatusFilter(String status) => selectedStatus.value = status;
  void togglePerformanceFilter(bool value) => showPerformanceIssues.value = value;
  void toggleRecentFilter(bool value) => showRecentlyUpdated.value = value;
  void toggleTrafficFilter(bool value) => showHighTraffic.value = value;

  // Statistics methods
  int getOnlineCount() => intersections.where((i) => i.isOnline).length;
  int getTrainingCount() => intersections.where((i) => i.isTraining).length;
  int getOfflineCount() => intersections.where((i) => i.isOffline).length;
  
  double getOnlineTrend() => 0.0; // Mock trend data
  double getTrainingTrend() => 0.0; // Mock trend data
  double getOfflineTrend() => 0.0; // Mock trend data

  // CRUD operations
  Future<void> refreshData() => loadIntersections();
  
  Future<void> createIntersection(Map<String, dynamic> data) async {
    await addIntersection(data);
  }
  
  Future<void> updateIntersection(String id, Map<String, dynamic> data) async {
    await updateIntersectionConfig(id, data);
  }
  
  Future<void> deleteIntersection(String id) async {
    await removeIntersection(id);
  }

  Future<void> loadMockData() async {
    isLoading.value = true;
    try {
      // Clear current intersections
      intersections.clear();
      
      // Load mock data based on intersection agent configurations
      final mockIntersections = [
        {
          'id': 'agent1',
          'name': 'Dien Bien Phu - Hai Ba Trung',
          'location': {'lat': 10.786519, 'lng': 106.693680},
          'status': 'online',
        },
        {
          'id': 'agent2', 
          'name': 'Dien Bien Phu - Dinh Tien Hoang',
          'location': {'lat': 10.799418, 'lng': 106.694178},
          'status': 'online',
        },
        {
          'id': 'agent3',
          'name': 'Hai Ba Trung - Nguyen Thi Minh Khai', 
          'location': {'lat': 10.782851, 'lng': 106.698079},
          'status': 'offline',
        },
        {
          'id': 'agent4',
          'name': 'Nguyen Thi Minh Khai - Dinh Tien Hoang',
          'location': {'lat': 10.786750, 'lng': 106.701765}, 
          'status': 'training',
        },
      ];
      
      // Add each mock intersection
      for (final mockData in mockIntersections) {
        addSampleIntersection(mockData);
      }
      
      Get.snackbar('Success', 'Mock data loaded with ${mockIntersections.length} intersections');
    } catch (e) {
      Get.snackbar('Error', 'Failed to load mock data: $e');
    } finally {
      isLoading.value = false;
    }
  }

  // Sample data generation for testing
  void addSampleIntersection(Map<String, dynamic> data) {
    final intersection = IntersectionData(
      id: data['id'],
      name: data['name'],
      latitude: data['location']['lat'],
      longitude: data['location']['lng'],
      status: data['status'],
      lastUpdate: DateTime.now(),
      configuration: {},
      metrics: IntersectionMetrics(
        averageWaitTime: 30.0,
        averageQueueLength: 5.0,
        vehicleCount: 50,
        throughput: 100.0,
        efficiency: 0.85,
        waitTimes: List.generate(24, (i) => 20.0 + (i % 10)),
        queueLengths: List.generate(24, (i) => 3.0 + (i % 5)),
        timestamp: DateTime.now(),
      ),
      phases: [],
      connectedIntersections: [],
      cameras: [
        Camera(
          id: '${data['id']}_cam_N',
          direction: 'north',
          latitude: data['location']['lat'] + 0.0008,
          longitude: data['location']['lng'],
          range: 200.0,
          active: true,
        ),
        Camera(
          id: '${data['id']}_cam_E',
          direction: 'east',
          latitude: data['location']['lat'],
          longitude: data['location']['lng'] + 0.0008,
          range: 200.0,
          active: true,
        ),
        Camera(
          id: '${data['id']}_cam_S',
          direction: 'south',
          latitude: data['location']['lat'] - 0.0008,
          longitude: data['location']['lng'],
          range: 200.0,
          active: true,
        ),
        Camera(
          id: '${data['id']}_cam_W',
          direction: 'west',
          latitude: data['location']['lat'],
          longitude: data['location']['lng'] - 0.0008,
          range: 200.0,
          active: true,
        ),
      ],
    );
    
    intersections.add(intersection);
  }
} 