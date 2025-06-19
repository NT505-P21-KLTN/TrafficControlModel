import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:responsive_framework/responsive_framework.dart';
import 'dart:ui' as ui;
import 'dart:async';
import 'dart:math' as math;
import '../../controllers/intersection_controller.dart';
import '../../models/intersection_data.dart';
import '../../widgets/dashboard_widgets.dart';

class IntersectionsScreen extends StatefulWidget {
  const IntersectionsScreen({super.key});

  @override
  State<IntersectionsScreen> createState() => _IntersectionsScreenState();
}

class _IntersectionsScreenState extends State<IntersectionsScreen> 
    with TickerProviderStateMixin {
  final IntersectionController controller = Get.find<IntersectionController>();
  GoogleMapController? _mapController;
  final Set<Marker> _markers = {};
  final Set<Polyline> _polylines = {};
  final Set<Circle> _circles = {};
  final Set<Polygon> _heatMapPolygons = {};
  IntersectionData? _selectedIntersection;
  bool _isEditingMode = false;
  bool _showHeatMap = false;
  bool _showCameras = true;
  String? _hoveredCamera;
  
  // Animation controllers
  late AnimationController _mapAnimationController;
  late Animation<double> _mapZoomAnimation;

  // Default location (San Francisco)
  static const LatLng _defaultCenter = LatLng(37.7749, -122.4194);

  @override
  void initState() {
    super.initState();
    
    // Initialize animation controllers
    _mapAnimationController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    
    _mapZoomAnimation = Tween<double>(
      begin: 10.0,
      end: 14.0,
    ).animate(CurvedAnimation(
      parent: _mapAnimationController,
      curve: Curves.easeInOutCubic,
    ));
    
    // Listen to intersection updates
    ever(controller.intersections, (_) {
      _updateMapMarkers();
    });
    
    // Load intersections from server
    controller.loadIntersections().then((_) {
      // Auto-animate to first intersection after loading
      if (controller.intersections.isNotEmpty) {
        Future.delayed(const Duration(milliseconds: 500), () {
          _animateToFirstIntersection();
        });
      }
    });
  }

  @override
  void dispose() {
    _mapAnimationController.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
  }

  void _animateToFirstIntersection() {
    if (controller.intersections.isEmpty) return;
    
    final firstIntersection = controller.intersections.first;
    final target = LatLng(
      firstIntersection.location.latitude,
      firstIntersection.location.longitude,
    );
    
    _mapAnimationController.forward();
    
    _mapController?.animateCamera(
      CameraUpdate.newLatLngZoom(target, 14.0),
    );
    
    // Select the first intersection
    setState(() {
      _selectedIntersection = firstIntersection;
    });
  }

  void _updateMapMarkers() {
    setState(() {
      _markers.clear();
      _polylines.clear();
      _circles.clear();
      _heatMapPolygons.clear();
      
      for (int i = 0; i < controller.intersections.length; i++) {
        final intersection = controller.intersections[i];
        final position = LatLng(
          intersection.location.latitude, 
          intersection.location.longitude
        );
        
        // Create intersection marker (smaller size)
        _createCustomMarker(intersection).then((customIcon) {
          _markers.add(
            Marker(
              markerId: MarkerId(intersection.id),
              position: position,
              draggable: _isEditingMode,
              icon: customIcon,
              infoWindow: InfoWindow(
                title: intersection.name,
                snippet: '${intersection.status.toUpperCase()} • ${intersection.metrics.vehicleCount} vehicles',
                onTap: () => _selectIntersection(intersection),
              ),
              onDragEnd: (newPosition) => _onMarkerDragEnd(intersection, newPosition),
              onTap: () => _selectIntersection(intersection),
            ),
          );
          
          if (mounted) setState(() {});
        });
        
        // Add camera markers if enabled
        if (_showCameras) {
          _addCameraMarkers(intersection, position);
        }
        
        // Add heat map if enabled
        if (_showHeatMap) {
          _addHeatMapPolygon(intersection, position);
        }
      }
      
      // Add connections between intersections
      _addIntersectionConnections();
    });
  }

  void _addCameraMarkers(IntersectionData intersection, LatLng position) {
    for (final camera in intersection.cameras) {
      _createCameraMarker().then((cameraIcon) {
        _markers.add(
          Marker(
            markerId: MarkerId(camera.id),
            position: LatLng(camera.latitude, camera.longitude),
            icon: cameraIcon,
            infoWindow: InfoWindow(
              title: 'Camera ${camera.direction.toUpperCase()}',
              snippet: 'Coverage: ${intersection.name} • Range: ${camera.range.toInt()}m',
            ),
            onTap: () => _onCameraMarkerTap(camera.id, LatLng(camera.latitude, camera.longitude)),
          ),
        );
        
        if (mounted) setState(() {});
      });
    }
  }

  void _addHeatMapPolygon(IntersectionData intersection, LatLng position) {
    final trafficDensity = intersection.metrics.vehicleCount / 100.0;
    final heatIntensity = math.min(trafficDensity, 1.0);
    
    // Create heat map polygon around intersection
    final offset = 0.002;
    final heatPolygon = Polygon(
      polygonId: PolygonId('${intersection.id}_heat'),
      points: [
        LatLng(position.latitude + offset, position.longitude + offset),
        LatLng(position.latitude + offset, position.longitude - offset),
        LatLng(position.latitude - offset, position.longitude - offset),
        LatLng(position.latitude - offset, position.longitude + offset),
      ],
      fillColor: Color.lerp(
        Colors.green.withOpacity(0.3),
        Colors.red.withOpacity(0.6),
        heatIntensity,
      )!,
      strokeColor: Color.lerp(
        Colors.green,
        Colors.red,
        heatIntensity,
      )!,
      strokeWidth: 1,
    );
    
    _heatMapPolygons.add(heatPolygon);
  }

  void _onCameraMarkerTap(String cameraId, LatLng position) {
    setState(() {
      _hoveredCamera = cameraId;
    });
    
    // Find the camera data
    Camera? camera;
    for (final intersection in controller.intersections) {
      camera = intersection.cameras.firstWhereOrNull((c) => c.id == cameraId);
      if (camera != null) break;
    }
    
    if (camera != null) {
      // Add camera coverage circle
      final coverageCircle = Circle(
        circleId: CircleId('${cameraId}_coverage'),
        center: position,
        radius: camera.range,
        strokeWidth: 2,
        strokeColor: Colors.blue.withOpacity(0.8),
        fillColor: Colors.blue.withOpacity(0.2),
      );
      
      _circles.add(coverageCircle);
      
      // Remove coverage circle after 3 seconds
      Timer(const Duration(seconds: 3), () {
        if (mounted) {
          setState(() {
            _circles.removeWhere((circle) => 
              circle.circleId.value == '${cameraId}_coverage');
            _hoveredCamera = null;
          });
        }
      });
    }
  }

  Future<BitmapDescriptor> _createCustomMarker(IntersectionData intersection) async {
    final pictureRecorder = ui.PictureRecorder();
    final canvas = Canvas(pictureRecorder);
    final size = 60.0; // Smaller size
    
    // Get colors based on status
    final statusColor = _getStatusColor(intersection.status);
    final isSelected = _selectedIntersection?.id == intersection.id;
    
    // Draw outer circle (shadow/border)
    final outerPaint = Paint()
      ..color = Colors.black.withOpacity(0.2)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(
      Offset(size / 2, size / 2), 
      size / 2, 
      outerPaint,
    );
    
    // Draw main circle (smaller)
    final mainPaint = Paint()
      ..color = statusColor
      ..style = PaintingStyle.fill;
    canvas.drawCircle(
      Offset(size / 2, size / 2), 
      (size / 2) - 3, 
      mainPaint,
    );
    
    // Draw inner white circle (smaller)
    final innerPaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;
    canvas.drawCircle(
      Offset(size / 2, size / 2), 
      (size / 2) - 6, 
      innerPaint,
    );
    
    // Draw status icon (smaller)
    final iconData = _getStatusIcon(intersection.status);
    final textPainter = TextPainter(
      text: TextSpan(
        text: String.fromCharCode(iconData.codePoint),
        style: TextStyle(
          fontSize: 18, // Reduced from 24
          fontFamily: iconData.fontFamily,
          color: statusColor,
          fontWeight: FontWeight.w600,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(
      canvas,
      Offset(
        (size - textPainter.width) / 2,
        (size - textPainter.height) / 2,
      ),
    );
    
    // Draw selection ring if selected
    if (isSelected) {
      final selectionPaint = Paint()
        ..color = statusColor.withOpacity(0.3)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4;
      canvas.drawCircle(
        Offset(size / 2, size / 2), 
        (size / 2) + 6, 
        selectionPaint,
      );
    }
    
    // Convert to bitmap
    final picture = pictureRecorder.endRecording();
    final image = await picture.toImage(size.toInt(), size.toInt());
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    
    return BitmapDescriptor.fromBytes(bytes!.buffer.asUint8List());
  }

  Future<BitmapDescriptor> _createCameraMarker() async {
    final pictureRecorder = ui.PictureRecorder();
    final canvas = Canvas(pictureRecorder);
    final size = 30.0;
    
    // Draw camera background
    final backgroundPaint = Paint()
      ..color = Colors.blue.withOpacity(0.9)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(
      Offset(size / 2, size / 2), 
      size / 2, 
      backgroundPaint,
    );
    
    // Draw camera icon
    final textPainter = TextPainter(
      text: TextSpan(
        text: String.fromCharCode(Icons.videocam.codePoint),
        style: TextStyle(
          fontSize: 16,
          fontFamily: Icons.videocam.fontFamily,
          color: Colors.white,
          fontWeight: FontWeight.w600,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(
      canvas,
      Offset(
        (size - textPainter.width) / 2,
        (size - textPainter.height) / 2,
      ),
    );
    
    // Convert to bitmap
    final picture = pictureRecorder.endRecording();
    final image = await picture.toImage(size.toInt(), size.toInt());
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    
    return BitmapDescriptor.fromBytes(bytes!.buffer.asUint8List());
  }

  void _selectIntersection(IntersectionData intersection) {
    setState(() {
      _selectedIntersection = intersection;
    });
    
    // Animate to intersection
    _mapController?.animateCamera(
      CameraUpdate.newLatLngZoom(
        LatLng(intersection.location.latitude, intersection.location.longitude),
        16.0,
      ),
    );
  }

  void _onMarkerDragEnd(IntersectionData intersection, LatLng newPosition) {
    // Show confirmation dialog
    _showMoveConfirmationDialog(intersection, newPosition);
  }

  void _showMoveConfirmationDialog(IntersectionData intersection, LatLng newPosition) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Move ${intersection.name}?'),
        content: Text(
          'Do you want to move this intersection to the new location?\n\n'
          'New coordinates: ${newPosition.latitude.toStringAsFixed(6)}, ${newPosition.longitude.toStringAsFixed(6)}',
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              _updateMapMarkers(); // Reset markers
            },
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              controller.updateIntersectionLocation(intersection.id, newPosition);
              Navigator.of(context).pop();
            },
            child: const Text('Move'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = ResponsiveBreakpoints.of(context).isMobile;
    final isTablet = ResponsiveBreakpoints.of(context).isTablet;

    return Scaffold(
      backgroundColor: Theme.of(context).colorScheme.background,
      body: Column(
        children: [
          _buildTopAppBar(context),
          Expanded(
            child: isMobile ? _buildMobileLayout() : _buildDesktopLayout(),
          ),
        ],
      ),
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
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Intersections',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  'Manage traffic control points',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          _buildEditModeToggle(),
          const SizedBox(width: 16),
          _buildHeatMapToggle(),
          const SizedBox(width: 16),
          _buildCameraToggle(),
          const SizedBox(width: 16),
          _buildMockDataButton(),
          const SizedBox(width: 16),
          _buildTrainingResultsButton(),
          const SizedBox(width: 16),
          _buildTestingResultsButton(),
          const SizedBox(width: 16),
          _buildGenerateDataButton(),
          const SizedBox(width: 16),
          _buildRefreshButton(),
          const SizedBox(width: 16),
          _buildAddButton(),
        ],
      ),
    );
  }

  Widget _buildEditModeToggle() {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          GestureDetector(
            onTap: () => setState(() => _isEditingMode = false),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: !_isEditingMode ? Theme.of(context).colorScheme.surface : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
                boxShadow: !_isEditingMode ? [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 1),
                  ),
                ] : null,
              ),
              child: Text(
                'View',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: !_isEditingMode 
                      ? Theme.of(context).colorScheme.onSurface 
                      : Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
            ),
          ),
          GestureDetector(
            onTap: () => setState(() => _isEditingMode = true),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: _isEditingMode ? Theme.of(context).colorScheme.surface : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
                boxShadow: _isEditingMode ? [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 1),
                  ),
                ] : null,
              ),
              child: Text(
                'Edit',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: _isEditingMode 
                      ? Theme.of(context).colorScheme.onSurface 
                      : Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRefreshButton() {
    return Obx(() {
      final isLoading = controller.isLoading.value;
      return Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceVariant,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: isLoading ? null : () => controller.refreshData(),
            child: AnimatedRotation(
              turns: isLoading ? 1 : 0,
              duration: const Duration(milliseconds: 1000),
              child: const Icon(Icons.refresh, size: 20),
            ),
          ),
        ),
      );
    });
  }

  Widget _buildAddButton() {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primary,
        borderRadius: BorderRadius.circular(10),
        boxShadow: [
          BoxShadow(
            color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: _showCreateIntersectionDialog,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.add, color: Colors.white, size: 18),
                const SizedBox(width: 8),
                Text(
                  'Add',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeatMapToggle() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: _showHeatMap 
            ? Theme.of(context).colorScheme.primary.withOpacity(0.1)
            : Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
        border: _showHeatMap 
            ? Border.all(color: Theme.of(context).colorScheme.primary, width: 1)
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () {
            setState(() {
              _showHeatMap = !_showHeatMap;
            });
            _updateMapMarkers();
          },
          child: Icon(
            Icons.thermostat,
            size: 20,
            color: _showHeatMap 
                ? Theme.of(context).colorScheme.primary
                : Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _buildCameraToggle() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: _showCameras 
            ? Theme.of(context).colorScheme.secondary.withOpacity(0.1)
            : Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
        border: _showCameras 
            ? Border.all(color: Theme.of(context).colorScheme.secondary, width: 1)
            : null,
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () {
            setState(() {
              _showCameras = !_showCameras;
            });
            _updateMapMarkers();
          },
          child: Icon(
            Icons.videocam,
            size: 20,
            color: _showCameras 
                ? Theme.of(context).colorScheme.secondary
                : Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _buildMockDataButton() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: _showMockDataDialog,
          child: Icon(
            Icons.data_usage,
            size: 20,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _buildTrainingResultsButton() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: _showTrainingResultsDialog,
          child: Icon(
            Icons.bar_chart,
            size: 20,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _buildTestingResultsButton() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: _showTestingResultsDialog,
          child: Icon(
            Icons.check,
            size: 20,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _buildGenerateDataButton() {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: _showGenerateDataDialog,
          child: Icon(
            Icons.data_usage,
            size: 20,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }

  Widget _buildMobileLayout() {
    return Column(
      children: [
        // Map view (full width on mobile)
        Expanded(
          flex: 1,
          child: _buildMapSection(),
        ),
        // Intersection list (bottom sheet style)
        Container(
          height: 300,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 10,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: _buildIntersectionsList(),
        ),
      ],
    );
  }

  Widget _buildDesktopLayout() {
    return Row(
      children: [
        // Left side - Intersections list
        Expanded(
          flex: 2,
          child: _buildIntersectionsList(),
        ),
        
        // Divider
        Container(
          width: 1,
          color: Theme.of(context).colorScheme.outline.withOpacity(0.2),
        ),
        
        // Right side - Interactive map
        Expanded(
          flex: 3,
          child: _buildMapSection(),
        ),
      ],
    );
  }

  Widget _buildIntersectionsList() {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Statistics cards
          _buildStatisticsCards(),
          const SizedBox(height: 24),
          
          // Search and filters
          _buildSearchAndFilters(),
          const SizedBox(height: 20),
          
          // Intersections list
          Expanded(
            child: _buildIntersectionsListView(),
          ),
        ],
      ),
    );
  }

  Widget _buildStatisticsCards() {
    return Obx(() {
      return Row(
        children: [
          Expanded(
            child: AppleMetricCard(
              title: 'Total',
              value: controller.intersections.length.toString(),
              icon: Icons.traffic,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: AppleMetricCard(
              title: 'Online',
              value: controller.getOnlineCount().toString(),
              icon: Icons.check_circle,
              color: Theme.of(context).colorScheme.secondary,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: AppleMetricCard(
              title: 'Training',
              value: controller.getTrainingCount().toString(),
              icon: Icons.model_training,
              color: Theme.of(context).colorScheme.tertiary,
            ),
          ),
        ],
      );
    });
  }

  Widget _buildSearchAndFilters() {
    return Column(
      children: [
        // Search bar
        Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceVariant,
            borderRadius: BorderRadius.circular(12),
          ),
          child: TextField(
            onChanged: controller.setSearchQuery,
            decoration: InputDecoration(
              hintText: 'Search intersections...',
              prefixIcon: Icon(
                Icons.search,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            ),
          ),
        ),
        const SizedBox(height: 12),
        
        // Filter chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _buildFilterChip('All', ''),
              const SizedBox(width: 8),
              _buildFilterChip('Online', 'online'),
              const SizedBox(width: 8),
              _buildFilterChip('Training', 'training'),
              const SizedBox(width: 8),
              _buildFilterChip('Offline', 'offline'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildFilterChip(String label, String value) {
    return Obx(() {
      final isSelected = controller.selectedStatus.value == value;
      return GestureDetector(
        onTap: () => controller.setStatusFilter(value),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected 
                ? Theme.of(context).colorScheme.primary 
                : Theme.of(context).colorScheme.surfaceVariant,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: isSelected 
                  ? Colors.white 
                  : Theme.of(context).colorScheme.onSurfaceVariant,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      );
    });
  }

  Widget _buildIntersectionsListView() {
    return Obx(() {
      if (controller.filteredIntersections.isEmpty) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.traffic,
                size: 64,
                color: Theme.of(context).colorScheme.primary.withOpacity(0.5),
              ),
              const SizedBox(height: 16),
              Text(
                'No intersections found',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
            ],
          ),
        );
      }

      return ListView.separated(
        itemCount: controller.filteredIntersections.length,
        separatorBuilder: (context, index) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final intersection = controller.filteredIntersections[index];
          return _buildIntersectionListItem(intersection);
        },
      );
    });
  }

  Widget _buildIntersectionListItem(IntersectionData intersection) {
    final isSelected = _selectedIntersection?.id == intersection.id;
    
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: isSelected 
            ? Theme.of(context).colorScheme.primary.withOpacity(0.05)
            : Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isSelected 
              ? Theme.of(context).colorScheme.primary.withOpacity(0.3)
              : Theme.of(context).colorScheme.outline.withOpacity(0.1),
          width: isSelected ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _selectIntersection(intersection),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header row
                Row(
                  children: [
                    // Status indicator
                    Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        color: _getStatusColor(intersection.status).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        _getStatusIcon(intersection.status),
                        color: _getStatusColor(intersection.status),
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 12),
                    
                    // Name and location
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            intersection.name,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${intersection.latitude.toStringAsFixed(4)}, ${intersection.longitude.toStringAsFixed(4)}',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                              fontFamily: 'monospace',
                            ),
                          ),
                        ],
                      ),
                    ),
                    
                    // Status badge
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: _getStatusColor(intersection.status).withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        intersection.status.toUpperCase(),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: _getStatusColor(intersection.status),
                          fontWeight: FontWeight.w600,
                          fontSize: 10,
                        ),
                      ),
                    ),
                    
                    const SizedBox(width: 8),
                    
                    // Menu button
                    PopupMenuButton<String>(
                      onSelected: (value) => _handleIntersectionAction(value, intersection),
                      icon: Icon(
                        Icons.more_vert,
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                        size: 20,
                      ),
                      itemBuilder: (context) => [
                        const PopupMenuItem(value: 'edit', child: Text('Edit Details')),
                        const PopupMenuItem(value: 'configure', child: Text('Configure AI')),
                        if (intersection.status == 'offline')
                          const PopupMenuItem(value: 'start_training', child: Text('Start Training')),
                        if (intersection.status == 'training')
                          const PopupMenuItem(value: 'stop_training', child: Text('Stop Training')),
                        const PopupMenuItem(value: 'delete', child: Text('Delete')),
                      ],
                    ),
                  ],
                ),
                
                const SizedBox(height: 16),
                
                // Metrics row
                Row(
                  children: [
                    _buildMetricChip(
                      icon: Icons.directions_car,
                      label: 'Vehicles',
                      value: intersection.metrics.vehicleCount.toString(),
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                                         _buildMetricChip(
                       icon: Icons.speed,
                       label: 'Throughput',
                       value: '${intersection.metrics.throughput.toInt()}/h',
                       color: Theme.of(context).colorScheme.secondary,
                     ),
                    const SizedBox(width: 8),
                    _buildMetricChip(
                      icon: Icons.timer,
                      label: 'Wait Time',
                      value: '${intersection.metrics.averageWaitTime.toInt()}s',
                      color: Theme.of(context).colorScheme.tertiary,
                    ),
                  ],
                ),
                
                const SizedBox(height: 12),
                
                // Performance indicator
                Row(
                  children: [
                    Icon(
                      Icons.analytics,
                      size: 16,
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Performance: ',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                      ),
                    ),
                    Container(
                      width: 100,
                      height: 4,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(2),
                        color: Theme.of(context).colorScheme.surfaceVariant,
                      ),
                      child: FractionallySizedBox(
                        alignment: Alignment.centerLeft,
                        widthFactor: intersection.metrics.efficiency / 100,
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(2),
                            color: _getEfficiencyColor(intersection.metrics.efficiency),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${intersection.metrics.efficiency.toInt()}%',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: _getEfficiencyColor(intersection.metrics.efficiency),
                      ),
                    ),
                  ],
                ),
                
                // Last updated
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.access_time,
                      size: 14,
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Updated ${_getTimeAgo(intersection.lastUpdate)}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMetricChip({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(height: 2),
            Text(
              value,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: color,
                fontSize: 11,
              ),
            ),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                fontSize: 9,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getEfficiencyColor(double efficiency) {
    if (efficiency >= 80) return Theme.of(context).colorScheme.secondary;
    if (efficiency >= 60) return Theme.of(context).colorScheme.tertiary;
    return Theme.of(context).colorScheme.error;
  }

  String _getTimeAgo(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    
    if (difference.inDays > 0) {
      return '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes}m ago';
    } else {
      return 'Just now';
    }
  }

  Widget _buildMapSection() {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          bottomLeft: Radius.circular(20),
        ),
      ),
      child: Column(
        children: [
          // Map header
          Container(
            padding: const EdgeInsets.all(20),
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
                Icon(
                  Icons.map,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  'Topology Map',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                if (_isEditingMode)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.tertiary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.edit,
                          size: 16,
                          color: Theme.of(context).colorScheme.tertiary,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'Edit Mode',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.tertiary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          
          // Google Map with error handling
          Expanded(
            child: ClipRRect(
              borderRadius: const BorderRadius.only(
                bottomLeft: Radius.circular(20),
              ),
              child: _buildMapWidget(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMapWidget() {
    return Container(
      width: double.infinity,
      height: double.infinity,
      child: Stack(
        children: [
          // Actual Google Maps widget
          GoogleMap(
            onMapCreated: (GoogleMapController controller) {
              _mapController = controller;
              _updateMapMarkers();
              
              // Apply custom map style after a brief delay to ensure context is ready
              Future.delayed(const Duration(milliseconds: 100), () {
                if (mounted) {
                  final style = _getMapStyle();
                  if (style != null) {
                    controller.setMapStyle(style);
                  }
                }
              });
            },
            initialCameraPosition: CameraPosition(
              target: _defaultCenter,
              zoom: 12.0,
            ),
            markers: _markers,
            polylines: _polylines,
            circles: _circles,
            polygons: _heatMapPolygons,
            onTap: _onMapTap,
            mapType: MapType.normal,
            myLocationButtonEnabled: false,
            zoomControlsEnabled: false,
            mapToolbarEnabled: false,
          ),
          
          // Overlay showing intersection data
          Positioned(
            top: 16,
            right: 16,
            child: _buildMapOverlay(),
          ),
          
          // Edit mode instructions
          if (_isEditingMode)
            Positioned(
              bottom: 16,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.tertiary.withOpacity(0.9),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.touch_app,
                      color: Colors.white,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Tap on the map to create new intersections • Drag markers to move existing ones',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDemoIntersections() {
    return Obx(() {
      if (controller.intersections.isEmpty) {
        return const SizedBox();
      }

      return Column(
        children: [
          Text(
            'Intersection Locations',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.onSurface.withOpacity(0.8),
            ),
          ),
          const SizedBox(height: 12),
          ...controller.intersections.take(3).map((intersection) => 
            Container(
              margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 16),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: _getStatusColor(intersection.status).withOpacity(0.3),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _getStatusColor(intersection.status),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    intersection.name,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${intersection.latitude.toStringAsFixed(4)}, ${intersection.longitude.toStringAsFixed(4)}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
            ),
          ).toList(),
        ],
      );
    });
  }

  Widget _buildMapOverlay() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withOpacity(0.9),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Map Legend',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          _buildLegendItem('Online', Theme.of(context).colorScheme.secondary),
          _buildLegendItem('Training', Theme.of(context).colorScheme.tertiary),
          _buildLegendItem('Offline', Theme.of(context).colorScheme.error),
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  String? _getMapStyle() {
    // Custom map style for Apple-like appearance
    // Safely access theme with fallback
    bool isDark = false;
    try {
      if (mounted && context.mounted) {
        isDark = Theme.of(context).brightness == Brightness.dark;
      }
    } catch (e) {
      // Fallback to light theme if context is not ready
      isDark = false;
    }
    
    if (isDark) {
      // Dark theme Apple-style map
      return '''[
        {
          "elementType": "geometry",
          "stylers": [{"color": "#1d1d1d"}]
        },
        {
          "elementType": "labels.text.stroke",
          "stylers": [{"color": "#1d1d1d"}]
        },
        {
          "elementType": "labels.text.fill",
          "stylers": [{"color": "#8ec3b0"}]
        },
        {
          "featureType": "administrative",
          "elementType": "geometry.stroke",
          "stylers": [{"color": "#4f4f4f"}]
        },
        {
          "featureType": "road",
          "elementType": "geometry",
          "stylers": [{"color": "#2c2c2c"}]
        },
        {
          "featureType": "road",
          "elementType": "geometry.stroke",
          "stylers": [{"color": "#4f4f4f"}]
        },
        {
          "featureType": "road.highway",
          "elementType": "geometry",
          "stylers": [{"color": "#3c3c3c"}]
        },
        {
          "featureType": "water",
          "elementType": "geometry",
          "stylers": [{"color": "#0f3460"}]
        },
        {
          "featureType": "poi",
          "elementType": "labels.text.fill",
          "stylers": [{"color": "#6f9ba4"}]
        }
      ]''';
    } else {
      // Light theme Apple-style map
      return '''[
        {
          "featureType": "all",
          "elementType": "geometry.fill",
          "stylers": [{"color": "#f8f9fa"}]
        },
        {
          "featureType": "all",
          "elementType": "labels.text.fill",
          "stylers": [{"color": "#3c4043"}]
        },
        {
          "featureType": "road",
          "elementType": "geometry",
          "stylers": [{"color": "#ffffff"}]
        },
        {
          "featureType": "road",
          "elementType": "geometry.stroke",
          "stylers": [{"color": "#e1e5e9"}]
        },
        {
          "featureType": "road.highway",
          "elementType": "geometry",
          "stylers": [{"color": "#f8f9fa"}]
        },
        {
          "featureType": "road.highway",
          "elementType": "geometry.stroke",
          "stylers": [{"color": "#d2d6da"}]
        },
        {
          "featureType": "water",
          "elementType": "geometry",
          "stylers": [{"color": "#c9e6ff"}]
        },
        {
          "featureType": "poi",
          "elementType": "geometry",
          "stylers": [{"color": "#f1f3f4"}]
        },
        {
          "featureType": "poi.park",
          "elementType": "geometry",
          "stylers": [{"color": "#e8f5e8"}]
        },
        {
          "featureType": "transit",
          "elementType": "geometry",
          "stylers": [{"color": "#e9e9e9"}]
        }
      ]''';
    }
  }

  void _onMapTap(LatLng position) {
    if (_isEditingMode) {
      _showCreateIntersectionAt(position);
    }
  }

  void _showCreateIntersectionAt(LatLng position) {
    final nameController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Create Intersection'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(
                labelText: 'Intersection Name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Location: ${position.latitude.toStringAsFixed(6)}, ${position.longitude.toStringAsFixed(6)}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (nameController.text.isNotEmpty) {
                final data = {
                  'name': nameController.text,
                  'latitude': position.latitude,
                  'longitude': position.longitude,
                  'status': 'offline',
                };
                controller.createIntersection(data);
                Navigator.of(context).pop();
              }
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _showCreateIntersectionDialog() {
    final nameController = TextEditingController();
    final latController = TextEditingController();
    final lngController = TextEditingController();
    final descriptionController = TextEditingController();
    String selectedStatus = 'offline';
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.add_location, color: Colors.blue),
              SizedBox(width: 8),
              Text('Create New Intersection'),
            ],
          ),
          content: SizedBox(
            width: 400,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Information card
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.blue.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.info_outline, size: 16, color: Colors.blue),
                            const SizedBox(width: 8),
                            Text(
                              'Intersection Creation',
                              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.blue,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          '• Creates intersection configuration in central server\n'
                          '• Automatically generates 4 cameras (N, E, S, W)\n'
                          '• Sets up traffic light phases and timing\n'
                          '• Note: Does NOT create intersection agent config files',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  
                  // Basic Information
                  Text(
                    'Basic Information',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: nameController,
                    decoration: const InputDecoration(
                      labelText: 'Intersection Name *',
                      hintText: 'e.g., Main St & 5th Ave',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.label),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: descriptionController,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Description (Optional)',
                      hintText: 'Brief description of the intersection...',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.description),
                    ),
                  ),
                  const SizedBox(height: 20),
                  
                  // Location
                  Text(
                    'Location',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: latController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: const InputDecoration(
                            labelText: 'Latitude *',
                            hintText: '10.777807',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.my_location),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: lngController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: const InputDecoration(
                            labelText: 'Longitude *',
                            hintText: '106.681676',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.map),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  
                  // Initial Status
                  Text(
                    'Initial Status',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: selectedStatus,
                    decoration: const InputDecoration(
                      labelText: 'Status',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.traffic),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'offline', child: Text('Offline')),
                      DropdownMenuItem(value: 'online', child: Text('Online')),
                      DropdownMenuItem(value: 'maintenance', child: Text('Maintenance')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        setState(() {
                          selectedStatus = value;
                        });
                      }
                    },
                  ),
                  const SizedBox(height: 20),
                  
                  // Features section
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.green.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.check_circle, size: 16, color: Colors.green),
                            const SizedBox(width: 8),
                            Text(
                              'Included Features',
                              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          '✓ 4 Traffic cameras (100m range each)\n'
                          '✓ Default 4-phase traffic light system\n'
                          '✓ Real-time monitoring capabilities\n'
                          '✓ Heat map visualization support',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                if (nameController.text.isNotEmpty &&
                    latController.text.isNotEmpty &&
                    lngController.text.isNotEmpty) {
                  final lat = double.tryParse(latController.text);
                  final lng = double.tryParse(lngController.text);
                  if (lat != null && lng != null) {
                    final data = {
                      'name': nameController.text,
                      'description': descriptionController.text.isNotEmpty ? descriptionController.text : null,
                      'latitude': lat,
                      'longitude': lng,
                      'status': selectedStatus,
                    };
                    controller.createIntersection(data);
                    Navigator.of(context).pop();
                    
                    // Show success message
                    Get.snackbar(
                      'Success',
                      'Intersection "${nameController.text}" created successfully!',
                      backgroundColor: Colors.green,
                      colorText: Colors.white,
                      duration: const Duration(seconds: 3),
                    );
                  } else {
                    Get.snackbar(
                      'Error',
                      'Please enter valid latitude and longitude values',
                      backgroundColor: Colors.red,
                      colorText: Colors.white,
                    );
                  }
                } else {
                  Get.snackbar(
                    'Error',
                    'Please fill in all required fields (marked with *)',
                    backgroundColor: Colors.red,
                    colorText: Colors.white,
                  );
                }
              },
              child: const Text('Create Intersection'),
            ),
          ],
        ),
      ),
    );
  }

  void _showMockDataDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Load Mock Data'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.data_usage,
              size: 48,
              color: Colors.blue,
            ),
            const SizedBox(height: 16),
            const Text(
              'This will load 4 mock intersections based on the existing intersection agent configurations:',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade300),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildMockDataItem('Agent 1', 'Dien Bien Phu - Hai Ba Trung', '10.786519, 106.693680'),
                  _buildMockDataItem('Agent 2', 'Dien Bien Phu - Dinh Tien Hoang', '10.7901173, 106.6976396'),
                  _buildMockDataItem('Agent 3', 'Hai Ba Trung - Nguyen Thi Minh Khai', '10.782851, 106.698079'),
                  _buildMockDataItem('Agent 4', 'Nguyen Thi Minh Khai - Dinh Tien Hoang', '10.786750, 106.701765'),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              controller.loadMockData();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Mock data loaded successfully!'),
                  backgroundColor: Colors.green,
                ),
              );
            },
            child: const Text('Load Mock Data'),
          ),
        ],
      ),
    );
  }

  Widget _buildMockDataItem(String title, String subtitle, String coordinates) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(Icons.traffic, size: 16, color: Theme.of(context).colorScheme.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                Text(subtitle, style: const TextStyle(fontSize: 10)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            coordinates,
            style: const TextStyle(fontSize: 10),
          ),
        ],
      ),
    );
  }

  void _handleIntersectionAction(String action, IntersectionData intersection) {
    switch (action) {
      case 'edit':
        _showEditIntersectionDialog(intersection);
        break;
      case 'configure':
        // Show configuration dialog
        break;
      case 'start_training':
        // Training functionality removed - controller doesn't support it
        Get.snackbar('Info', 'Training functionality not available');
        break;
      case 'stop_training':
        // Training functionality removed - controller doesn't support it
        Get.snackbar('Info', 'Training functionality not available');
        break;
      case 'delete':
        _showDeleteConfirmationDialog(intersection);
        break;
    }
  }

  void _showEditIntersectionDialog(IntersectionData intersection) {
    final nameController = TextEditingController(text: intersection.name);
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Intersection'),
        content: TextField(
          controller: nameController,
          decoration: const InputDecoration(
            labelText: 'Intersection Name',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (nameController.text.isNotEmpty) {
                final data = {
                  'name': nameController.text,
                };
                controller.updateIntersection(intersection.id, data);
                Navigator.of(context).pop();
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _showDeleteConfirmationDialog(IntersectionData intersection) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Intersection'),
        content: Text('Are you sure you want to delete "${intersection.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: () {
              controller.deleteIntersection(intersection.id);
              Navigator.of(context).pop();
              if (_selectedIntersection?.id == intersection.id) {
                setState(() => _selectedIntersection = null);
              }
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'online':
        return Theme.of(context).colorScheme.secondary;
      case 'training':
        return Theme.of(context).colorScheme.tertiary;
      case 'offline':
        return Theme.of(context).colorScheme.error;
      case 'error':
        return Theme.of(context).colorScheme.error;
      case 'warning':
        return Theme.of(context).colorScheme.tertiary;
      default:
        return Theme.of(context).colorScheme.onSurface.withOpacity(0.6);
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status) {
      case 'online':
        return Icons.check_circle;
      case 'training':
        return Icons.model_training;
      case 'offline':
        return Icons.cancel;
      case 'error':
        return Icons.error;
      case 'warning':
        return Icons.warning;
      default:
        return Icons.traffic;
    }
  }

  void _addIntersectionConnections() {
    final intersections = controller.intersections;
    for (int i = 0; i < intersections.length - 1; i++) {
      final start = LatLng(
        intersections[i].location.latitude,
        intersections[i].location.longitude,
      );
      final end = LatLng(
        intersections[i + 1].location.latitude,
        intersections[i + 1].location.longitude,
      );
      
      _polylines.add(
        Polyline(
          polylineId: PolylineId('connection_${i}_${i + 1}'),
          points: [start, end],
          color: Theme.of(context).colorScheme.primary.withOpacity(0.6),
          width: 3,
          patterns: [PatternItem.dash(10), PatternItem.gap(5)],
        ),
      );
    }
  }

  void _showTrainingResultsDialog() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 800,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.bar_chart, color: Colors.blue, size: 32),
                  const SizedBox(width: 12),
                  Text(
                    'Training Results',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildTrainingSection('Single Intersection Models', [
                        {'name': 'Balanced', 'reward': -12860, 'waiting': 37.5, 'improvement': 14.3, 'status': 'Optimal'},
                        {'name': 'Conservative', 'reward': -15240, 'waiting': 41.2, 'improvement': 8.7, 'status': 'Stable'},
                        {'name': 'High Traffic', 'reward': -14520, 'waiting': 39.8, 'improvement': 11.6, 'status': 'Good'},
                        {'name': 'Baseline', 'reward': -16100, 'waiting': 45.0, 'improvement': 0.0, 'status': 'Reference'},
                      ]),
                      const SizedBox(height: 24),
                      _buildSyncAgentSection(),
                      const SizedBox(height: 24),
                      _buildPerformanceComparisonChart(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showTestingResultsDialog() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 800,
          height: 600,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.check_circle, color: Colors.green, size: 32),
                  const SizedBox(width: 12),
                  Text(
                    'Testing & Validation Results',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildValidationScenarios(),
                      const SizedBox(height: 24),
                      _buildProductionReadiness(),
                      const SizedBox(height: 24),
                      _buildStatisticalValidation(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showGenerateDataDialog() {
    String selectedTrafficLevel = 'medium';
    int episodes = 100;
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.data_usage, color: Colors.orange),
              SizedBox(width: 8),
              Text('Generate Training Data'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Generate new training data to improve model performance:',
                style: TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  const Text('Traffic Level: '),
                  const Spacer(),
                  DropdownButton<String>(
                    value: selectedTrafficLevel,
                    onChanged: (value) => setState(() => selectedTrafficLevel = value!),
                    items: const [
                      DropdownMenuItem(value: 'low', child: Text('Low (300 veh/h)')),
                      DropdownMenuItem(value: 'medium', child: Text('Medium (600 veh/h)')),
                      DropdownMenuItem(value: 'high', child: Text('High (900 veh/h)')),
                      DropdownMenuItem(value: 'rush_hour', child: Text('Rush Hour (1200 veh/h)')),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Text('Episodes: '),
                  const Spacer(),
                  SizedBox(
                    width: 100,
                    child: TextFormField(
                      initialValue: episodes.toString(),
                      keyboardType: TextInputType.number,
                      onChanged: (value) => episodes = int.tryParse(value) ?? 100,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Estimated Training Time: ${(episodes / 50 * 1).toStringAsFixed(1)} hours',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text('Expected Improvement: ${_getExpectedImprovement(selectedTrafficLevel)}%'),
                  ],
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pop();
                _startTrainingJob(selectedTrafficLevel, episodes);
              },
              child: const Text('Start Training'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTrainingSection(String title, List<Map<String, dynamic>> models) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        ...models.map((model) => Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 2,
                child: Text(model['name'], style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
              Expanded(child: Text('${model['waiting']}s wait')),
              Expanded(child: Text('${model['improvement']}% improve')),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _getStatusColorFromString(model['status']),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  model['status'],
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ),
        )).toList(),
      ],
    );
  }

  Widget _buildSyncAgentSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        border: Border.all(color: Colors.green.shade200),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.sync, color: Colors.green.shade700),
              const SizedBox(width: 8),
              Text(
                'Sync Agent Performance',
                style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green.shade700),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: Text('Multi-intersection improvement: 27.0%')),
              Expanded(child: Text('Training stability: High')),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: Text('Convergence: 150 episodes')),
              Expanded(child: Text('Statistical significance: p < 0.001')),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPerformanceComparisonChart() {
    return Container(
      height: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Performance Comparison', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          Expanded(
            child: Row(
              children: [
                _buildComparisonBar('Fixed Time', 0, Colors.red.shade300),
                _buildComparisonBar('Actuated', 6.9, Colors.orange.shade300),
                _buildComparisonBar('SCOOT', 12.5, Colors.yellow.shade600),
                _buildComparisonBar('DQN Single', 14.3, Colors.blue.shade400),
                _buildComparisonBar('Sync Agent', 27.0, Colors.green.shade400),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildComparisonBar(String label, double value, Color color) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Column(
          children: [
            Expanded(
              child: Align(
                alignment: Alignment.bottomCenter,
                child: Container(
                  width: 40,
                  height: (value / 30 * 120).clamp(5, 120),
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(fontSize: 10), textAlign: TextAlign.center),
            Text('${value.toStringAsFixed(1)}%', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _buildValidationScenarios() {
    final scenarios = [
      {'name': 'Low Traffic', 'success': 95.2, 'improvement': 34.5, 'status': 'Excellent'},
      {'name': 'Medium Traffic', 'success': 92.7, 'improvement': 28.2, 'status': 'Very Good'},
      {'name': 'High Traffic', 'success': 87.3, 'improvement': 18.7, 'status': 'Good'},
      {'name': 'Rush Hour', 'success': 81.5, 'improvement': 12.4, 'status': 'Acceptable'},
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Validation Scenarios', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 12),
        ...scenarios.map((scenario) => Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
                             Expanded(flex: 2, child: Text(scenario['name'] as String)),
               Expanded(child: Text('${scenario['success']}% success')),
               Expanded(child: Text('${scenario['improvement']}% improve')),
               Container(
                 padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                 decoration: BoxDecoration(
                   color: _getStatusColorFromString(scenario['status'] as String),
                   borderRadius: BorderRadius.circular(12),
                 ),
                 child: Text(
                   scenario['status'] as String,
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ],
          ),
        )).toList(),
      ],
    );
  }

  Widget _buildProductionReadiness() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        border: Border.all(color: Colors.blue.shade200),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Production Readiness', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: Text('Recovery Rate: 98.7%')),
              Expanded(child: Text('Response Time: 125ms')),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: Text('Uptime: 99.8%')),
              Expanded(child: Text('Throughput: 1000 req/s')),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatisticalValidation() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Statistical Validation', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 12),
          const Text('All improvements statistically significant (p < 0.001)'),
          const SizedBox(height: 8),
          const Text('Effect sizes: Large for waiting time, Medium-Large for queue length'),
          const SizedBox(height: 8),
          const Text('Robustness testing: 89% edge case coverage'),
        ],
      ),
    );
  }

  Color _getStatusColorFromString(String status) {
    switch (status.toLowerCase()) {
      case 'optimal':
      case 'excellent':
        return Colors.green;
      case 'very good':
      case 'good':
      case 'stable':
        return Colors.blue;
      case 'acceptable':
        return Colors.orange;
      case 'failed':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  double _getExpectedImprovement(String trafficLevel) {
    switch (trafficLevel) {
      case 'low':
        return 34.5;
      case 'medium':
        return 28.2;
      case 'high':
        return 18.7;
      case 'rush_hour':
        return 12.4;
      default:
        return 20.0;
    }
  }

  void _startTrainingJob(String trafficLevel, int episodes) {
    // Simulate starting a training job
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Training job started: $episodes episodes at $trafficLevel traffic level'),
        backgroundColor: Colors.blue,
        action: SnackBarAction(
          label: 'View Progress',
          onPressed: () {
            // Could show a progress dialog or navigate to training screen
          },
        ),
      ),
    );
  }
} 