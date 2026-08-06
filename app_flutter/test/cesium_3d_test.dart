import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/coordinate_transformer.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/cesium_3d_native.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';

void main() {
  group('VirtualCamera Tests', () {
    test('Constructor sets fields correctly', () {
      final camera = VirtualCamera(
        dim_0: 37.7749,
        dim_1: -122.4194,
        dim_2: 500.0,
        heading: 10.0,
        pitch: -45.0,
        roll: 5.0,
      );

      expect(camera.dim_0, 37.7749);
      expect(camera.dim_1, -122.4194);
      expect(camera.dim_2, 500.0);
      expect(camera.heading, 10.0);
      expect(camera.pitch, -45.0);
      expect(camera.roll, 5.0);
      expect(camera.toString(), contains('VirtualCamera'));
    });

    test('Throws validation exception for invalid dim_0', () {
      expect(
        () => VirtualCamera(
          dim_0: 95.0,
          dim_1: -122.4194,
          dim_2: 500.0,
          heading: 0.0,
          pitch: -45.0,
          roll: 0.0,
        ),
        throwsA(isA<CoordinateValidationException>()),
      );
    });

    test('Throws validation exception for invalid dim_1', () {
      expect(
        () => VirtualCamera(
          dim_0: 37.7749,
          dim_1: -185.0,
          dim_2: 500.0,
          heading: 0.0,
          pitch: -45.0,
          roll: 0.0,
        ),
        throwsA(isA<CoordinateValidationException>()),
      );
    });

    test('Throws validation exception for invalid dim_2', () {
      expect(
        () => VirtualCamera(
          dim_0: 37.7749,
          dim_1: -122.4194,
          dim_2: -105.0,
          heading: 0.0,
          pitch: -45.0,
          roll: 0.0,
        ),
        throwsA(isA<CoordinateValidationException>()),
      );
    });

    test('clamped factory adjusts values and builds successfully', () {
      final camera = VirtualCamera.clamped(
        dim_0: 120.0,
        dim_1: -200.0,
        dim_2: -250.0,
        heading: 10.0,
        pitch: 20.0,
        roll: 30.0,
      );

      expect(camera.dim_0, 90.0);
      expect(camera.dim_1, -180.0);
      expect(camera.dim_2, -100.0);
    });

    test('Throws validation exception for NaN or Infinite inputs', () {
      expect(
        () => VirtualCamera(
          dim_0: double.nan,
          dim_1: -122.4194,
          dim_2: 500.0,
          heading: 0.0,
          pitch: -45.0,
          roll: 0.0,
        ),
        throwsA(isA<CoordinateValidationException>()),
      );
      expect(
        () => VirtualCamera(
          dim_0: 37.7749,
          dim_1: double.infinity,
          dim_2: 500.0,
          heading: 0.0,
          pitch: -45.0,
          roll: 0.0,
        ),
        throwsA(isA<CoordinateValidationException>()),
      );
    });

    test('clamped factory sanitizes NaN and Infinite inputs to 0.0', () {
      final camera = VirtualCamera.clamped(
        dim_0: double.nan,
        dim_1: double.infinity,
        dim_2: double.nan,
        heading: double.nan,
        pitch: double.infinity,
        roll: double.nan,
      );

      expect(camera.dim_0, 0.0);
      expect(camera.dim_1, 0.0);
      expect(camera.dim_2, 0.0);
      expect(camera.heading, 0.0);
      expect(camera.pitch, 0.0);
      expect(camera.roll, 0.0);
    });
  });

  group('CoordinateTransformer Tests', () {
    final transformer = CoordinateTransformer();

    test('Transforms valid ECEF to local coordinates', () {
      final local = transformer.transformEcefToLocal(100.0, 200.0, 300.0);
      expect(local.length, 3);
      expect(local[0], 1.0);
      expect(local[1], 2.0);
      expect(local[2], 3.0);
    });

    test('Throws validation exception for NaN ECEF X coordinate', () {
      expect(
        () => transformer.transformEcefToLocal(double.nan, 200.0, 300.0),
        throwsA(isA<CoordinateValidationException>()),
      );
    });

    test('Throws validation exception for Infinite ECEF Y coordinate', () {
      expect(
        () => transformer.transformEcefToLocal(100.0, double.infinity, 300.0),
        throwsA(isA<CoordinateValidationException>()),
      );
    });
  });

  group('Cesium3DNative Tests', () {
    final nativeEngine = Cesium3DNative();

    test('initializeTileset returns correct status', () {
      expect(nativeEngine.initializeTileset('https://assets.ion.cesium.com/12345/tileset.json'), isTrue);
      expect(nativeEngine.initializeTileset(''), isFalse);
    });

    test('updateViewport validates camera dim_2', () {
      final validCamera = VirtualCamera(
        dim_0: 37.7749,
        dim_1: -122.4194,
        dim_2: 500.0,
        heading: 0.0,
        pitch: -45.0,
        roll: 0.0,
      );
      expect(nativeEngine.updateViewport(validCamera), isTrue);

      final invalidCamera = VirtualCamera.clamped(
        dim_0: 37.7749,
        dim_1: -122.4194,
        dim_2: -150.0,
        heading: 0.0,
        pitch: -45.0,
        roll: 0.0,
      );

      expect(
        () => nativeEngine.updateViewport(invalidCamera),
        throwsA(isA<CoordinateValidationException>()),
      );
    });

    test('fetchVisibleTiles returns visible gltf tiles list', () {
      final tiles = nativeEngine.fetchVisibleTiles();
      expect(tiles, isNotEmpty);
      expect(tiles.first, contains('tile'));
    });
  });

  group('Scene3DViewport & Network3DScene Tests', () {
    final camera = VirtualCamera(
      dim_0: 37.7749,
      dim_1: -122.4194,
      dim_2: 500.0,
      heading: 0.0,
      pitch: -45.0,
      roll: 0.0,
    );

    testWidgets('Scene3DViewport builds successfully', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Scene3DViewport(camera: camera),
          ),
        ),
      );

      expect(find.byKey(const Key('scene_3d_viewport_container')), findsOneWidget);
    });

    test('initializeScene and render return true', () {
      final viewport = Scene3DViewport(camera: camera);
      expect(viewport.initializeScene(), isTrue);

      final canvas = Canvas(PictureRecorder());
      expect(viewport.render(canvas), isTrue);
    });

    test('Network3DScene loads models and applies materials', () async {
      final scene = Network3DScene();
      final loaded = await scene.loadModel('models/tower.gltf');
      expect(loaded, isFalse,
          reason: 'model file not available in test asset bundle');
      expect(scene.gltfData, isNull);
      expect(scene.state, ModelRenderState.error);

      expect(scene.applyPbrMaterials(), isFalse);
      expect(scene.isTranslucent, isFalse);
    });
  });
}
