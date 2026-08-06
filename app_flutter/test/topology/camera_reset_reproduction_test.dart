import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/topology/topographical_view.dart';
import 'package:app_flutter/features/topology/topology_map.dart';

/// Ephemeral implementation of [ThemeService] for testing.
class EphemeralThemeService implements ThemeService {
  @override
  Future<ThemeMode> loadThemeMode() async => ThemeMode.system;
  @override
  Future<void> saveThemeMode(ThemeMode mode) async {}
  @override
  Future<int> loadThemeScheme() async => 0;
  @override
  Future<void> saveThemeScheme(int scheme) async {}
  @override
  Future<double> loadTextScale() async => 1.0;
  @override
  Future<void> saveTextScale(double scale) async {}
  @override
  Future<Axis> loadLayoutSplitAxis() async => Axis.vertical;
  @override
  Future<void> saveLayoutSplitAxis(Axis axis) async {}
  @override
  Future<double> loadPanelOpacity() async => 0.85;
  @override
  Future<void> savePanelOpacity(double opacity) async {}
}

// dim0 = dim_1 (x), dim1 = dim_0 (y) per resolveCoordinate
const _topologyData = TopologyData(
  coordinateMapping: {},
  nodes: <TopologyNode>[
    TopologyNode(
      id: 'ViewA',
      label: 'View A',
      position: TopologyNodePosition(
        dim0: 140.0, // dim_1 (x)
        dim1: 35.0,  // dim_0 (y)
        dim2: 0.0,
        timeIndex: 0,
        vector: [],
      ),
      status: 'Active',
    ),
    TopologyNode(
      id: 'ViewB',
      label: 'View B',
      position: TopologyNodePosition(
        dim0: -75.0, // dim_1 (x)
        dim1: 50.0,   // dim_0 (y)
        dim2: 0.0,
        timeIndex: 0,
        vector: [],
      ),
      status: 'Active',
    ),
  ],
  links: [],
);

class _ParentWrapper extends StatefulWidget {
  final String currentView;
  final ValueChanged<String> onViewSelected;
  final TopologyData topologyData;

  const _ParentWrapper({
    super.key,
    required this.currentView,
    required this.onViewSelected,
    required this.topologyData,
  });

  @override
  State<_ParentWrapper> createState() => _ParentWrapperState();
}

class _ParentWrapperState extends State<_ParentWrapper> {
  String _currentView = 'ViewA';

  @override
  void initState() {
    super.initState();
    _currentView = widget.currentView;
  }

