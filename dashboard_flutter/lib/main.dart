import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:responsive_framework/responsive_framework.dart';

import 'controllers/api_controller.dart';
import 'controllers/dashboard_controller.dart';
import 'controllers/intersection_controller.dart';
import 'controllers/analytics_controller.dart';
import 'controllers/system_controller.dart';
import 'controllers/realtime_controller.dart';

import 'screens/login/login_screen.dart';
import 'screens/main_layout.dart';

import 'services/theme_service.dart';
import 'services/auth_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize services
  Get.put(AuthService());
  Get.put(ThemeService());
  
  // Initialize controllers
  Get.put(ApiController());
  Get.put(DashboardController());
  Get.put(IntersectionController());
  Get.put(AnalyticsController());
  Get.put(SystemController());
  Get.put(RealtimeController());
  
  runApp(const TrafficControlApp());
}

class TrafficControlApp extends StatelessWidget {
  const TrafficControlApp({super.key});

  @override
  Widget build(BuildContext context) {
    return GetBuilder<ThemeService>(
      builder: (themeService) {
        return GetMaterialApp(
          title: 'Traffic Control Dashboard',
          debugShowCheckedModeBanner: false,
          theme: _buildTheme(false),
          darkTheme: _buildTheme(true),
          themeMode: themeService.themeMode,
          builder: (context, child) {
            return ResponsiveBreakpoints.builder(
              child: child!,
              breakpoints: [
                const Breakpoint(start: 0, end: 450, name: MOBILE),
                const Breakpoint(start: 451, end: 800, name: TABLET),
                const Breakpoint(start: 801, end: 1920, name: DESKTOP),
                const Breakpoint(start: 1921, end: double.infinity, name: '4K'),
              ],
            );
          },
          initialRoute: '/login',
          getPages: _buildRoutes(),
          unknownRoute: GetPage(
            name: '/unknown',
            page: () => const Scaffold(
              body: Center(
                child: Text(
                  '404 - Page Not Found',
                  style: TextStyle(fontSize: 24),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  ThemeData _buildTheme(bool isDark) {
    // Simplified color scheme
    final colorScheme = isDark
        ? const ColorScheme.dark(
            primary: Color(0xFF007AFF),
            secondary: Color(0xFF34C759),
            tertiary: Color(0xFFFF9500),
            surface: Color(0xFF1C1C1E),
            background: Color(0xFF000000),
            error: Color(0xFFFF453A),
          )
        : const ColorScheme.light(
            primary: Color(0xFF007AFF),
            secondary: Color(0xFF34C759),
            tertiary: Color(0xFFFF9500),
            surface: Color(0xFFFFFFFF),
            background: Color(0xFFF2F2F7),
            error: Color(0xFFFF3B30),
          );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      fontFamily: null, // Use system fonts
      appBarTheme: AppBarTheme(
        elevation: 0,
        centerTitle: false,
        backgroundColor: colorScheme.background,
        foregroundColor: colorScheme.onBackground,
        titleTextStyle: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.bold,
          color: colorScheme.onBackground,
        ),
      ),
      cardTheme: CardTheme(
        elevation: 2,
        color: colorScheme.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: colorScheme.primary,
          foregroundColor: colorScheme.onPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colorScheme.primary,
          side: BorderSide(color: colorScheme.primary),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
      ),
      visualDensity: VisualDensity.standard,
    );
  }

  List<GetPage> _buildRoutes() {
    return [
      GetPage(
        name: '/login',
        page: () => const LoginScreen(),
      ),
      GetPage(
        name: '/',
        page: () => const MainLayout(),
        middlewares: [AuthMiddleware()],
      ),
      GetPage(
        name: '/dashboard',
        page: () => const MainLayout(),
        middlewares: [AuthMiddleware()],
      ),
      GetPage(
        name: '/intersections',
        page: () => const MainLayout(),
        middlewares: [AuthMiddleware()],
      ),
      GetPage(
        name: '/training',
        page: () => const MainLayout(),
        middlewares: [AuthMiddleware()],
      ),
    ];
  }
}

class AuthMiddleware extends GetMiddleware {
  @override
  RouteSettings? redirect(String? route) {
    final authService = Get.find<AuthService>();
    if (!authService.isAuthenticated) {
      return const RouteSettings(name: '/login');
    }
    return null;
  }
} 