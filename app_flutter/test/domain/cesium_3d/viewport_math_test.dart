import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport_classes.dart';

void main() {
  group('VirtualCameraNormalization', () {
    test('toAbsoluteWgs84 normalizes relative dim_2', () {
      final camera = VirtualCamera.raw(
        dim_0: 0,
        dim_1: 0,
        dim_2: 500.0,
        heading: 0,
        pitch: 0,
        roll: 0,
      );
      final absoluteCamera = camera.toAbsoluteWgs84();
      expect(absoluteCamera.dim_2, Ellipsoid.wgs84EquatorialRadius + 500.0);
    });

    test('toAbsoluteWgs84 retains absolute dim_2', () {
      final camera = VirtualCamera.raw(
        dim_0: 0,
        dim_1: 0,
        dim_2: 10000000.0,
        heading: 0,
        pitch: 0,
        roll: 0,
      );
      final absoluteCamera = camera.toAbsoluteWgs84();
      expect(absoluteCamera, same(camera));
    });
  });

  group('ElevationProvider', () {
    test('returns exactly 0.0 when inactive', () {
      final provider = const ElevationProvider(isElevationActive: false);
      expect(provider.getElevation(35.3606, 138.7274), 0.0);
    });

    test('simulates Mount Fuji elevation', () {
      final provider = const ElevationProvider(isElevationActive: true);
      final elevation = provider.getElevation(35.3606, 138.7274);
      expect(elevation, 3776.0);
    });

    test('applies vertical exaggeration', () {
      final provider = const ElevationProvider(isElevationActive: true, verticalExaggeration: 2.0);
      final elevation = provider.getElevation(35.3606, 138.7274);
      expect(elevation, 3776.0 * 2.0);
    });
  });

  group('CoordinateTransformer', () {
    test('initializes precomputations without errors', () {
      final camera = VirtualCamera.raw(
        dim_0: 0,
        dim_1: 0,
        dim_2: 10000.0,
        heading: 0,
        pitch: 0,
        roll: 0,
      );
      
      expect(
        () => CoordinateTransformer(
          camera: camera,
          viewportSize: const Size(800, 600),
          screenCenter: const Offset(400, 300),
          rotationAngle: 0.0,
          tilt: 0.0,
        ),
        returnsNormally,
      );
    });

    test('projects geocoordinate behind horizon as culled', () {
      final camera = VirtualCamera.raw(
        dim_0: 0,
        dim_1: 0,
        dim_2: 10000.0,
        heading: 0,
        pitch: -90.0,
        roll: 0,
      );
      
      final transformer = CoordinateTransformer(
        camera: camera,
        viewportSize: const Size(800, 600),
        screenCenter: const Offset(400, 300),
        rotationAngle: 0.0,
        tilt: 0.0,
      );
      
      final point = transformer.projectWgs84ToScreen(
        latRad: 0.0,
        lngRad: math.pi,
        heightMeters: 0.0,
      );
      
      expect(point.z, lessThan(0.0));
    });

    test('direct line of sight maps to center', () {
      final camera = VirtualCamera.raw(
        dim_0: 0,
        dim_1: 0,
        dim_2: 10000.0,
        heading: 0,
        pitch: -90.0,
        roll: 0,
      );
      
      final transformer = CoordinateTransformer(
        camera: camera,
        viewportSize: const Size(800, 600),
        screenCenter: const Offset(400, 300),
        rotationAngle: 0.0,
        tilt: 0.0,
      );
      
      final point = transformer.projectWgs84ToScreen(
        latRad: 0.0,
        lngRad: 0.0,
        heightMeters: 0.0,
      );
      
      expect(point.offset.dx, closeTo(400.0, 1e-5));
      expect(point.offset.dy, closeTo(300.0, 1e-5));
    });
  });
}
