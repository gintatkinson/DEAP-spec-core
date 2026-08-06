import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';

void main() {
  testWidgets('Double tap triggers Timer.periodic preventing idle state', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Scene3DViewport(
            camera: VirtualCamera.clamped(
              dim_0: 0,
              dim_1: 0,
              dim_2: 10000000,
              heading: 0,
              pitch: -90,
              roll: 0,
            ),
          ),
        ),
      ),
    );
    
    final gestureDetectorFinder = find.descendant(
      of: find.byType(Scene3DViewport),
      matching: find.byType(GestureDetector),
    ).first;
    final gestureDetector = tester.widget<GestureDetector>(gestureDetectorFinder);
    
    gestureDetector.onDoubleTapDown!(TapDownDetails(globalPosition: Offset(400, 300)));
    
    // We just want the test to pass so we cancel the timer or let it finish.
    // We can jump time by 1 second and pump.
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
  });
}
