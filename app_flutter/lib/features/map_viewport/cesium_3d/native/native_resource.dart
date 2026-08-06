import 'dart:ffi';
import 'package:ffi/ffi.dart';

final _finalizer = NativeFinalizer(calloc.nativeFree);

/// Wrapper around native memory allocation managing lifecycle and finalizers.
///
/// Realises: [Feat-10/NativeResource]
final class NativeResource implements Finalizable {
  Pointer<Void> _pointer;
  /// Member documentation.
  final int sizeBytes;
  bool _isReleased = false;

  /// Member documentation.
  bool get isReleased => _isReleased;

  /// Member documentation.
  Pointer<Void> get pointer {
    if (_isReleased) {
      throw StateError('Cannot access pointer after NativeResource has been released.');
    }
    return _pointer;
  }

  NativeResource._(this._pointer, this.sizeBytes) {
    _finalizer.attach(this, _pointer, detach: this, externalSize: sizeBytes);
  }

  /// Member documentation.
  factory NativeResource.alloc(int count, int elementSize) {
    if (count <= 0 || elementSize <= 0) {
      throw ArgumentError('Count and element size must be positive.');
    }
    if (count > 0x7FFFFFFFFFFFFFFF ~/ elementSize) {
      throw ArgumentError('Allocation size overflow.');
    }
    final totalSize = count * elementSize;
    final ptr = calloc<Int8>(totalSize);
    if (ptr == nullptr) {
      throw OutOfMemoryError();
    }
    return NativeResource._(ptr.cast(), totalSize);
  }

  /// Member documentation.
  void release() {
    if (_isReleased) return;
    _isReleased = true;
    _finalizer.detach(this);
    calloc.free(_pointer);
    _pointer = nullptr;
  }
}
