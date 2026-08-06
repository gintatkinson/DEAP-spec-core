/// Thrown when coordinate validation fails.
///
/// Realises: [Feat-10/CoordinateValidationException]
class CoordinateValidationException implements Exception {
  /// Member documentation.
  final String message;

  /// Member documentation.
  CoordinateValidationException(this.message);

  @override
  String toString() => 'CoordinateValidationException: $message';
}

/// Reference ellipsoid dimensions and constants.
///
/// Realises: [Feat-10/Ellipsoid]
class Ellipsoid {
  /// Member documentation.
  static const double wgs84EquatorialRadius = 6378137.0;
}

/// Altitude mode for positioning objects relative to terrain.
///
/// Realises: [Feat-10/AltitudeMode]
enum AltitudeMode {
  /// Member documentation.
  absolute,
  /// Member documentation.
  clampToGround,
  /// Member documentation.
  relativeToGround,
}

/// Represents virtual 3D camera state including position (dim_0, dim_1, dim_2) and orientation (heading, pitch, roll).
///
/// Realises: [Feat-10/VirtualCamera]
class VirtualCamera {
  /// Member documentation.
  final double dim_0;
  /// Member documentation.
  final double dim_1;
  /// Member documentation.
  final double dim_2;
  /// Member documentation.
  final double heading;
  /// Member documentation.
  final double pitch;
  /// Member documentation.
  final double roll;

  /// Public factory constructor preserving runtime exception behavior.
  factory VirtualCamera({
    required double dim_0,
    required double dim_1,
    required double dim_2,
    required double heading,
    required double pitch,
    required double roll,
  }) {
    if (dim_0.isNaN || dim_0.isInfinite ||
        dim_1.isNaN || dim_1.isInfinite ||
        dim_2.isNaN || dim_2.isInfinite ||
        heading.isNaN || heading.isInfinite ||
        pitch.isNaN || pitch.isInfinite ||
        roll.isNaN || roll.isInfinite) {
      throw CoordinateValidationException('Coordinates and orientation values must be finite numbers.');
    }
    if (dim_0 < -90.0 || dim_0 > 90.0) {
      throw CoordinateValidationException('Latitude must be in the range [-90.0, 90.0].');
    }
    if (dim_1 < -180.0 || dim_1 > 180.0) {
      throw CoordinateValidationException('Longitude must be in the range [-180.0, 180.0].');
    }
    if (dim_2 < -100.0) {
      throw CoordinateValidationException('Altitude must be greater than or equal to -100.0 meters.');
    }
    return VirtualCamera.raw(
      dim_0: dim_0,
      dim_1: dim_1,
      dim_2: dim_2,
      heading: heading,
      pitch: pitch,
      roll: roll,
    );
  }

  /// Internal const constructor for compile-time optimization.
  const VirtualCamera.raw({
    required this.dim_0,
    required this.dim_1,
    required this.dim_2,
    required this.heading,
    required this.pitch,
    required this.roll,
  });

  /// A static constant representing a default camera at origin.
  static const zero = VirtualCamera.raw(
    dim_0: 0.0,
    dim_1: 0.0,
    dim_2: 0.0,
    heading: 0.0,
    pitch: 0.0,
    roll: 0.0,
  );

  /// Creates a copy of VirtualCamera with clamped values if they exceed boundaries.
  /// Clamps dim_2 to at least -100.0, dim_0 to [-90, 90], and dim_1 to [-180, 180].
  factory VirtualCamera.clamped({
    required double dim_0,
    required double dim_1,
    required double dim_2,
    required double heading,
    required double pitch,
    required double roll,
  }) {
    final double val_dim_0 = (dim_0.isNaN || dim_0.isInfinite) ? 0.0 : dim_0;
    final double val_dim_1 = (dim_1.isNaN || dim_1.isInfinite) ? 0.0 : dim_1;
    final double val_dim_2 = (dim_2.isNaN || dim_2.isInfinite) ? 0.0 : dim_2;
    final double head = (heading.isNaN || heading.isInfinite) ? 0.0 : heading;
    final double pit = (pitch.isNaN || pitch.isInfinite) ? 0.0 : pitch;
    final double rl = (roll.isNaN || roll.isInfinite) ? 0.0 : roll;

    final double clampedLat = val_dim_0.clamp(-90.0, 90.0);
    final double clampedLng = val_dim_1.clamp(-180.0, 180.0);
    final double clampedAlt = val_dim_2 < -100.0 ? -100.0 : val_dim_2;
    return VirtualCamera(
      dim_0: clampedLat,
      dim_1: clampedLng,
      dim_2: clampedAlt,
      heading: head,
      pitch: pit,
      roll: rl,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    if (other is! VirtualCamera) return false;
    return other.dim_0 == dim_0 &&
        other.dim_1 == dim_1 &&
        other.dim_2 == dim_2 &&
        other.heading == heading &&
        other.pitch == pitch &&
        other.roll == roll;
  }

  /// Member documentation.
  bool isSpatiallyEquivalentTo(
    VirtualCamera other, {
    double epsilonCoordinate = 1e-7,
    double epsilonAltitude = 1e-3,
    double epsilonOrientation = 1e-3,
  }) {
    if (identical(this, other)) return true;
    return (dim_0 - other.dim_0).abs() <= epsilonCoordinate &&
           (dim_1 - other.dim_1).abs() <= epsilonCoordinate &&
           (dim_2 - other.dim_2).abs() <= epsilonAltitude &&
           (heading - other.heading).abs() <= epsilonOrientation &&
           (pitch - other.pitch).abs() <= epsilonOrientation &&
           (roll - other.roll).abs() <= epsilonOrientation;
  }

  @override
  int get hashCode => Object.hash(dim_0, dim_1, dim_2, heading, pitch, roll);

  @override
  String toString() {
    return 'VirtualCamera(dim_0: $dim_0, dim_1: $dim_1, dim_2: $dim_2, heading: $heading, pitch: $pitch, roll: $roll)';
  }
}
