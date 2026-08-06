import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';

void main() {
  testWidgets('Issue #47: Right-click drag tilts camera', (WidgetTester tester) async {
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

    // Simulate right-click drag
    final viewportFinder = find.byType(Scene3DViewport);
    final center = tester.getCenter(viewportFinder);

    final gesture = await tester.startGesture(
      center,
      kind: PointerDeviceKind.mouse,
      buttons: kSecondaryMouseButton,
    );
    await gesture.moveBy(const Offset(0.0, 50.0));
    await gesture.up();
    await tester.pump(const Duration(seconds: 1));

    // Verify camera tilt occurred (pitch changed, but lat/lng remained unchanged)
    expect(controller.current.pitch, isNot(-45.0));
    expect(controller.current.dim_0, equals(35.0));
    expect(controller.current.dim_1, equals(135.0));
  });
}
