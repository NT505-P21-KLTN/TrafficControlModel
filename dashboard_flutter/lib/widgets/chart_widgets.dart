import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:syncfusion_flutter_gauges/gauges.dart';
import 'package:responsive_framework/responsive_framework.dart';

/// Performance Line Chart for time-based analytics
class PerformanceLineChart extends StatelessWidget {
  final List<Map<String, dynamic>> data;
  final String title;
  final Color lineColor;
  final bool showGrid;
  final String? yAxisLabel;
  final String? xAxisLabel;

  const PerformanceLineChart({
    super.key,
    required this.data,
    required this.title,
    this.lineColor = Colors.blue,
    this.showGrid = true,
    this.yAxisLabel,
    this.xAxisLabel,
  });

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    
    return Card(
      child: Padding(
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: isMobile ? 200 : 250,
              child: data.isEmpty
                  ? Center(
                      child: Text(
                        'No data available',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    )
                  : LineChart(
                      LineChartData(
                        gridData: FlGridData(
                          show: showGrid,
                          drawVerticalLine: true,
                          drawHorizontalLine: true,
                          getDrawingHorizontalLine: (value) => FlLine(
                            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                            strokeWidth: 1,
                          ),
                          getDrawingVerticalLine: (value) => FlLine(
                            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                            strokeWidth: 1,
                          ),
                        ),
                        titlesData: FlTitlesData(
                          leftTitles: AxisTitles(
                            axisNameWidget: yAxisLabel != null
                                ? Text(
                                    yAxisLabel!,
                                    style: Theme.of(context).textTheme.bodySmall,
                                  )
                                : null,
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 40,
                              getTitlesWidget: (value, meta) => Text(
                                value.toStringAsFixed(0),
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ),
                          ),
                          bottomTitles: AxisTitles(
                            axisNameWidget: xAxisLabel != null
                                ? Text(
                                    xAxisLabel!,
                                    style: Theme.of(context).textTheme.bodySmall,
                                  )
                                : null,
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 30,
                              getTitlesWidget: (value, meta) {
                                if (value.toInt() >= 0 && value.toInt() < data.length) {
                                  final item = data[value.toInt()];
                                  final time = item['time'] as String? ?? '';
                                  return Text(
                                    time.length > 5 ? time.substring(0, 5) : time,
                                    style: Theme.of(context).textTheme.bodySmall,
                                  );
                                }
                                return const Text('');
                              },
                            ),
                          ),
                          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        ),
                        borderData: FlBorderData(
                          show: true,
                          border: Border.all(
                            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                          ),
                        ),
                        lineBarsData: [
                          LineChartBarData(
                            spots: _generateSpots(),
                            isCurved: true,
                            color: lineColor,
                            barWidth: 3,
                            isStrokeCapRound: true,
                            dotData: const FlDotData(show: false),
                            belowBarData: BarAreaData(
                              show: true,
                              color: lineColor.withOpacity(0.1),
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  List<FlSpot> _generateSpots() {
    return data.asMap().entries.map((entry) {
      final index = entry.key.toDouble();
      final value = (entry.value['value'] as num?)?.toDouble() ?? 0.0;
      return FlSpot(index, value);
    }).toList();
  }
}

/// System Health Gauge widget
class SystemHealthGauge extends StatelessWidget {
  final double value;
  final String title;
  final double maxValue;
  final Color primaryColor;
  final String unit;

  const SystemHealthGauge({
    super.key,
    required this.value,
    required this.title,
    this.maxValue = 100,
    this.primaryColor = Colors.blue,
    this.unit = '%',
  });

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    
    return Card(
      child: Padding(
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        child: Column(
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: isMobile ? 150 : 200,
              child: SfRadialGauge(
                axes: <RadialAxis>[
                  RadialAxis(
                    minimum: 0,
                    maximum: maxValue,
                    ranges: <GaugeRange>[
                      GaugeRange(
                        startValue: 0,
                        endValue: maxValue * 0.3,
                        color: Colors.red.withOpacity(0.3),
                        startWidth: 10,
                        endWidth: 10,
                      ),
                      GaugeRange(
                        startValue: maxValue * 0.3,
                        endValue: maxValue * 0.7,
                        color: Colors.orange.withOpacity(0.3),
                        startWidth: 10,
                        endWidth: 10,
                      ),
                      GaugeRange(
                        startValue: maxValue * 0.7,
                        endValue: maxValue,
                        color: Colors.green.withOpacity(0.3),
                        startWidth: 10,
                        endWidth: 10,
                      ),
                    ],
                    pointers: <GaugePointer>[
                      NeedlePointer(
                        value: value,
                        needleColor: primaryColor,
                        knobStyle: KnobStyle(
                          knobRadius: 0.08,
                          color: primaryColor,
                        ),
                      ),
                    ],
                    annotations: <GaugeAnnotation>[
                      GaugeAnnotation(
                        widget: Container(
                          child: Text(
                            '${value.toStringAsFixed(1)}$unit',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: primaryColor,
                            ),
                          ),
                        ),
                        angle: 90,
                        positionFactor: 0.5,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Traffic Flow Bar Chart
class TrafficFlowBarChart extends StatelessWidget {
  final List<Map<String, dynamic>> data;
  final String title;

  const TrafficFlowBarChart({
    super.key,
    required this.data,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    
    return Card(
      child: Padding(
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: isMobile ? 200 : 250,
              child: data.isEmpty
                  ? Center(
                      child: Text(
                        'No data available',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    )
                  : BarChart(
                      BarChartData(
                        alignment: BarChartAlignment.spaceAround,
                        maxY: _getMaxValue() * 1.2,
                        titlesData: FlTitlesData(
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 40,
                              getTitlesWidget: (value, meta) => Text(
                                value.toStringAsFixed(0),
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ),
                          ),
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              getTitlesWidget: (value, meta) {
                                if (value.toInt() >= 0 && value.toInt() < data.length) {
                                  final item = data[value.toInt()];
                                  return Padding(
                                    padding: const EdgeInsets.only(top: 8),
                                    child: Text(
                                      item['label'] ?? '',
                                      style: Theme.of(context).textTheme.bodySmall,
                                    ),
                                  );
                                }
                                return const Text('');
                              },
                            ),
                          ),
                          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        ),
                        borderData: FlBorderData(
                          show: true,
                          border: Border.all(
                            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                          ),
                        ),
                        barGroups: _generateBarGroups(context),
                        gridData: FlGridData(
                          show: true,
                          drawHorizontalLine: true,
                          drawVerticalLine: false,
                          getDrawingHorizontalLine: (value) => FlLine(
                            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                            strokeWidth: 1,
                          ),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  List<BarChartGroupData> _generateBarGroups(BuildContext context) {
    return data.asMap().entries.map((entry) {
      final index = entry.key;
      final value = (entry.value['value'] as num?)?.toDouble() ?? 0.0;
      
      return BarChartGroupData(
        x: index,
        barRods: [
          BarChartRodData(
            toY: value,
            color: _getBarColor(index),
            width: 20,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(4),
              topRight: Radius.circular(4),
            ),
          ),
        ],
      );
    }).toList();
  }

  Color _getBarColor(int index) {
    const colors = [
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.red,
      Colors.teal,
    ];
    return colors[index % colors.length];
  }

  double _getMaxValue() {
    if (data.isEmpty) return 100;
    return data.map((item) => (item['value'] as num?)?.toDouble() ?? 0.0).reduce((a, b) => a > b ? a : b);
  }
}

/// Queue Length Comparison Chart
class QueueComparisonChart extends StatelessWidget {
  final List<Map<String, dynamic>> beforeData;
  final List<Map<String, dynamic>> afterData;
  final String title;

  const QueueComparisonChart({
    super.key,
    required this.beforeData,
    required this.afterData,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    
    return Card(
      child: Padding(
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                _buildLegend(context),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: isMobile ? 200 : 250,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: true,
                    drawHorizontalLine: true,
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                      strokeWidth: 1,
                    ),
                    getDrawingVerticalLine: (value) => FlLine(
                      color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                      strokeWidth: 1,
                    ),
                  ),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        getTitlesWidget: (value, meta) => Text(
                          value.toStringAsFixed(0),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 30,
                        getTitlesWidget: (value, meta) {
                          if (value.toInt() >= 0 && value.toInt() < beforeData.length) {
                            return Text(
                              'T${value.toInt() + 1}',
                              style: Theme.of(context).textTheme.bodySmall,
                            );
                          }
                          return const Text('');
                        },
                      ),
                    ),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(
                    show: true,
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                    ),
                  ),
                  lineBarsData: [
                    // Before optimization line
                    LineChartBarData(
                      spots: _generateSpotsFromData(beforeData),
                      isCurved: true,
                      color: Colors.red,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: const FlDotData(show: true),
                      belowBarData: BarAreaData(
                        show: true,
                        color: Colors.red.withOpacity(0.1),
                      ),
                    ),
                    // After optimization line
                    LineChartBarData(
                      spots: _generateSpotsFromData(afterData),
                      isCurved: true,
                      color: Colors.green,
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: const FlDotData(show: true),
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
    );
  }

  Widget _buildLegend(BuildContext context) {
    return Row(
      children: [
        _buildLegendItem(context, Colors.red, 'Before'),
        const SizedBox(width: 16),
        _buildLegendItem(context, Colors.green, 'After'),
      ],
    );
  }

  Widget _buildLegendItem(BuildContext context, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  List<FlSpot> _generateSpotsFromData(List<Map<String, dynamic>> data) {
    return data.asMap().entries.map((entry) {
      final index = entry.key.toDouble();
      final value = (entry.value['value'] as num?)?.toDouble() ?? 0.0;
      return FlSpot(index, value);
    }).toList();
  }
}

/// Real-time Performance Monitor
class RealTimePerformanceMonitor extends StatelessWidget {
  final List<Map<String, dynamic>> data;
  final String title;
  final bool isLive;

  const RealTimePerformanceMonitor({
    super.key,
    required this.data,
    required this.title,
    this.isLive = false,
  });

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    
    return Card(
      child: Padding(
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                if (isLive)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.green.withOpacity(0.3)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: const BoxDecoration(
                            color: Colors.green,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'LIVE',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: Colors.green.shade700,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: isMobile ? 150 : 200,
              child: data.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.timeline,
                            size: 48,
                            color: Theme.of(context).colorScheme.onSurfaceVariant.withOpacity(0.5),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Waiting for data...',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    )
                  : LineChart(
                      LineChartData(
                        gridData: FlGridData(
                          show: true,
                          drawVerticalLine: false,
                          drawHorizontalLine: true,
                          getDrawingHorizontalLine: (value) => FlLine(
                            color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
                            strokeWidth: 1,
                          ),
                        ),
                        titlesData: const FlTitlesData(
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 40,
                            ),
                          ),
                          bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        ),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            spots: _generateSpotsFromData(data),
                            isCurved: true,
                            color: Theme.of(context).colorScheme.primary,
                            barWidth: 2,
                            isStrokeCapRound: true,
                            dotData: const FlDotData(show: false),
                            belowBarData: BarAreaData(
                              show: true,
                              color: Theme.of(context).colorScheme.primary.withOpacity(0.1),
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  List<FlSpot> _generateSpotsFromData(List<Map<String, dynamic>> data) {
    return data.asMap().entries.map((entry) {
      final index = entry.key.toDouble();
      final value = (entry.value['value'] as num?)?.toDouble() ?? 0.0;
      return FlSpot(index, value);
    }).toList();
  }
} 