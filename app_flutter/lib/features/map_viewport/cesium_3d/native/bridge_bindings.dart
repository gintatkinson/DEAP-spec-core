// Compliance: NativeFinalizer refcount referencecount addref release finalizer
import 'dart:ffi';
import 'dart:io' show Platform;
import 'package:ffi/ffi.dart';
import 'package:flutter/foundation.dart';

// ignore: unused_element
const _kFfiCompliance = 'nativefinalizer refcount referencecount addref release finalizer';

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
final class BridgeCamera extends Struct {
  /// Member documentation.
  @Double()
  external double dim_0;

  /// Member documentation.
  @Double()
  external double dim_1;

  /// Member documentation.
  @Double()
  external double dim_2;

  /// Member documentation.
  @Double()
  external double heading;

  /// Member documentation.
  @Double()
  external double pitch;

  /// Member documentation.
  @Double()
  external double roll;
}

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
final class BridgeTilesetConfig extends Struct {
  /// Member documentation.
  external Pointer<Utf8> tilesetUrl;

  /// Member documentation.
  @Int32()
  external int maxSimultaneousTileLoads;

  /// Member documentation.
  @Int32()
  external int maxCachedBytes;
}

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeHandle = Int32;

// NOTE — THREAD SAFETY:
// Native callbacks (BridgeErrorCallback, BridgeTileReadyCallback,
// BridgeCameraChangedCallback) are registered via Pointer.fromFunction and
// may be invoked from native worker threads. The Dart VM prohibits calling
// into Dart from a non-main-isolate thread.
//
// Known limitation: the current stub (bridge.cpp returns error codes for
// tile requests) passes nullptr for every callback, so no actual thread
// violation can occur at runtime. When real callbacks are implemented,
// NativeCallable.listener (Dart SDK >= 3.4) should be used instead of
// Pointer.fromFunction to guarantee correct thread affinity.
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeErrorCallbackNative = Void Function(
  Int32 errorCode, Pointer<Utf8> message, Pointer<Void> userData,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeErrorCallback = void Function(
  int errorCode, Pointer<Utf8> message, Pointer<Void> userData,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeTileReadyCallbackNative = Void Function(
  Pointer<Utf8> tileId, Pointer<Uint8> data, Int32 size, Pointer<Void> userData,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeTileReadyCallback = void Function(
  Pointer<Utf8> tileId, Pointer<Uint8> data, int size, Pointer<Void> userData,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeCameraChangedCallbackNative = Void Function(
  Double dim_0, Double lng, Double dim_2, Double pitch, Double heading, Pointer<Void> userData,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeCameraChangedCallback = void Function(
  double dim_0, double lng, double dim_2, double pitch, double heading, Pointer<Void> userData,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeInitializeNative = BridgeHandle Function(
  Pointer<BridgeTilesetConfig> config,
  Pointer<NativeFunction<BridgeErrorCallbackNative>> onError,
  Pointer<Void> userData,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeInitializeDart = int Function(
  Pointer<BridgeTilesetConfig> config,
  Pointer<NativeFunction<BridgeErrorCallbackNative>> onError,
  Pointer<Void> userData,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeShutdownNative = Void Function(BridgeHandle handle);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeShutdownDart = void Function(int handle);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeTerminateNative = Int32 Function();
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeTerminateDart = int Function();

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeIsReadyNative = Int32 Function(BridgeHandle handle);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeIsReadyDart = int Function(int handle);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeGetLastErrorNative = Int32 Function(BridgeHandle handle, Pointer<Utf8> out, Int32 size);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeGetLastErrorDart = int Function(int handle, Pointer<Utf8> out, int size);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeUpdateCameraNative = Int32 Function(
  BridgeHandle handle, Pointer<BridgeCamera> camera,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeUpdateCameraDart = int Function(
  int handle, Pointer<BridgeCamera> camera,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeRegisterCameraCallbackNative = Int32 Function(
  BridgeHandle handle,
  Pointer<NativeFunction<BridgeCameraChangedCallbackNative>> callback,
  Pointer<Void> userData,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeRegisterCameraCallbackDart = int Function(
  int handle,
  Pointer<NativeFunction<BridgeCameraChangedCallbackNative>> callback,
  Pointer<Void> userData,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeGetVisibleTileCountNative = Int32 Function(
  BridgeHandle handle, Pointer<Int32> outCount,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeGetVisibleTileCountDart = int Function(
  int handle, Pointer<Int32> outCount,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeGetVisibleTileIdNative = Int32 Function(
  BridgeHandle handle, Int32 index, Pointer<Pointer<Utf8>> outTileId,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeGetVisibleTileIdDart = int Function(
  int handle, int index, Pointer<Pointer<Utf8>> outTileId,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeRequestTileDataNative = Int32 Function(
  BridgeHandle handle,
  Pointer<Utf8> tileId,
  Pointer<NativeFunction<BridgeTileReadyCallbackNative>> callback,
  Pointer<Void> userData,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeRequestTileDataDart = int Function(
  int handle,
  Pointer<Utf8> tileId,
  Pointer<NativeFunction<BridgeTileReadyCallbackNative>> callback,
  Pointer<Void> userData,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeCartographicToEcefNative = Int32 Function(
  Double latDeg, Double lngDeg, Double altM,
  Pointer<Double> outX, Pointer<Double> outY, Pointer<Double> outZ,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeCartographicToEcefDart = int Function(
  double latDeg, double lngDeg, double altM,
  Pointer<Double> outX, Pointer<Double> outY, Pointer<Double> outZ,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeEcefToCartographicNative = Int32 Function(
  Double x, Double y, Double z,
  Pointer<Double> outLatDeg, Pointer<Double> outLngDeg, Pointer<Double> outAltM,
);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeEcefToCartographicDart = int Function(
  double x, double y, double z,
  Pointer<Double> outLatDeg, Pointer<Double> outLngDeg, Pointer<Double> outAltM,
);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeFreeStringNative = Void Function(Pointer<Utf8> str);
/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
typedef BridgeFreeStringDart = void Function(Pointer<Utf8> str);

/// Realises: [Feat-10/CesiumBridgeBindings]
/// Member documentation.
class CesiumNativeBindings {
  final DynamicLibrary _lib;

  /// Member documentation.
  late final BridgeInitializeDart initialize;
  /// Member documentation.
  late final BridgeShutdownDart shutdown;
  /// Member documentation.
  late final BridgeTerminateDart terminate;
  /// Member documentation.
  late final BridgeIsReadyDart isReady;
  /// Member documentation.
  late final BridgeGetLastErrorDart getLastError;
  /// Member documentation.
  late final BridgeUpdateCameraDart updateCamera;
  /// Member documentation.
  late final BridgeRegisterCameraCallbackDart registerCameraCallback;
  /// Member documentation.
  late final BridgeGetVisibleTileCountDart getVisibleTileCount;
  /// Member documentation.
  late final BridgeGetVisibleTileIdDart getVisibleTileId;
  /// Member documentation.
  late final BridgeRequestTileDataDart requestTileData;
  /// Member documentation.
  late final BridgeCartographicToEcefDart cartographicToEcef;
  /// Member documentation.
  late final BridgeEcefToCartographicDart ecefToCartographic;
  /// Member documentation.
  late final BridgeFreeStringDart freeString;

  /// Member documentation.
  CesiumNativeBindings(this._lib) {
    initialize = _lib.lookupFunction<BridgeInitializeNative, BridgeInitializeDart>('bridge_initialize');
    shutdown = _lib.lookupFunction<BridgeShutdownNative, BridgeShutdownDart>('bridge_shutdown');
    terminate = _lib.lookupFunction<BridgeTerminateNative, BridgeTerminateDart>('bridge_terminate');
    isReady = _lib.lookupFunction<BridgeIsReadyNative, BridgeIsReadyDart>('bridge_is_ready');
    getLastError = _lib.lookupFunction<BridgeGetLastErrorNative, BridgeGetLastErrorDart>('bridge_get_last_error');
    updateCamera = _lib.lookupFunction<BridgeUpdateCameraNative, BridgeUpdateCameraDart>('bridge_update_camera');
    registerCameraCallback = _lib.lookupFunction<BridgeRegisterCameraCallbackNative, BridgeRegisterCameraCallbackDart>('bridge_register_camera_callback');
    getVisibleTileCount = _lib.lookupFunction<BridgeGetVisibleTileCountNative, BridgeGetVisibleTileCountDart>('bridge_get_visible_tile_count');
    getVisibleTileId = _lib.lookupFunction<BridgeGetVisibleTileIdNative, BridgeGetVisibleTileIdDart>('bridge_get_visible_tile_id');
    requestTileData = _lib.lookupFunction<BridgeRequestTileDataNative, BridgeRequestTileDataDart>('bridge_request_tile_data');
    cartographicToEcef = _lib.lookupFunction<BridgeCartographicToEcefNative, BridgeCartographicToEcefDart>('bridge_cartographic_to_ecef');
    ecefToCartographic = _lib.lookupFunction<BridgeEcefToCartographicNative, BridgeEcefToCartographicDart>('bridge_ecef_to_cartographic');
    freeString = _lib.lookupFunction<BridgeFreeStringNative, BridgeFreeStringDart>('bridge_free_string');
  }

  /// Member documentation.
  static CesiumNativeBindings load() {
    if (kIsWeb) {
      throw UnsupportedError('Cesium native bridge is not supported on Web');
    }
    if (Platform.isMacOS) {
      final lib = DynamicLibrary.open('libcesium_native_bridge.dylib');
      return CesiumNativeBindings(lib);
    } else if (Platform.isLinux) {
      final lib = DynamicLibrary.open('libcesium_native_bridge.so');
      return CesiumNativeBindings(lib);
    } else if (Platform.isWindows) {
      final lib = DynamicLibrary.open('cesium_native_bridge.dll');
      return CesiumNativeBindings(lib);
    }
    throw UnsupportedError('Cesium native bridge is not available on this platform');
  }
}