  @override
  void didUpdateWidget(_ParentWrapper oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.currentView != oldWidget.currentView) {
      setState(() {
        _currentView = widget.currentView;
      });
    }
  }

  void forceViewChange(String newView) {
    if (mounted) {
      setState(() {
        _currentView = newView;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider<ThemeController>(
      create: (_) => ThemeController(EphemeralThemeService()),
      child: MaterialApp(
        home: Scaffold(
          body: TopographicalView(
            currentView: _currentView,
            onViewSelected: widget.onViewSelected,
            topologyData: widget.topologyData,
          ),
        ),
      ),
    );
  }
}

void main() {
  group('Camera reset reproduction (Issue #50)', () {
    VirtualCamera _makeCamera(double lat, double lng) {
      return VirtualCamera(
        dim_0: lat,
        dim_1: lng,
        dim_2: 500.0,
        heading: 0.0,
        pitch: -45.0,
        roll: 0.0,
      );
    }

    Future<_ParentWrapperState> _pumpTopographicalView(
      WidgetTester tester, {
      String startView = 'ViewA',
    }) async {
      tester.view.physicalSize = const Size(1200, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        _ParentWrapper(
          currentView: startView,
          onViewSelected: (_) {},
          topologyData: _topologyData,
        ),
      );
      await tester.pumpAndSettle();

      return tester.state(find.byType(_ParentWrapper));
    }

    CameraController _findCameraController(WidgetTester tester) {
      expect(find.byType(Scene3DViewport), findsOneWidget);
      final state = tester.state(find.byType(Scene3DViewport)) as dynamic;
      return state.cameraController as CameraController;
    }

    testWidgets(
      'Camera resets when parent rebuild changes currentView to a different node',
      (WidgetTester tester) async {
        final wrapperState = await _pumpTopographicalView(tester, startView: 'ViewA');

        final CameraController controller = _findCameraController(tester);

        // Verify initial camera is at ViewA coordinates (dim1=35.0 latency, dim0=140.0 lng)
        expect(controller.current.dim_0, 35.0);
        expect(controller.current.dim_1, 140.0);

        // Simulate user panning: move the camera
        controller.pan(const Offset(-100, 0));
        final double pannedDim_1 = controller.current.dim_1;
        expect(pannedDim_1, greaterThan(140.0),
            reason: 'Camera should have panned right');

        // Simulate what _LayoutState._updateCurrentViewFromLayout() does:
        // silently changes _currentView to the first tree node
        // This represents the TreeViewModel notification path
        wrapperState.forceViewChange('ViewB');
        await tester.pumpAndSettle();

        // CAMERA SHOULD NOT RESET TO ViewB! It should preserve the user's pan/coords.
        final CameraController afterController = _findCameraController(tester);
        expect(afterController.current.dim_0, 35.0,
            reason: 'Camera dim_0 should remain at ViewA coordinate since we decoupled single-click');
        expect(afterController.current.dim_1, pannedDim_1,
            reason: 'Camera dim_1 should remain at panned coordinate since we decoupled single-click');
      });

    testWidgets(
      'Camera state is preserved when currentView does not change during parent rebuild',
      (WidgetTester tester) async {
        final wrapperState = await _pumpTopographicalView(tester, startView: 'ViewA');
        final CameraController controller = _findCameraController(tester);

        // Pan the camera
        controller.pan(const Offset(-50, -50));
        final double pannedLat = controller.current.dim_0;
        final double pannedLng = controller.current.dim_1;

        // Force a rebuild without changing the view
        // (simulates a TreeViewModel notification when _currentView doesn't change)
        wrapperState.forceViewChange('ViewA');
        await tester.pumpAndSettle();

        final CameraController afterController = _findCameraController(tester);
        expect(afterController.current.dim_0, pannedLat,
            reason: 'Camera dim_0 should be preserved when view is unchanged');
        expect(afterController.current.dim_1, pannedLng,
            reason: 'Camera dim_1 should be preserved when view is unchanged');
      });

    testWidgets(
      'didUpdateWidget in Scene3DViewport overwrites camera when widget.camera differs',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(800, 600);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final originalCam = _makeCamera(35.0, 135.0);
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Scene3DViewport(
                camera: originalCam,
                topologyData: _topologyData,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final CameraController controller = _findCameraController(tester);

        // Pan to a different position
        controller.pan(const Offset(-200, -100));
        expect(controller.current.dim_1, isNot(135.0));

        // Parent rebuild passes a NEW camera instance with different values
        // (simulating what _resolveCamera does after view change)
        final newCam = _makeCamera(50.0, -75.0);
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Scene3DViewport(
                camera: newCam,
                topologyData: _topologyData,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        // BUG: Camera was overwritten to the new camera values
        final CameraController afterController = _findCameraController(tester);
        expect(afterController.current.dim_0, 50.0);
        expect(afterController.current.dim_1, -75.0);
      });

    testWidgets(
      'didUpdateWidget preserves camera when widget.camera is unchanged',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(800, 600);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final initialCam = VirtualCamera.clamped(
          dim_0: 35.0,
          dim_1: 135.0,
          dim_2: 500.0,
          heading: 0.0,
          pitch: -45.0,
          roll: 0.0,
        );
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Scene3DViewport(
                camera: initialCam,
                topologyData: _topologyData,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final CameraController controller = _findCameraController(tester);
        controller.pan(const Offset(-200, 0));
        final double pannedLng = controller.current.dim_1;

        // Rebuild with the same camera values (not reference, but equal by value)
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Scene3DViewport(
                camera: VirtualCamera.clamped(
                  dim_0: 35.0,
                  dim_1: 135.0,
                  dim_2: 500.0,
                  heading: 0.0,
                  pitch: -45.0,
                  roll: 0.0,
                ),
                topologyData: _topologyData,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final CameraController afterController = _findCameraController(tester);
        expect(afterController.current.dim_1, pannedLng,
            reason: 'Camera state should be preserved when widget camera is value-equal');
      });

    testWidgets(
      'Camera is preserved after tree notification (simulating expand/collapse)',
      (WidgetTester tester) async {
        final wrapperState = await _pumpTopographicalView(tester, startView: 'ViewB');
        final CameraController controller = _findCameraController(tester);

        expect(controller.current.dim_0, 50.0);
        expect(controller.current.dim_1, -75.0);

        controller.pan(const Offset(-150, 0));
        final double pannedLat = controller.current.dim_0;
        final double pannedLng = controller.current.dim_1;

        wrapperState.forceViewChange('ViewB');
        await tester.pumpAndSettle();

        final CameraController afterController = _findCameraController(tester);
        expect(afterController.current.dim_0, pannedLat,
            reason: 'Camera dim_0 preserved after tree notification');
        expect(afterController.current.dim_1, pannedLng,
            reason: 'Camera dim_1 preserved after tree notification');
      });

    testWidgets(
      'currentView is NOT overwritten on subsequent tree notifications',
      (WidgetTester tester) async {
        final wrapperState = await _pumpTopographicalView(tester, startView: 'ViewA');
        final CameraController controller = _findCameraController(tester);

        wrapperState.forceViewChange('ViewB');
        await tester.pumpAndSettle();

        final CameraController afterNavController = _findCameraController(tester);
        // Expect that it does NOT jump to ViewB, so it remains at 35.0, 140.0
        expect(afterNavController.current.dim_0, 35.0);
        expect(afterNavController.current.dim_1, 140.0);

        final CameraController ctrl = _findCameraController(tester);
        ctrl.pan(const Offset(-100, -50));
        final double pannedLat = ctrl.current.dim_0;
        final double pannedLng = ctrl.current.dim_1;

        wrapperState.forceViewChange('ViewB');
        await tester.pumpAndSettle();

        final CameraController afterController = _findCameraController(tester);
        expect(afterController.current.dim_0, pannedLat,
            reason: 'currentView NOT overwritten by tree notification');
        expect(afterController.current.dim_1, pannedLng,
            reason: 'currentView NOT overwritten by tree notification');
      });

    testWidgets(
      'Initial view selection still works correctly on first launch',
      (WidgetTester tester) async {
        await _pumpTopographicalView(tester, startView: 'ViewB');
        final CameraController controller = _findCameraController(tester);

        expect(controller.current.dim_0, 50.0,
            reason: 'Initial camera should be at ViewB dim_0');
        expect(controller.current.dim_1, -75.0,
            reason: 'Initial camera should be at ViewB dim_1');
        expect(controller.current.dim_0, isNot(35.0),
            reason: 'Initial camera should NOT be at ViewA when ViewB is specified');
      });

    testWidgets(
      'Issue #68: _cachedCamera not corrupted by stale onCameraChanged after view switch',
      (WidgetTester tester) async {
        final wrapperState = await _pumpTopographicalView(tester, startView: 'ViewA');
        final CameraController controller = _findCameraController(tester);

        expect(controller.current.dim_0, 35.0);
        expect(controller.current.dim_1, 140.0);

        wrapperState.forceViewChange('ViewB');
        await tester.pumpAndSettle();

        final CameraController afterSwitchCtrl = _findCameraController(tester);
        // Under decoupled behavior, camera remains at ViewA
        expect(afterSwitchCtrl.current.dim_0, 35.0);
        expect(afterSwitchCtrl.current.dim_1, 140.0);

        afterSwitchCtrl.pan(const Offset(50, 0));
        final double pannedLng = afterSwitchCtrl.current.dim_1;

        wrapperState.forceViewChange('ViewA');
        await tester.pumpAndSettle();

        final CameraController backCtrl = _findCameraController(tester);
        expect(backCtrl.current.dim_0, 35.0);
        expect(backCtrl.current.dim_1, pannedLng);
      });

    testWidgets(
      'Issue #68: Rapid view cycling does not corrupt _cachedCamera',
      (WidgetTester tester) async {
        final wrapperState = await _pumpTopographicalView(tester, startView: 'ViewA');

        for (int i = 0; i < 5; i++) {
          wrapperState.forceViewChange('ViewB');
          await tester.pumpAndSettle();
          final CameraController bCtrl = _findCameraController(tester);
          expect(bCtrl.current.dim_0, 35.0,
              reason: 'Cycle $i: must remain at ViewA');
          expect(bCtrl.current.dim_1, 140.0,
              reason: 'Cycle $i: must remain at ViewA');

          wrapperState.forceViewChange('ViewA');
          await tester.pumpAndSettle();
          final CameraController aCtrl = _findCameraController(tester);
          expect(aCtrl.current.dim_0, 35.0,
              reason: 'Cycle $i: must remain at ViewA');
          expect(aCtrl.current.dim_1, 140.0,
              reason: 'Cycle $i: must remain at ViewA');
        }
      });
  });

  group('Issue #44: Stale fly-to does not overwrite camera after view change', () {
    VirtualCamera _makeCamera(double lat, double lng) {
      return VirtualCamera(
        dim_0: lat,
        dim_1: lng,
        dim_2: 500.0,
        heading: 0.0,
        pitch: -45.0,
        roll: 0.0,
      );
    }

    Future<CameraController> _pumpScene3DViewport(
      WidgetTester tester, {
      required VirtualCamera camera,
      TopologyData? topologyData,
    }) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Scene3DViewport(
              camera: camera,
              topologyData: topologyData ?? _topologyData,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final state = tester.state(find.byType(Scene3DViewport)) as dynamic;
      return state.cameraController as CameraController;
    }

    testWidgets(
      'Flight animation is NOT interrupted by external camera update',
      (WidgetTester tester) async {
        final cameraA = _makeCamera(35.0, 140.0);
        final controller = await _pumpScene3DViewport(tester, camera: cameraA);

        // Initial camera at view A
        expect(controller.current.dim_0, closeTo(35.0, 0.1));
        expect(controller.current.dim_1, closeTo(140.0, 0.1));

        // Simulate double-tap to start fly-to animation
        final gestureDetectorFinder = find.descendant(
          of: find.byType(Scene3DViewport),
          matching: find.byType(GestureDetector),
        ).first;
        final gestureDetector = tester.widget<GestureDetector>(gestureDetectorFinder);
        gestureDetector.onDoubleTapDown!(TapDownDetails(globalPosition: const Offset(360, 300)));

        // Trigger first tick to set start time before advancing virtual clock
        await tester.pump();

        // Let the fly-to progress partway
        await tester.pump(const Duration(milliseconds: 100));

        // The fallback fly-to target has same lat/lng but lower dim_2.
        // Verify dim_2 is changing.
        expect(controller.current.dim_2, isNot(6378137.0 + 500.0),
            reason: 'Fly-to should have started changing from initial dim_2');
        expect(controller.current.dim_2, greaterThan(3189318.0),
            reason: 'Fly-to should not have reached target dim_2 yet');

        // External camera update: rebuild with a new camera (simulating view change)
        final cameraB = _makeCamera(50.0, -75.0);
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Scene3DViewport(
                camera: cameraB,
                topologyData: _topologyData,
              ),
            ),
          ),
        );
        await tester.pump();

        // Camera should NOT be at the B position, it should remain in flight
        expect(controller.current.dim_0, isNot(closeTo(50.0, 0.1)),
            reason: 'Camera should not jump to B dim_0');
        expect(controller.current.dim_1, isNot(closeTo(-75.0, 0.1)),
            reason: 'Camera should not jump to B dim_1');

        expect(controller.current.dim_0, closeTo(35.0, 0.1),
            reason: 'Camera should be on the flight path near 35.0 dim_0');
        expect(controller.current.dim_1, closeTo(140.0, 1.0),
            reason: 'Camera should be on the flight path near 140.0 dim_1');

        // Pump more frames - the flight continues
        for (int i = 0; i < 10; i++) {
          await tester.pump(const Duration(milliseconds: 50));
          expect(controller.current.dim_0, isNot(closeTo(50.0, 0.1)),
              reason: 'Camera should NOT jump to B dim_0 at frame $i');
          expect(controller.current.dim_1, isNot(closeTo(-75.0, 0.1)),
              reason: 'Camera should NOT jump to B dim_1 at frame $i');
        }
      });
  });

  group('_resolveCamera coordinate resolution', () {
    testWidgets(
      'resolves camera from topology node coordinates via resolveCoordinate',
      (WidgetTester tester) async {
        const data = TopologyData(
          coordinateMapping: {},
          nodes: [
            TopologyNode(
              id: 'TestNode',
              label: 'Test',
              position: TopologyNodePosition(
                dim0: 50.0,
                dim1: -75.0,
                dim2: 0.0,
                timeIndex: 0,
                vector: [],
              ),
              status: 'Active',
            ),
          ],
          links: [],
        );

        tester.view.physicalSize = const Size(800, 600);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        await tester.pumpWidget(
          ChangeNotifierProvider<ThemeController>(
            create: (_) => ThemeController(EphemeralThemeService()),
            child: MaterialApp(
              home: Scaffold(
                body: TopographicalView(
                  currentView: 'TestNode',
                  onViewSelected: (_) {},
                  topologyData: data,
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final viewportState = tester.state(find.byType(Scene3DViewport)) as dynamic;
        final CameraController controller = viewportState.cameraController as CameraController;

        expect(controller.current.dim_0, -75.0);
        expect(controller.current.dim_1, 50.0);
        expect(controller.current.dim_2, 6378137.0 + 500.0);
        expect(controller.current.heading, 0.0);
        expect(controller.current.pitch, -89.9);
      });
  });
}
