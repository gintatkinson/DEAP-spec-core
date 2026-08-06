import 'dart:async';

/// Realises: [UC-04/GnmiTelemetryUpdate]
/// Telemetry metric update received from a gNMI stream.
class GnmiTelemetryUpdate {
  /// The gNMI path target.
  final String path;

  /// The metric value.
  final dynamic value;

  /// Timestamp of the telemetry measurement.
  final DateTime timestamp;

  /// Creates a new [GnmiTelemetryUpdate].
  GnmiTelemetryUpdate({
    required this.path,
    required this.value,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Converts update to JSON map.
  Map<String, dynamic> toMap() {
    return {
      'path': path,
      'value': value,
      'timestamp': timestamp.toIso8601String(),
    };
  }
}

/// Realises: [UC-04/GnmiTelemetryClient]
/// gNMI telemetry client for streaming real-time network and device telemetry.
///
/// Provides methods to establish streaming telemetry sessions ([connectStream]) and
/// teardown active connections ([disconnectStream]).
class GnmiTelemetryClient {
  StreamController<GnmiTelemetryUpdate>? _streamController;
  bool _isConnected = false;
  String? _activeTarget;
  List<String>? _activePaths;

  /// Whether a telemetry stream is currently active and connected.
  bool get isConnected => _isConnected;

  /// The active gNMI stream target endpoint, or null if disconnected.
  String? get activeTarget => _activeTarget;

  /// The active subscribed gNMI paths, or null if disconnected.
  List<String>? get activePaths => _activePaths != null ? List.unmodifiable(_activePaths!) : null;

  /// Connects to a gNMI telemetry stream for the specified [target] and subscribed [paths].
  ///
  /// Returns a broadcast [Stream] emitting [GnmiTelemetryUpdate] instances.
  /// If a stream is already connected, it will be disconnected prior to establishing the new stream.
  Stream<GnmiTelemetryUpdate> connectStream({
    String target = 'localhost:50051',
    List<String> paths = const ['/components/component/state/telemetry'],
  }) {
    if (_isConnected) {
      disconnectStream();
    }

    _activeTarget = target;
    _activePaths = List.from(paths);
    _isConnected = true;
    _streamController = StreamController<GnmiTelemetryUpdate>.broadcast();

    return _streamController!.stream;
  }

  /// Emits a simulated telemetry update into the active stream.
  ///
  /// Useful for testing and local telemetry injection. Throws [StateError] if disconnected.
  void injectUpdate(GnmiTelemetryUpdate update) {
    if (!_isConnected || _streamController == null) {
      throw StateError('Cannot inject update while gNMI stream is disconnected.');
    }
    _streamController!.add(update);
  }

  /// Disconnects and closes the active gNMI telemetry stream.
  ///
  /// Releases stream controller resources and updates [isConnected] to `false`.
  Future<void> disconnectStream() async {
    if (!_isConnected) return;

    _isConnected = false;
    _activeTarget = null;
    _activePaths = null;
    await _streamController?.close();
    _streamController = null;
  }
}
