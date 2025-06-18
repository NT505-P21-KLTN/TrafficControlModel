import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/intersection_data.dart';

class ApiService {
  static const String baseUrl = 'http://localhost:5001'; // Use port 5001 to avoid conflicts
  
  // Get all intersections
  static Future<List<IntersectionData>> getIntersections() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/intersections'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final List<dynamic> intersections = data['intersections'] ?? [];
        
        return intersections.map((item) => IntersectionData.fromJson(item)).toList();
      } else {
        throw Exception('Failed to load intersections: ${response.statusCode}');
      }
    } catch (e) {
      print('Error loading intersections: $e');
      return [];
    }
  }
  
  // Add new intersection
  static Future<bool> addIntersection(Map<String, dynamic> intersectionData) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/intersections'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(intersectionData),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['status'] == 'success';
      }
      return false;
    } catch (e) {
      print('Error adding intersection: $e');
      return false;
    }
  }
  
  // Update intersection
  static Future<bool> updateIntersection(String intersectionId, Map<String, dynamic> intersectionData) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/api/intersections/$intersectionId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(intersectionData),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['status'] == 'success';
      }
      return false;
    } catch (e) {
      print('Error updating intersection: $e');
      return false;
    }
  }
  
  // Update intersection position
  static Future<bool> updateIntersectionPosition(String intersectionId, double latitude, double longitude) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/api/intersections/$intersectionId/position'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'latitude': latitude,
          'longitude': longitude,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['status'] == 'success';
      }
      return false;
    } catch (e) {
      print('Error updating intersection position: $e');
      return false;
    }
  }
  
  // Update intersection cameras
  static Future<bool> updateIntersectionCameras(String intersectionId, List<Map<String, dynamic>> cameras) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/api/intersections/$intersectionId/cameras'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'cameras': cameras}),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['status'] == 'success';
      }
      return false;
    } catch (e) {
      print('Error updating intersection cameras: $e');
      return false;
    }
  }
  
  // Delete intersection
  static Future<bool> deleteIntersection(String intersectionId) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/api/agent/$intersectionId'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['status'] == 'success';
      }
      return false;
    } catch (e) {
      print('Error deleting intersection: $e');
      return false;
    }
  }
  
  // Get server status
  static Future<Map<String, dynamic>?> getServerStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/status'),
        headers: {'Content-Type': 'application/json'},
      );
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      print('Error getting server status: $e');
      return null;
    }
  }
} 