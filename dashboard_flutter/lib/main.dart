import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:provider/provider.dart';
import 'package:responsive_framework/responsive_framework.dart';
import 'package:google_fonts/google_fonts.dart';

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
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: Get.find<ThemeService>()),
        ChangeNotifierProvider.value(value: Get.find<AuthService>()),
      ],
      child: Consumer<ThemeService>(
        builder: (context, themeService, child) {
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
      ),
    );
  }

  ThemeData _buildTheme(bool isDark) {
    // Apple Design System Colors
    final colorScheme = isDark
        ? const ColorScheme.dark(
            primary: Color(0xFF007AFF), // iOS Blue
            secondary: Color(0xFF34C759), // iOS Green
            tertiary: Color(0xFFFF9500), // iOS Orange
            surface: Color(0xFF1C1C1E), // iOS Dark Gray 2
            background: Color(0xFF000000), // iOS Black
            surfaceVariant: Color(0xFF2C2C2E), // iOS Dark Gray 3
            outline: Color(0xFF38383A), // iOS Dark Gray 4
            outlineVariant: Color(0xFF48484A), // iOS Dark Gray 5
            error: Color(0xFFFF453A), // iOS Red
            onPrimary: Colors.white,
            onSecondary: Colors.white,
            onSurface: Color(0xFFFFFFFF),
            onBackground: Color(0xFFFFFFFF),
            onError: Colors.white,
          )
        : const ColorScheme.light(
            primary: Color(0xFF007AFF), // iOS Blue
            secondary: Color(0xFF34C759), // iOS Green
            tertiary: Color(0xFFFF9500), // iOS Orange
            surface: Color(0xFFFFFFFF), // iOS White
            background: Color(0xFFF2F2F7), // iOS Gray 6
            surfaceVariant: Color(0xFFF2F2F7), // iOS Gray 6
            outline: Color(0xFFC7C7CC), // iOS Gray 4
            outlineVariant: Color(0xFFD1D1D6), // iOS Gray 3
            error: Color(0xFFFF3B30), // iOS Red
            onPrimary: Colors.white,
            onSecondary: Colors.white,
            onSurface: Color(0xFF000000),
            onBackground: Color(0xFF000000),
            onError: Colors.white,
          );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      // Use San Francisco font family for Apple design system
      fontFamily: '.SF Pro Display', // iOS system font
      textTheme: GoogleFonts.interTextTheme( // Inter is closest to SF Pro in Google Fonts
        isDark ? ThemeData.dark().textTheme : ThemeData.light().textTheme,
      ).copyWith(
        // Apple Typography Scale
        displayLarge: GoogleFonts.inter(
          fontSize: 34,
          fontWeight: FontWeight.w700, // Bold
          letterSpacing: 0.374,
          color: colorScheme.onBackground,
        ),
        displayMedium: GoogleFonts.inter(
          fontSize: 28,
          fontWeight: FontWeight.w700, // Bold
          letterSpacing: 0.364,
          color: colorScheme.onBackground,
        ),
        displaySmall: GoogleFonts.inter(
          fontSize: 22,
          fontWeight: FontWeight.w600, // Semibold
          letterSpacing: 0.352,
          color: colorScheme.onBackground,
        ),
        headlineLarge: GoogleFonts.inter(
          fontSize: 20,
          fontWeight: FontWeight.w600, // Semibold
          letterSpacing: 0.38,
          color: colorScheme.onBackground,
        ),
        headlineMedium: GoogleFonts.inter(
          fontSize: 17,
          fontWeight: FontWeight.w600, // Semibold
          letterSpacing: -0.408,
          color: colorScheme.onBackground,
        ),
        headlineSmall: GoogleFonts.inter(
          fontSize: 16,
          fontWeight: FontWeight.w600, // Semibold
          letterSpacing: -0.32,
          color: colorScheme.onBackground,
        ),
        titleLarge: GoogleFonts.inter(
          fontSize: 17,
          fontWeight: FontWeight.w600, // Semibold
          letterSpacing: -0.408,
          color: colorScheme.onBackground,
        ),
        titleMedium: GoogleFonts.inter(
          fontSize: 15,
          fontWeight: FontWeight.w500, // Medium
          letterSpacing: -0.24,
          color: colorScheme.onBackground,
        ),
        titleSmall: GoogleFonts.inter(
          fontSize: 13,
          fontWeight: FontWeight.w500, // Medium
          letterSpacing: -0.078,
          color: colorScheme.onBackground,
        ),
        bodyLarge: GoogleFonts.inter(
          fontSize: 17,
          fontWeight: FontWeight.w400, // Regular
          letterSpacing: -0.408,
          color: colorScheme.onBackground,
        ),
        bodyMedium: GoogleFonts.inter(
          fontSize: 15,
          fontWeight: FontWeight.w400, // Regular
          letterSpacing: -0.24,
          color: colorScheme.onBackground,
        ),
        bodySmall: GoogleFonts.inter(
          fontSize: 13,
          fontWeight: FontWeight.w400, // Regular
          letterSpacing: -0.078,
          color: colorScheme.onBackground,
        ),
        labelLarge: GoogleFonts.inter(
          fontSize: 15,
          fontWeight: FontWeight.w500, // Medium
          letterSpacing: -0.24,
          color: colorScheme.onBackground,
        ),
        labelMedium: GoogleFonts.inter(
          fontSize: 13,
          fontWeight: FontWeight.w500, // Medium
          letterSpacing: -0.078,
          color: colorScheme.onBackground,
        ),
        labelSmall: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w500, // Medium
          letterSpacing: 0.066,
          color: colorScheme.onBackground,
        ),
      ),
      appBarTheme: AppBarTheme(
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false, // Apple style left-aligned titles
        backgroundColor: colorScheme.background,
        surfaceTintColor: Colors.transparent,
        foregroundColor: colorScheme.onBackground,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 34,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.374,
          color: colorScheme.onBackground,
        ),
        toolbarHeight: 44, // iOS standard app bar height
      ),
      cardTheme: CardTheme(
        elevation: 0,
        color: colorScheme.surface,
        surfaceTintColor: Colors.transparent,
        shadowColor: isDark ? Colors.black45 : Colors.black12,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12), // Apple's standard corner radius
        ),
        margin: const EdgeInsets.all(8),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          backgroundColor: colorScheme.primary,
          foregroundColor: colorScheme.onPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8), // Apple button radius
          ),
          textStyle: GoogleFonts.inter(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.408,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: colorScheme.primary,
          side: BorderSide(color: colorScheme.primary, width: 1),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: GoogleFonts.inter(
            fontSize: 17,
            fontWeight: FontWeight.w600,
            letterSpacing: -0.408,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: colorScheme.primary,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: GoogleFonts.inter(
            fontSize: 17,
            fontWeight: FontWeight.w400,
            letterSpacing: -0.408,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceVariant,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10), // Apple input radius
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: colorScheme.error, width: 1),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: colorScheme.surfaceVariant,
        selectedColor: colorScheme.primary,
        labelStyle: GoogleFonts.inter(
          fontSize: 13,
          fontWeight: FontWeight.w500,
          letterSpacing: -0.078,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20), // Apple pill shape
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      listTileTheme: ListTileThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      dividerTheme: DividerThemeData(
        color: colorScheme.outline,
        thickness: 0.5, // Apple's hairline divider
        space: 1,
      ),
      dialogTheme: DialogTheme(
        backgroundColor: colorScheme.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 20,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14), // Apple modal radius
        ),
        titleTextStyle: GoogleFonts.inter(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.408,
          color: colorScheme.onSurface,
        ),
        contentTextStyle: GoogleFonts.inter(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          letterSpacing: -0.078,
          color: colorScheme.onSurface,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: colorScheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
        ),
        elevation: 20,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: colorScheme.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        height: 83, // iOS tab bar height
        labelTextStyle: MaterialStateProperty.all(
          GoogleFonts.inter(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.12,
          ),
        ),
      ),
      // Apple-style spacing and sizing
      visualDensity: VisualDensity.standard,
      splashFactory: NoSplash.splashFactory, // Remove material ripples for iOS feel
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