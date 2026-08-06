import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:clock/clock.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';

/// Controls virtual camera movements, flight animations, and user interactions for 3D map viewports.
///
/// Realises: [Feat-10/CameraController]
class CameraController extends ChangeNotifier {
  VirtualCamera _camera;

  VirtualCamera? _startCamera;
  VirtualCamera? _targetCamera;
  DateTime? _animationStart;
  Duration _flightDuration = const Duration(milliseconds: 500);

  /// Member documentation.
  @visibleForTesting
  Duration get flightDurationForTesting => _flightDuration;

  /// Member documentation.
  static const double dragSensitivity = 0.15;
  /// Member documentation.
  static const double scrollSensitivity = 0.5;
  /// Member documentation.
  static const double keyboardStep = 5.0;
  /// Member documentation.
  static const double minAltitude = 100.0;
  /// Member documentation.
  static const double maxAltitude = 40000000.0;

  /// Member documentation.
  double Function(double dim_0, double lng)? elevationProvider;

  double _getTerrainHeight(double dim_0, double lng) {
    if (elevationProvider == null) return 0.0;
    return elevationProvider!(dim_0, lng);
  }

  double _clampAltitudeToTerrain(double dim_0, double lng, double targetAlt) {
    final double terrainH = _getTerrainHeight(dim_0, lng);
    final double minAlt = Ellipsoid.wgs84EquatorialRadius + terrainH + minAltitude;
    return targetAlt < minAlt ? minAlt : targetAlt;
  }

  /// Member documentation.
  CameraController(VirtualCamera camera) : _camera = camera.dim_2 < Ellipsoid.wgs84EquatorialRadius ? VirtualCamera.clamped(
    dim_0: camera.dim_0,
    dim_1: camera.dim_1,
    dim_2: Ellipsoid.wgs84EquatorialRadius + camera.dim_2,
    heading: camera.heading,
    pitch: camera.pitch,
    roll: camera.roll,
  ) : camera;

  /// Member documentation.
  VirtualCamera get current => _camera;

  /// Member documentation.
  bool get isFlying => _targetCamera != null;

  /// Member documentation.
  void updateCamera(VirtualCamera camera) {
    final absoluteCamera = camera.dim_2 < Ellipsoid.wgs84EquatorialRadius ? VirtualCamera.clamped(
      dim_0: camera.dim_0,
      dim_1: camera.dim_1,
      dim_2: Ellipsoid.wgs84EquatorialRadius + camera.dim_2,
      heading: camera.heading,
      pitch: camera.pitch,
      roll: camera.roll,
    ) : camera;
    final double targetAlt = _clampAltitudeToTerrain(absoluteCamera.dim_0, absoluteCamera.dim_1, absoluteCamera.dim_2);
    final clampedCam = VirtualCamera.clamped(
      dim_0: absoluteCamera.dim_0,
      dim_1: absoluteCamera.dim_1,
      dim_2: targetAlt,
      heading: absoluteCamera.heading,
      pitch: absoluteCamera.pitch,
      roll: absoluteCamera.roll,
    );
    if (_camera == clampedCam) return;
    _camera = clampedCam;
    _targetCamera = null;
    _startCamera = null;
    notifyListeners();
  }

  static double _normalizeRadDiff(double diff) {
    if (diff.isNaN || !diff.isFinite) return 0.0;
    double wrapped = (diff + math.pi) % (2 * math.pi);
    if (wrapped < 0.0) wrapped += 2 * math.pi;
    return wrapped - math.pi;
  }

  static double _computeAngularDistance(VirtualCamera a, VirtualCamera b) {
    final double lat1 = a.dim_0 * math.pi / 180.0;
    final double lat2 = b.dim_0 * math.pi / 180.0;
    final double lon1 = a.dim_1 * math.pi / 180.0;
    final double lon2 = b.dim_1 * math.pi / 180.0;

    final double dLat = lat2 - lat1;
    final double dLon = _normalizeRadDiff(lon2 - lon1);

    final double sinDLat2 = math.sin(dLat / 2);
    final double sinDLon2 = math.sin(dLon / 2);
    final double val = sinDLat2 * sinDLat2 + math.cos(lat1) * math.cos(lat2) * sinDLon2 * sinDLon2;
    return 2 * math.asin(math.sqrt(val.clamp(0.0, 1.0)));
  }

