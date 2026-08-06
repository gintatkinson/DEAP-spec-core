import 'dart:async';
import 'dart:isolate';
import 'dart:math' as math;

/// Simple worker isolate wrapper.
/// Realises: [Feat-10/BackgroundWorker]
class BackgroundWorker {
  Timer? _timer;
  int _counter = 0;
  int? _lastResult;
  final StreamController<int> _controller = StreamController<int>.broadcast();
  bool _isDisposed = false;

  /// Member documentation.
  Stream<int> get results => _controller.stream;
  /// Member documentation.
  int? get lastResult => _lastResult;

  /// Member documentation.
  void start() {
    stop();
    _isDisposed = false;
    _timer = Timer.periodic(const Duration(seconds: 3), (_) {
      _counter++;
      _runCalculation(_counter.toDouble());
    });
  }

  Future<void> _runCalculation(double value) async {
    if (_timer == null || _isDisposed) return;
    try {
      final result = await Isolate.run(() {
        double sum = 0.0;
        for (int i = 0; i < 1000000; i++) {
          sum += math.sin(value + i);
        }
        return sum.round();
      });
      if (_timer == null || _isDisposed) return;
      _lastResult = result;
      if (!_controller.isClosed) {
        _controller.add(result);
      }
    } catch (e) {
      if (_timer == null || _isDisposed) return;
      double sum = 0.0;
      const chunkSize = 10000;
      for (int i = 0; i < 1000000; i += chunkSize) {
        if (_timer == null || _isDisposed) return;
        await Future.delayed(Duration.zero);
        for (int j = 0; j < chunkSize && (i + j) < 1000000; j++) {
          sum += math.sin(value + i + j);
        }
      }
      if (_timer == null || _isDisposed) return;
      _lastResult = sum.round();
      if (!_controller.isClosed) {
        _controller.add(sum.round());
      }
    }
  }

  /// Member documentation.
  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  /// Member documentation.
  void dispose() {
    _isDisposed = true;
    stop();
    _controller.close();
  }
}
