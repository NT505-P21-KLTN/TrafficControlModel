import "package:flutter/material.dart";
import 'package:get/get.dart';
import 'package:responsive_framework/responsive_framework.dart';
import '../services/auth_service.dart';
import '../services/theme_service.dart';
import 'dashboard/dashboard_screen.dart';
import 'intersections/intersections_screen.dart';
import 'analytics/analytics_screen.dart';
import 'training/training_screen.dart';

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _selectedIndex = 0;

  final List<NavigationItem> _navigationItems = [
    NavigationItem(
      icon: Icons.dashboard,
      label: 'Dashboard',
      screen: const DashboardScreen(),
      requiredRole: null, // Available to all authenticated users
    ),
    NavigationItem(
      icon: Icons.traffic,
      label: 'Intersections',
      screen: const IntersectionsScreen(),
      requiredRole: null,
    ),
    NavigationItem(
      icon: Icons.analytics,
      label: 'Analytics',
      screen: const AnalyticsScreen(),
      requiredRole: null,
    ),
    NavigationItem(
      icon: Icons.model_training,
      label: 'Training',
      screen: const TrainingScreen(),
      requiredRole: 'admin', // Only admin can access training
    ),
  ];

  List<NavigationItem> _getAccessibleItems(AuthService authService) {
    return _navigationItems.where((item) {
      if (item.requiredRole == null) return true;
      return authService.userRole == item.requiredRole;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;

    return GetBuilder<AuthService>(
      builder: (authService) {
        return GetBuilder<ThemeService>(
          builder: (themeService) {
            final accessibleItems = _getAccessibleItems(authService);
            
            if (_selectedIndex >= accessibleItems.length) {
              _selectedIndex = 0;
            }

            return Scaffold(
              body: Row(
                children: [
                  // Side Navigation for Desktop/Tablet
                  if (!isMobile) _buildSideNavigation(context, authService, themeService, accessibleItems),
                  
                  // Main Content
                  Expanded(
                    child: Column(
                      children: [
                        // Top App Bar
                        _buildTopAppBar(context, themeService, accessibleItems),
                        
                        // Page Content
                        Expanded(
                          child: accessibleItems.isNotEmpty
                              ? IndexedStack(
                                  index: _selectedIndex,
                                  children: accessibleItems.map((item) => item.screen).toList(),
                                )
                              : const Center(child: Text('No accessible screens')),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              
              // Bottom Navigation for Mobile
              bottomNavigationBar: isMobile ? _buildBottomNavigation(context, accessibleItems) : null,
            );
          },
        );
      },
    );
  }

  Widget _buildSideNavigation(BuildContext context, AuthService authService, ThemeService themeService, List<NavigationItem> accessibleItems) {
    final isTablet = ResponsiveBreakpoints.of(context).isTablet;
    
    return Container(
      width: isTablet ? 72 : 280,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          right: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.3),
            width: 0.5, // Apple hairline border
          ),
        ),
      ),
      child: Column(
        children: [
          // Logo/Header with Apple spacing
          Container(
            height: 88, // Increased for Apple spacing
            padding: EdgeInsets.symmetric(
              horizontal: isTablet ? 16 : 20,
              vertical: 20,
            ),
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                  width: 0.5,
                ),
              ),
            ),
            child: Row(
              children: [
                // App icon with Apple-style design
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Theme.of(context).colorScheme.primary,
                        Theme.of(context).colorScheme.primary.withOpacity(0.8),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(12), // Apple icon radius
                    boxShadow: [
                      BoxShadow(
                        color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.traffic,
                    color: Colors.white,
                    size: 24,
                  ),
                ),
                if (!isTablet) ...[
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          'Traffic Control',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w700, // Apple bold
                          ),
                        ),
                        Text(
                          'Dashboard',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          
          // Navigation Items with Apple styling
          Expanded(
            child: Padding(
              padding: EdgeInsets.symmetric(
                horizontal: isTablet ? 8 : 16,
                vertical: 16,
              ),
              child: ListView.separated(
                itemCount: accessibleItems.length,
                separatorBuilder: (context, index) => const SizedBox(height: 4),
                itemBuilder: (context, index) {
                  final item = accessibleItems[index];
                  final isSelected = index == _selectedIndex;
                  
                  return Container(
                    height: 48, // Apple standard row height
                    decoration: BoxDecoration(
                      color: isSelected
                          ? Theme.of(context).colorScheme.primary.withOpacity(0.1)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(10), // Apple radius
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(10),
                        onTap: () {
                          setState(() {
                            _selectedIndex = index;
                          });
                        },
                        child: Padding(
                          padding: EdgeInsets.symmetric(
                            horizontal: isTablet ? 8 : 16,
                            vertical: 12,
                          ),
                          child: Row(
                            children: [
                              // Icon with Apple styling
                              Container(
                                width: 24,
                                height: 24,
                                alignment: Alignment.center,
                                child: Icon(
                                  item.icon,
                                  size: 20,
                                  color: isSelected
                                      ? Theme.of(context).colorScheme.primary
                                      : Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                ),
                              ),
                              if (!isTablet) ...[
                                const SizedBox(width: 16),
                                Expanded(
                                  child: Text(
                                    item.label,
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                      color: isSelected
                                          ? Theme.of(context).colorScheme.primary
                                          : Theme.of(context).colorScheme.onSurface,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          
          // User Profile Section with Apple design
          Container(
            padding: EdgeInsets.all(isTablet ? 8 : 16),
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(
                  color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                  width: 0.5,
                ),
              ),
            ),
            child: Column(
              children: [
                Divider(color: Theme.of(context).colorScheme.outline.withOpacity(0.2)),
                const SizedBox(height: 8),
                ListTile(
                  leading: CircleAvatar(
                    backgroundColor: Theme.of(context).colorScheme.primary.withOpacity(0.1),
                    child: Icon(
                      Icons.person,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                  title: isTablet ? null : Text(
                    authService.userName ?? 'User',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  subtitle: isTablet ? null : Text(
                    (authService.userRole ?? 'guest').toUpperCase(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  trailing: isTablet ? null : PopupMenuButton<String>(
                    onSelected: (value) => _handleUserMenuAction(value, authService),
                    itemBuilder: (context) => [
                      const PopupMenuItem(
                        value: 'profile',
                        child: ListTile(
                          leading: Icon(Icons.person),
                          title: Text('Profile'),
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                      const PopupMenuItem(
                        value: 'logout',
                        child: ListTile(
                          leading: Icon(Icons.logout),
                          title: Text('Logout'),
                          contentPadding: EdgeInsets.zero,
                        ),
                      ),
                    ],
                  ),
                  onTap: isTablet ? () => _handleUserMenuAction('profile', authService) : null,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomNavigation(BuildContext context, List<NavigationItem> accessibleItems) {
    return BottomNavigationBar(
      currentIndex: _selectedIndex,
      onTap: (index) {
        setState(() {
          _selectedIndex = index;
        });
      },
      type: BottomNavigationBarType.fixed,
      items: accessibleItems.map((item) => BottomNavigationBarItem(
        icon: Icon(item.icon),
        label: item.label,
      )).toList(),
    );
  }

  Widget _buildTopAppBar(BuildContext context, ThemeService themeService, List<NavigationItem> accessibleItems) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    final currentItem = accessibleItems.isNotEmpty ? accessibleItems[_selectedIndex] : null;
    
    return Container(
      height: 64,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
          ),
        ),
      ),
      child: Row(
        children: [
          // Page Title
          Expanded(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: isMobile ? 16 : 16),
              child: Text(
                currentItem?.label ?? 'Dashboard',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          
          // Theme Toggle
          IconButton(
            icon: Icon(
              themeService.isDarkMode ? Icons.light_mode : Icons.dark_mode,
            ),
            onPressed: themeService.toggleTheme,
          ),
          
          // User Menu (Mobile)
          if (isMobile)
            GetBuilder<AuthService>(
              builder: (authService) {
                return PopupMenuButton<String>(
                  onSelected: (value) => _handleUserMenuAction(value, authService),
                  itemBuilder: (context) => [
                    const PopupMenuItem(
                      value: 'profile',
                      child: ListTile(
                        leading: Icon(Icons.person),
                        title: Text('Profile'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'logout',
                      child: ListTile(
                        leading: Icon(Icons.logout),
                        title: Text('Logout'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }

  void _handleUserMenuAction(String action, AuthService authService) {
    switch (action) {
      case 'profile':
        // Show user profile
        break;
      case 'logout':
        authService.logout();
        Get.offAllNamed('/login');
        break;
    }
  }
}

class NavigationItem {
  final IconData icon;
  final String label;
  final Widget screen;
  final String? requiredRole;

  NavigationItem({
    required this.icon,
    required this.label,
    required this.screen,
    this.requiredRole,
  });
}
