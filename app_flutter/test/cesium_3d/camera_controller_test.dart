import 'package:flutter_test/flutter_test.dart';
import 'package:clock/clock.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';

void main() {
  group('CameraController', () {
    VirtualCamera _makeCam({
      double lat = 35.0,
      double lng = 135.0,
      double alt = 500.0,
      double heading = 0.0,
      double pitch = 0.0,
      double roll = 0.0,
    }) {
      return VirtualCamera.clamped(
        dim_0: lat,
        dim_1: lng,
        dim_2: alt,
        heading: heading,
        pitch: pitch,
        roll: roll,
      );
    }

    test('pan changes lat/lng', () {
      final c = CameraController(_makeCam());
      c.pan(const Offset(100, 50));
      final cam = c.current;
      expect(cam.dim_1, lessThan(135.0));
      expect(cam.dim_0, lessThan(35.0));
    });

    test('pan left (negative dx) increases dim_1', () {
      final c = CameraController(_makeCam(lng: 135.0));
      final before = c.current.dim_1;
      c.pan(const Offset(-200, 0));
      final after = c.current;
      expect(after.dim_1, greaterThan(before));
      expect(after.dim_0, equals(35.0));
      expect(after.dim_2, equals(6378137.0 + 500.0));
      expect(after.pitch, equals(0.0));
      expect(after.heading, equals(0.0));
    });

    test('pan up (negative dy) increases dim_0', () {
      final c = CameraController(_makeCam(lat: 35.0));
      final before = c.current.dim_0;
      c.pan(const Offset(0, -100));
      final after = c.current;
      expect(after.dim_0, greaterThan(before));
      expect(after.dim_1, equals(135.0));
      expect(after.dim_2, equals(6378137.0 + 500.0));
    });

    test('pan with pixel-accurate precision', () {
      final c = CameraController(_makeCam(lat: 0.0, lng: 0.0));
      c.pan(const Offset(100, 100));
      expect(c.current.dim_1, closeTo(-1.75638, 0.0001));
      expect(c.current.dim_0, closeTo(-1.75638, 0.0001));
    });

    test('pan clamps dim_0 to [-90, 90]', () {
      final c = CameraController(_makeCam(lat: 85.0));
      c.pan(const Offset(0, -1000000.0));
      expect(c.current.dim_0, equals(90.0));
    });

    test('pan wraps dim_1 past 180', () {
      final c = CameraController(_makeCam(lng: 175.0));
      c.pan(const Offset(-1000.0, 0));
      expect(c.current.dim_1, lessThan(-160.0));
    });

    test('tilt changes pitch/heading, not lat/lng', () {
      final c = CameraController(_makeCam(pitch: -45));
      final before = c.current;
      c.tilt(const Offset(0, 100));
      final after = c.current;
      expect(after.pitch, lessThan(before.pitch));
      expect(after.dim_0, equals(before.dim_0));
      expect(after.dim_1, equals(before.dim_1));
    });

    test('rotateHeading changes heading only', () {
      final c = CameraController(_makeCam());
      c.rotateHeading(const Offset(100, 50));
      final after = c.current;
      expect(after.heading, isNot(0));
      expect(after.dim_0, equals(35.0));
      expect(after.pitch, equals(0.0));
    });

    test('shift+drag (tilt) modifies pitch and heading, not lat/lng', () {
      final c = CameraController(_makeCam(pitch: -45, heading: 90));
      final before = c.current;
      c.tilt(const Offset(20, 80));
      final after = c.current;
      expect(after.pitch, isNot(before.pitch));
      expect(after.heading, isNot(before.heading));
      expect(after.dim_0, equals(before.dim_0));
      expect(after.dim_1, equals(before.dim_1));
    });

    test('ctrl+drag (rotateHeading) modifies heading, not lat/lng/pitch', () {
      final c = CameraController(_makeCam(pitch: -30));
      final before = c.current;
      c.rotateHeading(const Offset(50, 100));
      final after = c.current;
      expect(after.heading, isNot(before.heading));
      expect(after.dim_0, equals(before.dim_0));
      expect(after.dim_1, equals(before.dim_1));
      expect(after.pitch, equals(before.pitch));
    });

    test('zoom changes dim_2', () {
      final c = CameraController(_makeCam());
      c.zoom(-200);
      expect(c.current.dim_2, lessThan(6378137.0 + 500.0));
    });

    test('heading wraps at 360', () {
      final c = CameraController(_makeCam(heading: 358));
      c.rotateHeading(const Offset(100, 0));
      expect(c.current.heading, lessThan(360));
      expect(c.current.heading, greaterThan(340));
    });

    test('dim_1 wraps around -180/+180 boundary', () {
      final c = CameraController(_makeCam(lng: -175));
      c.pan(const Offset(1000.0, 0));
      expect(c.current.dim_1, lessThan(180));
      expect(c.current.dim_1, greaterThan(155));
    });

    test('keyboardRotate changes dim_1 only', () {
      final c = CameraController(_makeCam());
      c.keyboardRotate(10);
      expect(c.current.dim_1, equals(145.0));
      expect(c.current.dim_0, equals(35.0));
    });

    test('keyboardRotateHeading changes heading only', () {
      final c = CameraController(_makeCam());
      c.keyboardRotateHeading(10);
      expect(c.current.heading, equals(10.0));
      expect(c.current.dim_1, equals(135.0));
      expect(c.current.dim_0, equals(35.0));
    });

    test('keyboardTilt changes pitch only', () {
      final c = CameraController(_makeCam());
      c.keyboardTilt(5);
      expect(c.current.pitch, equals(5.0));
    });

    test('zoom clamps to minAltitude', () {
      final c = CameraController(_makeCam(alt: 200));
      c.zoom(-10000);
      expect(c.current.dim_2, equals(6378137.0 + CameraController.minAltitude));
    });

    test('zoom clamps to maxAltitude', () {
      final c = CameraController(_makeCam());
      c.zoom(1000000000);
      expect(c.current.dim_2, equals(6378137.0 + CameraController.maxAltitude));
    });

    group('Scroll zoom behavior', () {
      test('negative delta decreases dim_2 (scroll up = zoom in)', () {
        final c = CameraController(_makeCam(alt: 500000));
        c.zoom(-100);
        expect(c.current.dim_2, lessThan(6378137.0 + 500000));
      });

      test('positive delta increases dim_2 (scroll down = zoom out)', () {
        final c = CameraController(_makeCam(alt: 500000));
        c.zoom(100);
        expect(c.current.dim_2, greaterThan(6378137.0 + 500000));
      });

      test('zoom respects scrollSensitivity', () {
        final c = CameraController(_makeCam(alt: 500000));
        c.zoom(-1);
        expect(c.current.dim_2, closeTo(6378137.0 + 500000 - CameraController.scrollSensitivity, 0.01));
        c.zoom(1);
        expect(c.current.dim_2, closeTo(6378137.0 + 500000, 0.01));
      });

      test('zoom does not affect lat/lng/pitch/heading', () {
        final c = CameraController(_makeCam(lat: 35, lng: 135, pitch: -45, heading: 90));
        final before = c.current;
        c.zoom(-200);
        final after = c.current;
        expect(after.dim_0, equals(before.dim_0));
        expect(after.dim_1, equals(before.dim_1));
        expect(after.pitch, equals(before.pitch));
        expect(after.heading, equals(before.heading));
      });

      test('small scroll delta produces visible dim_2 change', () {
        final c = CameraController(_makeCam(alt: 500000));
        c.zoom(-10);
        expect(c.current.dim_2, closeTo(6378137.0 + 500000 - 5.0, 0.01));
      });

      test('scroll up from minAltitude stays at minAltitude', () {
        final c = CameraController(_makeCam(alt: CameraController.minAltitude));
        c.zoom(-1);
        expect(c.current.dim_2, equals(6378137.0 + CameraController.minAltitude));
      });

      test('scroll down from maxAltitude stays at maxAltitude', () {
        final c = CameraController(_makeCam(alt: 6378137.0 + CameraController.maxAltitude));
        c.zoom(1);
        expect(c.current.dim_2, equals(6378137.0 + CameraController.maxAltitude));
      });
    });

    test('keyboardTilt wraps pitch past 180', () {
      final c = CameraController(_makeCam(pitch: 175));
      c.keyboardTilt(10);
      expect(c.current.pitch, equals(-175.0));
    });

    test('keyboardTilt wraps pitch past -180', () {
      final c = CameraController(_makeCam(pitch: -175));
      c.keyboardTilt(-10);
      expect(c.current.pitch, equals(175.0));
    });

    test('Enhanced flight path midpoint boost and destination arrival', () {
      DateTime time = DateTime(2026, 7, 19, 12, 0, 0);
      withClock(Clock(() => time), () {
        final start = VirtualCamera.clamped(
          dim_0: 35.6,
          dim_1: 135.0,
          dim_2: 6378137.0 + 500.0,
          heading: 0.0,
          pitch: 0.0,
          roll: 0.0,
        );
        final target = VirtualCamera.clamped(
          dim_0: 40.7,
          dim_1: -74.0,
          dim_2: 6378137.0 + 500.0,
          heading: 0.0,
          pitch: 0.0,
          roll: 0.0,
        );

        final controller = CameraController(start);
        controller.flyTo(target);
        controller.tick(); // lazy-initialize _animationStart to current mock time

        final duration = controller.flightDurationForTesting;
        expect(duration.inMilliseconds, greaterThan(500));

        final halfDurationMs = duration.inMilliseconds ~/ 2;
        time = time.add(Duration(milliseconds: halfDurationMs));

        final arrivedMid = controller.tick();
        expect(arrivedMid, isFalse);
        expect(controller.current.dim_2 - 6378137.0, greaterThan(1000000.0));

        final remainingMs = duration.inMilliseconds - halfDurationMs;
        time = time.add(Duration(milliseconds: remainingMs));

        final arrivedEnd = controller.tick();
        expect(arrivedEnd, isTrue);
        expect(controller.current.dim_0, closeTo(40.7, 0.001));
        expect(controller.current.dim_1, closeTo(-74.0, 0.001));
        expect(controller.current.dim_2 - 6378137.0, closeTo(500.0, 0.1));
      });
    });
  });

  group('VirtualCamera equality', () {
    test('identical cameras compare equal', () {
      final a = VirtualCamera(dim_0: 35, dim_1: 135, dim_2: 500, heading: 0, pitch: -45, roll: 0);
      final b = VirtualCamera(dim_0: 35, dim_1: 135, dim_2: 500, heading: 0, pitch: -45, roll: 0);
      expect(a, equals(b));
    });
    test('different values compare not equal', () {
      final a = VirtualCamera(dim_0: 35, dim_1: 135, dim_2: 500, heading: 0, pitch: -45, roll: 0);
      final b = VirtualCamera(dim_0: 36, dim_1: 135, dim_2: 500, heading: 0, pitch: -45, roll: 0);
      expect(a, isNot(equals(b)));
    });
  });
}
