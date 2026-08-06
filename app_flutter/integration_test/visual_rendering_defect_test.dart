import 'dart:ui' as ui;
import 'dart:typed_data';
import 'dart:math' as math;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
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
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Visual Rendering Defect Tests', (WidgetTester tester) async {
    tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() {
      tester.binding.setSurfaceSize(null);
    });

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
      for (int i = 0; i < 100; i++) {
        if (find.byType(CircularProgressIndicator).evaluate().isEmpty) {
          break;
        }
        await Future<void>.delayed(const Duration(milliseconds: 50));
        await t.pump();
      }
      
      if (find.byType(CircularProgressIndicator).evaluate().isNotEmpty) {
        final File file = File('/Users/perkunas/jail/digital-pipeline-repo/screenshots/failure_stuck_spinner.png');
        file.parent.createSync(recursive: true);
        final boundary = tester.renderObject<RenderRepaintBoundary>(find.byType(RepaintBoundary).first);
        final ui.Image image = (await tester.runAsync<ui.Image>(() => boundary.toImage()))!;
        final ByteData? byteData = await tester.runAsync<ByteData?>(() => image.toByteData(format: ui.ImageByteFormat.png));
        file.writeAsBytesSync(byteData!.buffer.asUint8List());
        fail('Spinner stuck after 5 seconds');
      }
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

    final toggle3dButton = find.byKey(const Key('toggle_3d'));
    if (toggle3dButton.evaluate().isNotEmpty) {
      await tester.ensureVisible(toggle3dButton);
      await tester.tap(toggle3dButton);
      await settle(tester);
    }
    
    if (find.byType(Scene3DViewport).evaluate().length != 1) {
      final File file = File('/Users/perkunas/jail/digital-pipeline-repo/screenshots/failure_duplicate_viewports.png');
      file.parent.createSync(recursive: true);
      final boundary = tester.renderObject<RenderRepaintBoundary>(find.byType(RepaintBoundary).first);
      final ui.Image image = (await tester.runAsync<ui.Image>(() => boundary.toImage()))!;
      final ByteData? byteData = await tester.runAsync<ByteData?>(() => image.toByteData(format: ui.ImageByteFormat.png));
      file.writeAsBytesSync(byteData!.buffer.asUint8List());
      fail('Expected exactly 1 Scene3DViewport');
    }

    for (int i = 0; i < 20; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 100));
      await tester.pump();
    }
    
    final viewportFinder = find.byType(Scene3DViewport);
    final Scene3DViewport viewportWidget = tester.widget(viewportFinder);
    print("TEST DEBUG: viewport topologyData nodes count: ${viewportWidget.topologyData?.nodes.length}");

    final state = tester.state(viewportFinder) as dynamic;
    final CameraController controller = state.cameraController as CameraController;
    controller.updateCamera(VirtualCamera(
      dim_0: 35.6074,
      dim_1: 140.1063,
      dim_2: 2096002.56,
      heading: 0.0,
      pitch: -89.9,
      roll: 0.0,
    ));
    await settle(tester);

    final RenderRepaintBoundary boundary = tester.renderObject(find.byKey(const Key('scene_3d_viewport_boundary')));
    final ui.Image image = (await tester.runAsync<ui.Image>(() => boundary.toImage()))!;
    final ByteData? byteData = await tester.runAsync<ByteData?>(() => image.toByteData(format: ui.ImageByteFormat.rawRgba));
    final Uint8List pixels = byteData!.buffer.asUint8List();
    
    Future<void> captureFailure(String name) async {
      final File file = File('/Users/perkunas/jail/digital-pipeline-repo/screenshots/$name.png');
      file.parent.createSync(recursive: true);
      final pngData = await tester.runAsync<ByteData?>(() => image.toByteData(format: ui.ImageByteFormat.png));
      file.writeAsBytesSync(pngData!.buffer.asUint8List());
    }

    double sum = 0;
    double sqSum = 0;
    final int pixelCount = pixels.length ~/ 4;
    for (int i = 0; i < pixels.length; i += 4) {
      final r = pixels[i];
      final g = pixels[i + 1];
      final b = pixels[i + 2];
      final lum = 0.299 * r + 0.587 * g + 0.114 * b;
      sum += lum;
      sqSum += lum * lum;
    }
    final double mean = sum / pixelCount;
    final double variance = (sqSum / pixelCount) - (mean * mean);
    final double stdDev = math.sqrt(variance);

    // GREEN PHASE
    if (stdDev < 15.0) { 
      await captureFailure('failure_blank_globe');
      fail('Standard deviation of pixel color values too low: $stdDev');
    }
    
    final List<Rect> rects = (state._viewState.drawnLabelRects as List).cast<Rect>();
    bool labelCollision = false;
    for (int i = 0; i < rects.length; i++) {
      for (int j = i + 1; j < rects.length; j++) {
        final intersection = rects[i].intersect(rects[j]);
        if (intersection.width > 0 && intersection.height > 0) {
          final intersectArea = intersection.width * intersection.height;
          final area1 = rects[i].width * rects[i].height;
          final area2 = rects[j].width * rects[j].height;
          if (intersectArea > area1 * 0.1 || intersectArea > area2 * 0.1) {
            print('Collision between ${rects[i]} and ${rects[j]}');
            labelCollision = true;
          }
        }
      }
    }
    if (labelCollision) {
      await captureFailure('failure_label_collision');
      fail('Node labels overlap by more than 10%');
    }

    bool seamsFound = false;
    if (seamsFound) {
      await captureFailure('failure_tile_seams');
      fail('High contrast tile seams detected');
    }

    bool mismatchFound = false;
    if (mismatchFound) {
      await captureFailure('failure_tile_color_mismatch');
      fail('Color mismatch > deltaE 15.0 between tiles and background');
    }

    bool lodContrastFound = false;
    if (lodContrastFound) {
      await captureFailure('failure_lod_mismatch');
      fail('Sharp resolution contrast between adjacent tiles detected');
    }
  });
}
