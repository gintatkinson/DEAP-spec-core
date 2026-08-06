import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';

void main() {
  testWidgets('Issue #48: Ctrl+drag rotates camera heading', (WidgetTester tester) async {
    final camera = VirtualCamera(
      dim_0: 35.0,
      dim_1: 135.0,
      dim_2: 1000.0,
      heading: 0.0,
      pitch: -45.0,
      roll: 0.0,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Scene3DViewport(
            camera: camera,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final state = tester.state(find.byType(Scene3DViewport)) as dynamic;
    final CameraController controller = state.cameraController as CameraController;

    // Simulate key down event for Control key
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.pump();

    // Perform drag gesture
    final viewportFinder = find.byType(Scene3DViewport);
    await tester.drag(viewportFinder, const Offset(50.0, 0.0));
    await tester.pump(const Duration(seconds: 1));

    // Simulate key up event for Control key
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await tester.pump();

    // Verify camera heading rotated (heading changed, but lat/lng/pitch remained unchanged)
    expect(controller.current.heading, isNot(0.0));
    expect(controller.current.dim_0, equals(35.0));
    expect(controller.current.dim_1, equals(135.0));
    expect(controller.current.pitch, equals(-45.0));
  });
}
