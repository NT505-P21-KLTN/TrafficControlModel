import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:responsive_framework/responsive_framework.dart';
import '../../controllers/dashboard_controller.dart';
import '../../controllers/realtime_controller.dart';
import '../../widgets/dashboard_widgets.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> with TickerProviderStateMixin {
  final DashboardController _dashboardController = Get.find<DashboardController>();
  final RealtimeController _realtimeController = Get.find<RealtimeController>();

  late AnimationController _animationController;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.background,
      body: _buildMainContent(context),
    );
  }

  Widget _buildMainContent(BuildContext context) {
    return Column(
      children: [
        _buildTopAppBar(context),
        Expanded(
          child: _buildDashboardContent(context),
        ),
      ],
    );
  }

  Widget _buildTopAppBar(BuildContext context) {
    return Container(
      height: 80,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
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
          if (!ResponsiveBreakpoints.of(context).isDesktop)
            IconButton(
              icon: const Icon(Icons.menu),
              onPressed: () => Scaffold.of(context).openDrawer(),
            ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  _getPageTitle(),
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  _getPageSubtitle(),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          _buildConnectionStatus(),
          const SizedBox(width: 16),
          _buildRefreshButton(),
          const SizedBox(width: 16),
          _buildNotificationButton(),
        ],
      ),
    );
  }

  Widget _buildConnectionStatus() {
    return Obx(() {
      final isConnected = _realtimeController.isConnected.value;
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isConnected ? Colors.green : Colors.red,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isConnected ? Icons.wifi : Icons.wifi_off,
              size: 16,
              color: Colors.white,
            ),
            const SizedBox(width: 4),
            Text(
              isConnected ? 'Connected' : 'Disconnected',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildRefreshButton() {
    return Obx(() {
      final isLoading = _dashboardController.isLoading.value;
      return IconButton(
        icon: AnimatedRotation(
          turns: isLoading ? 1 : 0,
          duration: const Duration(milliseconds: 1000),
          child: const Icon(Icons.refresh),
        ),
        onPressed: isLoading ? null : () => _dashboardController.forceRefresh(),
        tooltip: 'Refresh Data',
      );
    });
  }

  Widget _buildNotificationButton() {
    return Obx(() {
      final eventCount = _realtimeController.realtimeEvents.length;
      return Badge(
        isLabelVisible: eventCount > 0,
        label: Text(eventCount > 99 ? '99+' : eventCount.toString()),
        child: IconButton(
          icon: const Icon(Icons.notifications_outlined),
          onPressed: _showNotificationsDialog,
          tooltip: 'Notifications',
        ),
      );
    });
  }

  Widget _buildDashboardContent(BuildContext context) {
    return Obx(() {
      if (_dashboardController.isLoading.value && 
          _dashboardController.intersections.isEmpty) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'Loading dashboard...',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
            ],
          ),
        );
      }

      return SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_dashboardController.dashboardData.isEmpty) ...[
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceVariant,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Dashboard is loading. Make sure the backend server is running on http://localhost:5000',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
            ],
            
            _buildKPICards(context),
            const SizedBox(height: 24),
            _buildChartsSection(context),
            const SizedBox(height: 24),
            _buildIntersectionsGrid(context),
            const SizedBox(height: 24),
            _buildRecentActivity(context),
          ],
        ),
      );
    });
  }

  Widget _buildKPICards(BuildContext context) {
    return Obx(() {
      final summary = _dashboardController.dashboardData['summary'] ?? {};
      
      return ResponsiveRowColumn(
        layout: ResponsiveBreakpoints.of(context).isMobile
            ? ResponsiveRowColumnType.COLUMN
            : ResponsiveRowColumnType.ROW,
        rowSpacing: 20,
        columnSpacing: 16,
        children: [
          ResponsiveRowColumnItem(
            rowFlex: 1,
            child:             AppleMetricCard(
              title: 'Active Intersections',
              value: '${summary['activeIntersections'] ?? 0}',
              subtitle: 'Currently operational',
              icon: Icons.traffic,
              color: Theme.of(context).colorScheme.primary,
              trend: '+12% from last month',
            ),
          ),
          ResponsiveRowColumnItem(
            rowFlex: 1,
            child:             AppleMetricCard(
              title: 'Average Wait Time',
              value: '${summary['avgWaitTime'] ?? 0}s',
              subtitle: 'Across all intersections',
              icon: Icons.timer,
              color: Theme.of(context).colorScheme.secondary,
              trend: '-8% improvement',
            ),
          ),
          ResponsiveRowColumnItem(
            rowFlex: 1,
            child:             AppleMetricCard(
              title: 'Total Vehicles',
              value: '${summary['totalVehicles'] ?? 0}',
              subtitle: 'Processed today',
              icon: Icons.directions_car,
              color: Theme.of(context).colorScheme.tertiary,
              trend: '+5% vs yesterday',
            ),
          ),
          ResponsiveRowColumnItem(
            rowFlex: 1,
            child: AppleMetricCard(
              title: 'System Efficiency',
              value: '${((summary['efficiency'] ?? 0.0) * 100).toInt()}%',
              subtitle: 'Overall performance',
              icon: Icons.speed,
              color: Theme.of(context).colorScheme.secondary,
              trend: '+2.1% this week',
            ),
          ),
        ],
      );
    });
  }

  Widget _buildChartsSection(BuildContext context) {
    return Obx(() {
      final chartData = _dashboardController.dashboardData['charts'] ?? {};
      
      return Column(
        children: [
          // Simplified Performance Chart
          AppleChartCard(
            title: 'Performance Overview',
            subtitle: 'Traffic flow and efficiency metrics',
            actions: [
              AppleSegmentedControl(
                segments: const ['Today', 'Week', 'Month'],
                selectedIndex: 0,
                onSelectionChanged: (index) {
                  // Handle time range selection
                },
              ),
            ],
            child: Container(
              height: 200,
              alignment: Alignment.center,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.analytics,
                    size: 48,
                    color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Performance data will be displayed here',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 20),
          
          // Simplified Distribution Cards
          Row(
            children: [
              Expanded(
                child: AppleChartCard(
                  title: 'Traffic Distribution',
                  subtitle: 'By intersection',
                  child: Container(
                    height: 150,
                    alignment: Alignment.center,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.pie_chart,
                          size: 40,
                          color: Theme.of(context).colorScheme.secondary.withOpacity(0.5),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Distribution chart',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              
              const SizedBox(width: 20),
              
              Expanded(
                child: AppleChartCard(
                  title: 'Queue Analysis',
                  subtitle: 'Average queue length',
                  child: Container(
                    height: 150,
                    alignment: Alignment.center,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.bar_chart,
                          size: 40,
                          color: Theme.of(context).colorScheme.tertiary.withOpacity(0.5),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Queue analysis',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      );
    });
  }

  Widget _buildIntersectionsGrid(BuildContext context) {
    return Obx(() {
      final intersections = _dashboardController.intersections;
      
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Intersections',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  TextButton.icon(
                    onPressed: () => Get.toNamed('/intersections'),
                    icon: const Icon(Icons.arrow_forward),
                    label: const Text('View All'),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (intersections.isEmpty)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('No intersections available'),
                  ),
                )
              else
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: ResponsiveBreakpoints.of(context).isDesktop ? 4 : 2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: 1.2,
                  ),
                  itemCount: intersections.length > 8 ? 8 : intersections.length,
                  itemBuilder: (context, index) {
                    final intersection = intersections[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: const Icon(Icons.traffic),
                        title: Text(intersection.name),
                        subtitle: Text('Status: ${intersection.status}'),
                        trailing: Text(
                          '${intersection.averageWaitTime.toStringAsFixed(0)}s',
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),
                        onTap: () => _dashboardController.selectIntersection(intersection.id),
                      ),
                    );
                  },
                ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildRecentActivity(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Recent Activity',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            Obx(() {
              final events = _realtimeController.realtimeEvents.take(5).toList();
              
              if (events.isEmpty) {
                return const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('No recent activity'),
                  ),
                );
              }

              return ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: events.length,
                separatorBuilder: (context, index) => const Divider(),
                itemBuilder: (context, index) {
                  final event = events[index];
                  return RecentActivityItem(event: event);
                },
              );
            }),
          ],
        ),
      ),
    );
  }

  String _getPageTitle() {
    return 'Dashboard Overview';
  }

  String _getPageSubtitle() {
    return 'Real-time system overview and performance metrics';
  }

  void _showNotificationsDialog() {
    Get.dialog(
      Dialog(
        child: Container(
          width: 400,
          height: 500,
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Notifications',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  IconButton(
                    onPressed: () => Get.back(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const Divider(),
              Expanded(
                child: Obx(() {
                  final events = _realtimeController.realtimeEvents;
                  
                  if (events.isEmpty) {
                    return const Center(child: Text('No notifications'));
                  }

                  return ListView.builder(
                    itemCount: events.length,
                    itemBuilder: (context, index) {
                      final event = events[index];
                      return ListTile(
                        leading: _getEventIcon(event['type']),
                        title: Text(event['title'] ?? ''),
                        subtitle: Text(event['message'] ?? ''),
                        trailing: Text(
                          _formatTimestamp(event['timestamp']),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      );
                    },
                  );
                }),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Icon _getEventIcon(String? type) {
    switch (type) {
      case 'intersection_update': return const Icon(Icons.traffic, color: Colors.blue);
      case 'system_alert': return const Icon(Icons.warning, color: Colors.orange);
      case 'performance_update': return const Icon(Icons.analytics, color: Colors.green);
      case 'training_update': return const Icon(Icons.model_training, color: Colors.purple);
      case 'connection_error': return const Icon(Icons.error, color: Colors.red);
      default: return const Icon(Icons.info, color: Colors.grey);
    }
  }

  String _formatTimestamp(dynamic timestamp) {
    if (timestamp == null) return '';
    
    try {
      final dateTime = DateTime.parse(timestamp.toString());
      final now = DateTime.now();
      final difference = now.difference(dateTime);
      
      if (difference.inMinutes < 1) {
        return 'Just now';
      } else if (difference.inHours < 1) {
        return '${difference.inMinutes}m ago';
      } else if (difference.inDays < 1) {
        return '${difference.inHours}h ago';
      } else {
        return '${difference.inDays}d ago';
      }
    } catch (e) {
      return '';
    }
  }
} 