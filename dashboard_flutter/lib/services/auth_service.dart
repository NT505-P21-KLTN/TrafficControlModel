import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService with ChangeNotifier {
  bool _isAuthenticated = false;
  String? _userRole;
  String? _userName;
  String? _token;

  bool get isAuthenticated => _isAuthenticated;
  String? get userRole => _userRole;
  String? get userName => _userName;
  String? get token => _token;

  AuthService() {
    _loadAuthState();
  }

  Future<void> _loadAuthState() async {
    final prefs = await SharedPreferences.getInstance();
    _isAuthenticated = prefs.getBool('isAuthenticated') ?? false;
    _userRole = prefs.getString('userRole');
    _userName = prefs.getString('userName');
    _token = prefs.getString('token');
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    // Simple authentication for demo purposes
    // In production, this would connect to your actual auth system
    if (username.isNotEmpty && password.isNotEmpty) {
      _isAuthenticated = true;
      _userName = username;
      _userRole = username == 'admin' ? 'admin' : 'operator';
      _token = 'demo_token_${DateTime.now().millisecondsSinceEpoch}';
      
      await _saveAuthState();
      notifyListeners();
      return true;
    }
    return false;
  }

  Future<void> logout() async {
    _isAuthenticated = false;
    _userName = null;
    _userRole = null;
    _token = null;
    
    await _clearAuthState();
    notifyListeners();
  }

  Future<void> _saveAuthState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('isAuthenticated', _isAuthenticated);
    if (_userRole != null) await prefs.setString('userRole', _userRole!);
    if (_userName != null) await prefs.setString('userName', _userName!);
    if (_token != null) await prefs.setString('token', _token!);
  }

  Future<void> _clearAuthState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('isAuthenticated');
    await prefs.remove('userRole');
    await prefs.remove('userName');
    await prefs.remove('token');
  }

  bool hasPermission(String permission) {
    if (!_isAuthenticated) return false;
    
    switch (permission) {
      case 'admin':
        return _userRole == 'admin';
      case 'manage_intersections':
        return _userRole == 'admin' || _userRole == 'operator';
      case 'view_analytics':
        return true; // All authenticated users can view analytics
      case 'system_config':
        return _userRole == 'admin';
      case 'training_control':
        return _userRole == 'admin';
      default:
        return false;
    }
  }
} 