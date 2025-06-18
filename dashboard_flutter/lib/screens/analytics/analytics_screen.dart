import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:responsive_framework/responsive_framework.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../controllers/analytics_controller.dart';
import '../../widgets/dashboard_widgets.dart';

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.put(AnalyticsController());
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;

    return Scaffold(
      body: Obx(() => LoadingOverlay(
        isLoading: controller.isLoading.value,
        message: 'Loading analytics data...',
        child: SingleChildScrollView(
          padding: EdgeInsets.all(isMobile ? 12 : 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Text(
                'Analytics & Reporting',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),

              // KPI Cards
              ResponsiveRowColumn(
                layout: isMobile ? ResponsiveRowColumnType.COLUMN : ResponsiveRowColumnType.ROW,
                rowSpacing: 16,
                columnSpacing: 16,
                children: [
                  ResponsiveRowColumnItem(
                    child: KPICard(
                      title: 'Average Performance',
                      value: '${(controller.avgPerformanceScore.value * 100).toStringAsFixed(1)}%',
                      icon: Icons.analytics,
                      color: _getPerformanceColor(controller.avgPerformanceScore.value),
                      trend: '+${controller.performanceTrend.value.toStringAsFixed(1)}%',
                      subtitle: 'Across all intersections',
                    ),
                  ),
                  ResponsiveRowColumnItem(
                    child: KPICard(
                      title: 'Total Vehicles',
                      value: controller.totalVehiclesProcessed.value.toString(),
                      icon: Icons.directions_car,
                      color: Colors.blue,
                      trend: '+${controller.vehiclesTrend.value.toStringAsFixed(1)}%',
                      subtitle: 'Processed today',
                    ),
                  ),
                  ResponsiveRowColumnItem(
                    child: KPICard(
                      title: 'Avg Wait Time',
                      value: '${controller.avgWaitTime.value.toStringAsFixed(1)}s',
                      icon: Icons.timer,
                      color: _getWaitTimeColor(controller.avgWaitTime.value),
                      trend: '${controller.waitTimeTrend.value.toStringAsFixed(1)}%',
                      subtitle: 'Per vehicle',
                    ),
                  ),
                  ResponsiveRowColumnItem(
                    child: KPICard(
                      title: 'Queue Efficiency',
                      value: '${(controller.queueEfficiency.value * 100).toStringAsFixed(1)}%',
                      icon: Icons.linear_scale,
                      color: _getEfficiencyColor(controller.queueEfficiency.value),
                      trend: '+${controller.queueTrend.value.toStringAsFixed(1)}%',
                      subtitle: 'Reduction vs baseline',
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 32),

              // Performance Chart
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Performance Trends',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        height: 300,
                        child: LineChart(
                          LineChartData(
                            gridData: FlGridData(
                              show: true,
                              drawVerticalLine: true,
                              drawHorizontalLine: true,
                            ),
                            titlesData: FlTitlesData(
                              leftTitles: AxisTitles(
                                sideTitles: SideTitles(
                                  showTitles: true,
                                  reservedSize: 40,
                                  getTitlesWidget: (value, meta) => Text(
                                    '${(value * 100).toInt()}%',
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                ),
                              ),
                              bottomTitles: AxisTitles(
                                sideTitles: SideTitles(
                                  showTitles: true,
                                  reservedSize: 30,
                                  getTitlesWidget: (value, meta) => Text(
                                    '${value.toInt()}h',
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                ),
                              ),
                              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                            ),
                            borderData: FlBorderData(show: true),
                            lineBarsData: [
                              LineChartBarData(
                                spots: controller.performanceData.asMap().entries.map((entry) {
                                  return FlSpot(entry.key.toDouble(), entry.value['value']?.toDouble() ?? 0.0);
                                }).toList(),
                                isCurved: true,
                                color: Colors.green,
                                barWidth: 3,
                                isStrokeCapRound: true,
                                dotData: const FlDotData(show: false),
                                belowBarData: BarAreaData(
                                  show: true,
                                  color: Colors.green.withOpacity(0.1),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 32),
            ],
          ),
        ),
      )),
    );
  }

  Color _getPerformanceColor(double score) {
    if (score > 0.8) return Colors.green;
    if (score > 0.6) return Colors.orange;
    return Colors.red;
  }

  Color _getWaitTimeColor(double waitTime) {
    if (waitTime < 30) return Colors.green;
    if (waitTime < 60) return Colors.orange;
    return Colors.red;
  }

  Color _getEfficiencyColor(double efficiency) {
    if (efficiency > 0.8) return Colors.green;
    if (efficiency > 0.6) return Colors.orange;
    return Colors.red;
  }
}