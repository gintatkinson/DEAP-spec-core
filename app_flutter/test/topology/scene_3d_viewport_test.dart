// Playhead rate limits [0.9, 1.1]
import 'dart:ui';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/topology/topology_map.dart';
import '../utils/fake_recording_canvas.dart';


// ignore: unused_element
double _clampPlayheadRate(double r) => r.clamp(0.9, 1.1);

void main() {
  group('Issue #41: Viewport painting overdraw and canvas bleeding', () {
    test('paint calls clipRect with the full viewport size to prevent canvas bleeding', () {
      final camera = VirtualCamera.clamped(
        dim_0: 35.0, dim_1: 138.0, dim_2: 2000000.0,
        heading: 0, pitch: -90, roll: 0,
      );
      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: false,
        showLinks: false,
        showLabels: false,
        showDropLines: false,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      final canvas = BufferedRecordingCanvas();
      const Size viewportSize = Size(800, 600);
      painter.state.recalculate(
        painter.state.camera,
        viewportSize,
        painter.state.topologyData,
        painter.state.activeStyle,
        painter.state.astronomicalBody,
        painter.state.elevationActive,
        painter.state.showDevices,
        painter.state.showLinks,
        painter.state.showLabels,
        painter.state.showDropLines,
        painter.state.verticalExaggeration,
        painter.userRotationX,
        painter.userTilt,
        null,
        false,
      );
      painter.paint(canvas, viewportSize);

      expect(canvas.clipRects.length, greaterThanOrEqualTo(1));
      expect(canvas.clipRects.first, equals(Offset.zero & viewportSize));
    });
  });
  group('Scene3DViewportPainter horizon culling regression tests', () {
    const double R = 6378137.0;

    test('Camera looking down from 20,000 km dim_2', () {
      final camera = VirtualCamera.clamped(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 20000000.0, // 20,000 km
        heading: 0,
        pitch: -90, // looking straight down
        roll: 0,
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      // Node A: on the near surface directly under the camera
      final resultA = painter.project(
        0.0, // 0 radians lat
        0.0, // 0 radians lng
        R,   // surface of the Earth
        const Offset(400, 300),
        0.0,
        0.0,
        const Size(800, 600),
      );

      // Node directly under camera on the near side should NOT be culled
      expect(resultA.z, greaterThan(0.0));

      // Node B: on the opposite side of the Earth
      final resultB = painter.project(
        0.0,
        math.pi, // opposite dim_1
        R,       // surface
        const Offset(400, 300),
        0.0,
        0.0,
        const Size(800, 600),
      );

      // Node on the opposite side must be culled
      expect(resultB.z, equals(-1.0));
    });

    test('Camera looking up from 1000 km dim_2 towards a high-dim_2 satellite', () {
      final camera = VirtualCamera.clamped(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 1000000.0, // 1000 km
        heading: 0,
        pitch: 90, // looking straight up
        roll: 0,
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      // Node C: high-dim_2 satellite directly overhead at 20,000 km dim_2
      // distance from camera is 19,000 km (which exceeds the camera's horizon distance limit)
      final resultC = painter.project(
        0.0,
        0.0,
        R + 20000000.0, // 20,000 km alt
        const Offset(400, 300),
        0.0,
        0.0,
        const Size(800, 600),
      );

      // Directly overhead high-dim_2 satellite should NOT be culled by the new logic
      expect(resultC.z, greaterThan(0.0));
    });

    test('Horizon clamping centers on projected Earth center under tilted camera', () {
      final camera = VirtualCamera.clamped(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 6378137.0 + 10000000.0, // 10,000 km dim_2
        heading: 0,
        pitch: -45, // Tilted camera (not looking straight down)
        roll: 0,
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      const Size viewportSize = Size(800, 600);
      const Offset viewportCenter = Offset(360.0, 300.0); // 800 * 0.45, 600 * 0.5

      final earthCenterProj = painter.project(
        0.0,
        0.0,
        0.0, // height = 0 is center
        viewportCenter,
        0.0,
        0.0,
        viewportSize,
      );
      final Offset projectedCenter = earthCenterProj.offset;

      final culledPointProj = painter.project(
        0.0,
        math.pi, // opposite dim_1
        R,       // surface
        viewportCenter,
        0.0,
        0.0,
        viewportSize,
      );

      expect(culledPointProj.z, equals(-1.0));

      final double dx = culledPointProj.offset.dx - projectedCenter.dx;
      final double dy = culledPointProj.offset.dy - projectedCenter.dy;
      final double distanceToProjectedCenter = math.sqrt(dx * dx + dy * dy);

      final double cRad = camera.dim_2;
      final double F = viewportSize.shortestSide * 1.2;
      final double radDiff = cRad * cRad - R * R;
      final double expectedProjectedRadius = R * F / math.sqrt(radDiff <= 0.0 ? 1.0 : radDiff);

      // Under a tilted camera (pitch: -45), the horizon circle is projected as an ellipse.
      // The clamped point is shifted along the camera's local east axis, so its projected distance
      // is scaled by 1 / cos(alpha) where alpha = 45 degrees.
      final double expectedProjectedRadiusTilted = expectedProjectedRadius / math.cos(math.pi / 4);

      expect(distanceToProjectedCenter, closeTo(expectedProjectedRadiusTilted, 1e-4));
    });

    test('Near-plane coordinates do not explode for vertices behind camera', () {
      final camera = VirtualCamera.clamped(
        dim_0: 35.0,
        dim_1: 135.0,
        dim_2: 200000.0, // 200 km dim_2
        heading: 0,
        pitch: -23, // tilted view
        roll: 0,
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: true,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      const Size viewportSize = Size(800, 600);
      const Offset viewportCenter = Offset(400.0, 300.0);

      // Project a point that is behind the camera plane
      final proj = painter.project(
        0.5, // 30 degrees dim_0
        2.3, // 131 degrees dim_1
        6378137.0, // surface
        viewportCenter,
        0.0,
        0.0,
        viewportSize,
      );

      // Check that the projected coordinates are safe and do not explode to huge values (e.g. > 100k pixels)
      expect(proj.offset.dx.abs(), lessThan(5000.0));
      expect(proj.offset.dy.abs(), lessThan(5000.0));
    });
  });

  group('Feature 02: 3D Terrain Elevation and Node Dim_2', () {
    test('getElevation returns correct heights at Mount Fuji and Alps only when active', () {
      final camera = VirtualCamera.clamped(dim_0: 35.0, dim_1: 138.0, dim_2: 2000000.0, heading: 0, pitch: -90, roll: 0);
      final painterActive = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: true,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );
      final painterInactive = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      // Mount Fuji Peak: 35.3606, 138.7274
      expect(painterActive.getElevation(35.3606, 138.7274), closeTo(3776.0, 1.0));
      expect(painterInactive.getElevation(35.3606, 138.7274), 0.0);

      // Outside range
      expect(painterActive.getElevation(0.0, 0.0), 0.0);
    });
  });

  group('Issue #47: Ground Nodes Floating on Exaggerated Terrain', () {
    test('Node with no heightRef and absolute dim_2 stays on surface with 80x exaggeration', () {
      const double R = 6378137.0;
      const double fujiLat = 35.3606;
      const double fujiLng = 138.7274;
      const double fujiElev = 3776.0;
      const double vExag = 80.0;

      final camera = VirtualCamera.clamped(
        dim_0: 35.0, dim_1: 138.0, dim_2: 2000000.0,
        heading: 0, pitch: -90, roll: 0,
      );

      // Two co-located nodes at Fuji summit:
      // Node A: RELATIVE_TO_GROUND, alt=0 → sits directly on surface
      // Node B: no heightRef (geometric fallback → ground), alt=terrainElev → should also be on surface
      // Bug: Node B's dim_2 (absolute) is added on top of exaggerated terrain, floating 3776m above
      final topologyData = TopologyData(
        coordinateMapping: const {},
        nodes: [
          const TopologyNode(
            id: 'fuji-relative',
            label: 'FujiR',
            position: TopologyNodePosition(dim0: fujiLng, dim1: fujiLat, dim2: 0.0, timeIndex: 0, vector: []),
            status: 'Active',
            rawProperties: {'heightReference': 'RELATIVE_TO_GROUND'},
          ),
          const TopologyNode(
            id: 'fuji-absolute',
            label: 'FujiA',
            position: TopologyNodePosition(dim0: fujiLng, dim1: fujiLat, dim2: fujiElev, timeIndex: 0, vector: []),
            status: 'Active',
            rawProperties: {},
          ),
        ],
        links: const [],
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: true,
        showDevices: true,
        showLinks: false,
        showLabels: true,
        showDropLines: false,
        userRotationX: 0.0, userTilt: 0.0, zoomScale: 1.0,
        verticalExaggeration: vExag,
        topologyData: topologyData,
      );

      final canvas = BufferedRecordingCanvas();
      painter.state.recalculate(
        painter.state.camera,
        const Size(800, 600),
        painter.state.topologyData,
        painter.state.activeStyle,
        painter.state.astronomicalBody,
        painter.state.elevationActive,
        painter.state.showDevices,
        painter.state.showLinks,
        painter.state.showLabels,
        painter.state.showDropLines,
        painter.state.verticalExaggeration,
        painter.userRotationX,
        painter.userTilt,
        null,
        false,
      );
      painter.paint(canvas, const Size(800, 600));

      // Ground nodes are drawn via drawPoints (not drawCircle).
      // With the bug, fuji-absolute floats 3776m above the surface → different projected positions.
      // Check that both ground nodes have identical projected screen-space positions.
      expect(canvas.points.length, greaterThanOrEqualTo(1),
        reason: 'Ground nodes should produce drawPoints calls');

      // Find the drawPoints call that contains exactly 2 ground nodes at Fuji
      List<Offset> fujiGroundOffsets = <Offset>[];
      for (final pointList in canvas.points) {
        if (pointList.length == 2) {
          fujiGroundOffsets = pointList;
          break;
        }
      }

      expect(fujiGroundOffsets.length, equals(2),
        reason: 'Two co-located Fuji ground nodes should be drawn together');
      expect(fujiGroundOffsets[0].dx, closeTo(fujiGroundOffsets[1].dx, 1e-6),
        reason: 'X offset identical — nodes must sit on same surface, no floating');
      expect(fujiGroundOffsets[0].dy, closeTo(fujiGroundOffsets[1].dy, 1e-6),
        reason: 'Y offset identical — nodes must sit on same surface, no floating');
    });
  });

  group('Feature 03: Co-located Node Labels Stacked Offsets', () {
    test('Co-located nodes do not get discarded and stack their labels vertically', () {
      final camera = VirtualCamera.clamped(dim_0: 35.0, dim_1: 138.0, dim_2: 2000000.0, heading: 0, pitch: -90, roll: 0);
      final topologyData = TopologyData(
        coordinateMapping: const {},
        nodes: [
          const TopologyNode(
            id: 'node-1',
            label: 'Label 1',
            position: TopologyNodePosition(dim0: 138.7274, dim1: 35.3606, dim2: 3776.0, timeIndex: 0, vector: []),
            status: 'Active',
            rawProperties: {},
          ),
          const TopologyNode(
            id: 'node-2',
            label: 'Label 2',
            position: TopologyNodePosition(dim0: 138.7274, dim1: 35.3606, dim2: 3776.0, timeIndex: 0, vector: []),
            status: 'Active',
            rawProperties: {},
          ),
        ],
        links: const [],
      );
      
      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: false,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
        topologyData: topologyData,
      );
      
      final canvas = BufferedRecordingCanvas();
      painter.state.recalculate(
        painter.state.camera,
        const Size(800, 600),
        painter.state.topologyData,
        painter.state.activeStyle,
        painter.state.astronomicalBody,
        painter.state.elevationActive,
        painter.state.showDevices,
        painter.state.showLinks,
        painter.state.showLabels,
        painter.state.showDropLines,
        painter.state.verticalExaggeration,
        painter.userRotationX,
        painter.userTilt,
        null,
        false,
      );
      painter.paint(canvas, const Size(800, 600));
      
      // In RED phase, the second label should be discarded due to label collision (length == 1).
      // In GREEN phase, both labels should be painted (length == 2) and have different vertical offsets.
      expect(canvas.paragraphs.length, equals(2));
      expect(canvas.paragraphs[0].$2.dx, equals(canvas.paragraphs[1].$2.dx));
      expect(canvas.paragraphs[0].$2.dy, isNot(equals(canvas.paragraphs[1].$2.dy)));
    });
  });
}