  /// Member documentation.
  void flyTo(VirtualCamera target) {
    final double angularDistance = _computeAngularDistance(_camera, target);
    final double ms = 500.0 + (angularDistance / math.pi) * 1300.0;
    _flightDuration = Duration(milliseconds: ms.round());
    _startCamera = _camera;
    _targetCamera = target;
    _animationStart = null;
  }

  /// Member documentation.
  bool tick() {
    if (_startCamera == null || _targetCamera == null) return true;
    _animationStart ??= clock.now();
    final elapsed = clock.now().difference(_animationStart!);
    final progress =
        (elapsed.inMilliseconds / _flightDuration.inMilliseconds).clamp(0.0, 1.0);
    final t = _easeInOutCubic(progress);
    _camera = _lerpCamera(_startCamera!, _targetCamera!, t);
    notifyListeners();
    if (progress >= 1.0) {
      _camera = _targetCamera!;
      _startCamera = null;
      _targetCamera = null;
      notifyListeners();
      return true;
    }
    return false;
  }

  static double _easeInOutCubic(double t) {
    return t < 0.5 ? 4 * t * t * t : 1 - math.pow(-2 * t + 2, 3) / 2;
  }

  static VirtualCamera _lerpCamera(VirtualCamera a, VirtualCamera b, double t) {
    final double distance = _computeAngularDistance(a, b);
    final double maxBoost = (distance / math.pi) * 5000000.0;
    final double baseAltitude = a.dim_2 + (b.dim_2 - a.dim_2) * t;
    final double boostedAltitude = baseAltitude + math.sin(t * math.pi) * maxBoost;

    return VirtualCamera.clamped(
      dim_0: a.dim_0 + (b.dim_0 - a.dim_0) * t,
      dim_1: _interpolateCircular(a.dim_1, b.dim_1, t, _wrapLngStatic),
      dim_2: boostedAltitude,
      heading: _interpolateCircular(a.heading, b.heading, t, _wrapHeadingStatic),
      pitch: _interpolateCircular(a.pitch, b.pitch, t, _wrapPitchStatic),
      roll: a.roll + (b.roll - a.roll) * t,
    );
  }

  static double _interpolateCircular(double from, double to, double t, double Function(double) wrapFn) {
    double diff = to - from;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    return wrapFn(from + diff * t);
  }

  static double _wrapLngStatic(double lng) {
    if (lng.isNaN || !lng.isFinite) return 0.0;
    double wrapped = (lng + 180.0) % 360.0;
    if (wrapped < 0.0) wrapped += 360.0;
    double val = wrapped - 180.0;
    if (val == -180.0) {
      return lng >= 0.0 ? 180.0 : -180.0;
    }
    return val;
  }

  static double _wrapHeadingStatic(double heading) {
    if (heading.isNaN || !heading.isFinite) return 0.0;
    double wrapped = heading % 360.0;
    if (wrapped < 0.0) wrapped += 360.0;
    return wrapped;
  }

