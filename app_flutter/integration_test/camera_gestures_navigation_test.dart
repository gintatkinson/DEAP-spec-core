import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:integration_test/integration_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:app_flutter/main.dart' as app_main;
import 'package:app_flutter/app/app.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart';
import 'package:app_flutter/core/theme/text_scaler.dart';
import 'package:app_flutter/core/string_resources.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/data/data_sources/sqlite_data_source.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/tile_fetcher.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/globe_tile_renderer.dart';
import 'dart:math' as math;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Visual Globe TDD verification: HUD, Fly-to-Node, Panning, and Rotation', (WidgetTester tester) async {
    tester.binding.setSurfaceSize(const Size(1920, 1080));
    addTearDown(() {
      tester.binding.setSurfaceSize(null);
      TileFetcher.urlOverride = null;
    });

    // Set local tile file override to verify tile rendering visually
    File localTile = File('${Directory.current.path}/test/topology/goldens/exaggerated_fuji_node.png');
    if (!localTile.existsSync()) {
      localTile = File('${Directory.current.path}/app_flutter/test/topology/goldens/exaggerated_fuji_node.png');
    }
    if (!localTile.existsSync()) {
      localTile = File('/Users/perkunas/jail/digital-pipeline-repo/app_flutter/test/topology/goldens/exaggerated_fuji_node.png');
    }
    if (localTile.existsSync()) {
      TileFetcher.urlOverride = 'file://${localTile.absolute.path}';
    }

    await StringResources.load();

    final db = await DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: true);
    addTearDown(() async {
      await db.close();
    });

    final dataSource = SqliteDataSource(db);

    final themeController = ThemeController(SharedPreferencesThemeService());
    await themeController.loadSettings();

    final textScalerController = TextScalerController();
    await textScalerController.load();

    app_main.globalThemeController = themeController;
    app_main.globalTextScalerController = textScalerController;

    Future<void> settle(WidgetTester t) async {
      await Future<void>.delayed(const Duration(milliseconds: 50));
      await t.pump();
      for (int i = 0; i < 50; i++) {
        if (find.byType(CircularProgressIndicator).evaluate().isEmpty) {
          break;
        }
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await t.pump();
      }
    }

    Future<double> calculateStdDev(Uint8List pngBytes) async {
      final double? result = await tester.runAsync<double>(() async {
        final ui.Codec codec = await ui.instantiateImageCodec(pngBytes);
        final ui.FrameInfo frame = await codec.getNextFrame();
        final ui.Image decodedImage = frame.image;
        final ByteData? rawRgba = await decodedImage.toByteData(format: ui.ImageByteFormat.rawRgba);
        if (rawRgba == null) return 0.0;
        final Uint8List rgbaBytes = rawRgba.buffer.asUint8List();
        
        double sum = 0.0;
        int count = 0;
        for (int i = 0; i < rgbaBytes.length; i += 16) {
          final double r = rgbaBytes[i].toDouble();
          final double g = rgbaBytes[i + 1].toDouble();
          final double b = rgbaBytes[i + 2].toDouble();
          final double gray = 0.299 * r + 0.587 * g + 0.114 * b;
          sum += gray;
          count++;
        }
        if (count == 0) return 0.0;
        final double mean = sum / count;
        
        double sumSquaredDiff = 0.0;
        for (int i = 0; i < rgbaBytes.length; i += 16) {
          final double r = rgbaBytes[i].toDouble();
          final double g = rgbaBytes[i + 1].toDouble();
          final double b = rgbaBytes[i + 2].toDouble();
          final double gray = 0.299 * r + 0.587 * g + 0.114 * b;
          final double diff = gray - mean;
          sumSquaredDiff += diff * diff;
        }
        final double variance = sumSquaredDiff / count;
        return math.sqrt(variance);
      });
      return result ?? 0.0;
    }

    Future<void> takeScreenshot(String name) async {
      final String screenshotDir = Platform.environment['SCREENSHOT_DIR'] ?? '/Users/perkunas/jail/digital-pipeline-repo/screenshots';
      final File file = File('$screenshotDir/$name.png');
      file.parent.createSync(recursive: true);
      final RenderRepaintBoundary boundary = tester.renderObject(find.byType(RepaintBoundary).first);
      final ui.Image image = (await tester.runAsync<ui.Image>(() => boundary.toImage()))!;
      final ByteData? byteData = await tester.runAsync<ByteData?>(() => image.toByteData(format: ui.ImageByteFormat.png));
      final Uint8List pngBytes = byteData!.buffer.asUint8List();
      
      final double stdDev = await calculateStdDev(pngBytes);
      expect(stdDev, greaterThan(15.0), reason: 'Standard deviation $stdDev is not greater than 15.0; screen is likely blank/solid-color');
      
      file.writeAsBytesSync(pngBytes);
    }

    Future<void> waitForTilesToLoad() async {
      final state = tester.state(find.byType(Scene3DViewport)) as Scene3DViewportState;
      int stableTicks = 0;
      int lastCount = -1;
      int attempts = 0;
      while (attempts < 100) {
        final int count = state.tileRenderer?.loadedImagesCount ?? 0;
        if (count >= 4 && count == lastCount) {
          stableTicks++;
        } else {
          stableTicks = 0;
        }
        lastCount = count;
        if (stableTicks >= 5) {
          break;
        }
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await tester.pump();
        attempts++;
      }
      expect(state.tileRenderer?.loadedImagesCount, greaterThanOrEqualTo(4), reason: 'At least 4 tiles should be loaded');
    }

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider<DataSource>.value(value: dataSource),
          ChangeNotifierProvider<ThemeController>.value(value: themeController),
          ChangeNotifierProvider<TextScalerController>.value(value: textScalerController),
        ],
        child: const MyApp(),
      ),
    );

    await settle(tester);

    int attempts = 0;
    while (attempts < 20 && find.byKey(const Key('node_Master_1')).evaluate().isEmpty) {
      await Future<void>.delayed(const Duration(milliseconds: 200));
      await tester.pump();
      attempts++;
    }

    expect(find.byKey(const Key('node_Master_1')), findsOneWidget, reason: 'Sidebar tree should contain Master_1');

    // Ensure 3D globe is active
    final toggle3dButton = find.byKey(const Key('toggle_3d'));
    if (toggle3dButton.evaluate().isNotEmpty) {
      await tester.ensureVisible(toggle3dButton);
      await tester.tap(toggle3dButton);
      await settle(tester);
    }

    expect(find.byType(Scene3DViewport), findsOneWidget, reason: '3D viewport should be mounted');
    await settle(tester);

    await waitForTilesToLoad();

    // Capture initial state screenshot
    await takeScreenshot('camera_initial_hud');

    final state = tester.state(find.byType(Scene3DViewport)) as dynamic;
    final CameraController controller = state.cameraController as CameraController;
    final double initialDim0 = controller.current.dim_0;
    final double initialDim1 = controller.current.dim_1;

    // Double-tap sidebar node (fly to node)
    final nodeFinder = find.byKey(const Key('node_Master_1_Child_1'));
    await tester.ensureVisible(nodeFinder);
    await tester.tap(nodeFinder);
    await tester.pump();
    await tester.tap(nodeFinder); // Double click simulation
    await settle(tester);

    // Verify fly-to-node updates coordinates
    final double postFlyLat = controller.current.dim_0;
    final double postFlyLng = controller.current.dim_1;
    expect(postFlyLat, isNot(equals(initialDim0)), reason: 'Dim_0 should update after fly-to');
    expect(postFlyLng, isNot(equals(initialDim1)), reason: 'Dim_1 should update after fly-to');
    await waitForTilesToLoad();
    await takeScreenshot('camera_fly_to_node');

    // Drag (Pan gesture)
    final viewport = find.byKey(const Key('scene_3d_viewport_container'));
    await tester.drag(viewport, const Offset(-50.0, 0.0));
    await settle(tester);

    final double postDragLng = controller.current.dim_1;
    expect(postDragLng, isNot(equals(postFlyLng)), reason: 'Dim_1 should change after pan drag gesture');

    // Ctrl+Drag (Rotate gesture)
    final double initialHeading = controller.current.heading;
    await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await tester.drag(viewport, const Offset(-100.0, 0.0));
    await tester.pump();
    await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await settle(tester);

    final double postRotateHeading = controller.current.heading;
    expect(postRotateHeading, isNot(equals(initialHeading)), reason: 'Heading should change after rotate gesture');
    await waitForTilesToLoad();
    await takeScreenshot('camera_gesture_rotated');
  });
}
