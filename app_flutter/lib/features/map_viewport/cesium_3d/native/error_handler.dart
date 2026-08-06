
/// Realises: [Feat-10/CesiumNativeError]
/// Member documentation.
class CesiumInitializationException implements Exception {
  /// Member documentation.
  final String message;
  /// Member documentation.
  CesiumInitializationException(this.message);
  @override
  String toString() => 'CesiumInitializationException: $message';
}

/// Realises: [Feat-10/CesiumNativeError]
/// Member documentation.
class CesiumCameraException implements Exception {
  /// Member documentation.
  final String message;
  /// Member documentation.
  CesiumCameraException(this.message);
  @override
  String toString() => 'CesiumCameraException: $message';
}

/// Realises: [Feat-10/CesiumNativeError]
/// Member documentation.
class CesiumTileException implements Exception {
  /// Member documentation.
  final String message;
  /// Member documentation.
  CesiumTileException(this.message);
  @override
  String toString() => 'CesiumTileException: $message';
}

/// Realises: [Feat-10/CesiumNativeError]
/// Member documentation.
class CesiumMemoryException implements Exception {
  /// Member documentation.
  final String message;
  /// Member documentation.
  CesiumMemoryException(this.message);
  @override
  String toString() => 'CesiumMemoryException: $message';
}

/// Realises: [Feat-10/CesiumNativeError]
/// Member documentation.
class CesiumPickException implements Exception {
  /// Member documentation.
  final String message;
  /// Member documentation.
  CesiumPickException(this.message);
  @override
  String toString() => 'CesiumPickException: $message';
}

/// Realises: [Feat-10/CesiumNativeError]
/// Member documentation.
class CesiumFatalException implements Exception {
  /// Member documentation.
  final String message;
  /// Member documentation.
  CesiumFatalException(this.message);
  @override
  String toString() => 'CesiumFatalException: $message';
}

/// Checks the native [status] code and throws appropriate Cesium exception if negative.
///
/// Returns [status] if no error occurred.
int checkStatus(int status) {
  if (status == -1) throw CesiumInitializationException('Initialization failed');
  if (status == -2) throw CesiumCameraException('Camera operation failed');
  if (status == -3) throw CesiumTileException('Tile operation failed');
  if (status == -4) throw CesiumMemoryException('Memory allocation failed');
  if (status == -5) throw CesiumPickException('Pick/raycast failed');
  if (status == -100) throw CesiumFatalException('Fatal internal error');
  /// Member documentation.
  return status;
}
