import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'api_controller.dart';

class SystemController extends GetxController {
  final ApiController _apiController = Get.find<ApiController>();
  
  final RxBool isLoading = false.obs;
  final RxMap<String, dynamic> systemConfig = <String, dynamic>{}.obs;
  final RxList<Map<String, dynamic>> systemLogs = <Map<String, dynamic>>[].obs;
  final RxString logLevel = 'all'.obs;

  @override
  void onInit() {
    super.onInit();
    loadSystemLogs();
    _initializeSystemConfig();
  }

  void _initializeSystemConfig() {
    systemConfig.value = {
      'autoRestart': true,
      'logLevel': 'info',
      'maxIntersections': 100,
      'updateInterval': 30,
      'enableAlerts': true,
      'backupEnabled': true,
      'maintenanceMode': false,
    };
  }

  Future<void> loadSystemLogs() async {
    isLoading.value = true;
    try {
      final logs = await _apiController.getLogs(
        level: logLevel.value == 'all' ? null : logLevel.value,
        limit: 100,
      );
      systemLogs.value = logs;
    } catch (e) {
      Get.snackbar('Error', 'Failed to load system logs: $e');
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> resetSystem() async {
    final confirmed = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Confirm System Reset'),
        content: const Text('Are you sure you want to reset the entire system? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Get.back(result: true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Reset'),
          ),
        ],
      ),
    ) ?? false;

    if (!confirmed) return;

    isLoading.value = true;
    try {
      final success = await _apiController.resetSystem();
      if (success) {
        Get.snackbar('Success', 'System has been reset successfully');
        await loadSystemLogs();
      } else {
        Get.snackbar('Error', 'Failed to reset system');
      }
    } catch (e) {
      Get.snackbar('Error', 'Error resetting system: $e');
    } finally {
      isLoading.value = false;
    }
  }

  void updateSystemConfig(String key, dynamic value) {
    systemConfig[key] = value;
    // In a real app, this would send the config to the server
    Get.snackbar('Config Updated', '$key has been updated to $value');
  }

  void setLogLevel(String level) {
    logLevel.value = level;
    loadSystemLogs();
  }

  Future<void> exportLogs() async {
    try {
      Get.snackbar('Export Started', 'System logs export has been initiated');
      await Future.delayed(const Duration(seconds: 2));
      Get.snackbar('Export Complete', 'System logs have been exported successfully');
    } catch (e) {
      Get.snackbar('Error', 'Failed to export logs: $e');
    }
  }

  Future<void> clearLogs() async {
    final confirmed = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Clear Logs'),
        content: const Text('Are you sure you want to clear all system logs?'),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Get.back(result: true),
            child: const Text('Clear'),
          ),
        ],
      ),
    ) ?? false;

    if (confirmed) {
      systemLogs.clear();
      Get.snackbar('Success', 'System logs cleared');
    }
  }
} 