  /// Member documentation.
  void pan(Offset delta, [double shortestSide = 800.0]) {
    if (shortestSide <= 0.0 || shortestSide.isNaN) {
      shortestSide = 800.0;
    }
    final double factor = (_camera.dim_2 - Ellipsoid.wgs84EquatorialRadius + 500000.0) * 2.8074e-5 / shortestSide;
    final double radH = _camera.heading * math.pi / 180.0;
    final double cosH = math.cos(radH);
    final double sinH = math.sin(radH);
    final double dxAligned = delta.dx * cosH + delta.dy * sinH;
    final double dyAligned = -delta.dx * sinH + delta.dy * cosH;
    final newLat = (_camera.dim_0 - dyAligned * factor).clamp(-90.0, 90.0);
    final newLng = _wrapLng(_camera.dim_1 - dxAligned * factor);
    final double targetAlt = _clampAltitudeToTerrain(newLat, newLng, _camera.dim_2);
    _camera = VirtualCamera.clamped(
      dim_0: newLat,
      dim_1: newLng,
      dim_2: targetAlt,
      heading: _camera.heading,
      pitch: _camera.pitch,
      roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void tilt(Offset delta) {
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0, dim_1: _camera.dim_1,
      dim_2: _camera.dim_2,
      heading: _wrapHeading(_camera.heading - delta.dx * dragSensitivity),
      pitch: _wrapPitch(_camera.pitch - delta.dy * dragSensitivity),
      roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void rotateHeading(Offset delta) {
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0, dim_1: _camera.dim_1,
      dim_2: _camera.dim_2,
      heading: _wrapHeading(_camera.heading - delta.dx * dragSensitivity),
      pitch: _camera.pitch, roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void zoom(double scrollDelta) {
    final double terrainH = _getTerrainHeight(_camera.dim_0, _camera.dim_1);
    final double currentHeightAGL = _camera.dim_2 - (Ellipsoid.wgs84EquatorialRadius + terrainH);
    final double targetHeightAGL = currentHeightAGL + scrollDelta * scrollSensitivity;
    final double clampedHeightAGL = targetHeightAGL.clamp(minAltitude, maxAltitude);
    final double newAlt = Ellipsoid.wgs84EquatorialRadius + clampedHeightAGL + terrainH;
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0,
      dim_1: _camera.dim_1,
      dim_2: newAlt,
      heading: _camera.heading,
      pitch: _camera.pitch,
      roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void zoomInteractive(double scrollDelta) {
    final double clampedDelta = scrollDelta.clamp(-100.0, 100.0);
    final double factor = math.exp(clampedDelta * 0.001);
    final double terrainH = _getTerrainHeight(_camera.dim_0, _camera.dim_1);
    final double currentHeightAGL = _camera.dim_2 - (Ellipsoid.wgs84EquatorialRadius + terrainH);
    final double targetHeightAGL = currentHeightAGL * factor;
    final double clampedHeightAGL = targetHeightAGL.clamp(minAltitude, maxAltitude);
    final double newAlt = Ellipsoid.wgs84EquatorialRadius + clampedHeightAGL + terrainH;
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0,
      dim_1: _camera.dim_1,
      dim_2: newAlt,
      heading: _camera.heading,
      pitch: _camera.pitch,
      roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void keyboardRotate(double degrees) {
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0, dim_1: _wrapLng(_camera.dim_1 + degrees),
      dim_2: _camera.dim_2, heading: _camera.heading,
      pitch: _camera.pitch, roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void keyboardRotateHeading(double degrees) {
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0, dim_1: _camera.dim_1,
      dim_2: _camera.dim_2,
      heading: _wrapHeading(_camera.heading + degrees),
      pitch: _camera.pitch, roll: _camera.roll,
    );
    notifyListeners();
  }

  /// Member documentation.
  void keyboardTilt(double degrees) {
    _camera = VirtualCamera.clamped(
      dim_0: _camera.dim_0, dim_1: _camera.dim_1,
      dim_2: _camera.dim_2, heading: _camera.heading,
      pitch: _wrapPitch(_camera.pitch + degrees),
      roll: _camera.roll,
    );
    notifyListeners();
  }

  double _wrapLng(double lng) {
    if (lng.isNaN || !lng.isFinite) return 0.0;
    double wrapped = (lng + 180.0) % 360.0;
    if (wrapped < 0.0) wrapped += 360.0;
    double val = wrapped - 180.0;
    if (val == -180.0) {
      return lng >= 0.0 ? 180.0 : -180.0;
    }
    return val;
  }

  double _wrapHeading(double heading) => _wrapHeadingStatic(heading);

  double _wrapPitch(double pitch) => _wrapPitchStatic(pitch);

  static double _wrapPitchStatic(double pitch) {
    if (pitch.isNaN || !pitch.isFinite) return 0.0;
    double wrapped = (pitch + 180.0) % 360.0;
    if (wrapped < 0.0) wrapped += 360.0;
    double val = wrapped - 180.0;
    if (val == -180.0) {
      return pitch >= 0.0 ? 180.0 : -180.0;
    }
    return val;
  }

  /// Member documentation.
  @visibleForTesting
  static double wrapLngStaticForTesting(double lng) => _wrapLngStatic(lng);

  /// Member documentation.
  @visibleForTesting
  static double wrapHeadingStaticForTesting(double heading) => _wrapHeadingStatic(heading);

  /// Member documentation.
  @visibleForTesting
  double wrapLngForTesting(double lng) => _wrapLng(lng);

  /// Member documentation.
  @visibleForTesting
  static double wrapPitchStaticForTesting(double pitch) => _wrapPitchStatic(pitch);
}
