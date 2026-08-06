import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:flutter_driver/flutter_driver.dart' as driver;
import 'package:path/path.dart' as p;
import 'package:provider/provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:app_flutter/app/app.dart';
import 'package:app_flutter/core/string_resources.dart';
import 'package:app_flutter/core/theme/text_scaler.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/data/data_sources/sqlite_data_source.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/features/topology/topographical_view.dart';
import 'package:app_flutter/main.dart' as app;

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  group('Performance Profiling Test Suite', () {
    testWidgets('3D Viewport Stress Test - Timeline', (WidgetTester tester) async {
      tester.binding.setSurfaceSize(const Size(1920, 1080));
      addTearDown(() {
        tester.binding.setSurfaceSize(null);
      });

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

      // 1. Setup SQLite Database
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
      final dbPath = p.join(Directory.systemTemp.path, 'perf_test.db');
      final file = File(dbPath);
      if (file.existsSync()) file.deleteSync();

      // 2. Initialise Database with actual seeding
      final db = await DatabaseInitializer.create(dbPath: dbPath, seed: true);
      final dataSource = SqliteDataSource(db);

      // 3. Mount the application
      final themeService = SharedPreferencesThemeService();
      final themeController = ThemeController(themeService);
      await themeController.loadSettings();

      final textScalerController = TextScalerController(themeService);
      await textScalerController.load();

      app.globalThemeController = themeController;
      app.globalTextScalerController = textScalerController;

      await StringResources.load();

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

      await tester.pump(const Duration(seconds: 2));
      await takeScreenshot('perf_initial_hud');

      final topoViewFinder = find.byType(TopographicalView);
      expect(topoViewFinder, findsOneWidget);
      final TopographicalView topoView = tester.widget<TopographicalView>(topoViewFinder);
      expect(topoView.topologyData.nodes.length, greaterThan(800), reason: 'Database seeding failed or loaded stale empty DB');
      expect(topoView.topologyData.links.length, greaterThan(1000), reason: 'Database seeding failed or loaded stale empty DB');


      // 4. Trace the interaction script
      await binding.traceAction(() async {
        final center = tester.getCenter(find.byType(MaterialApp));

        // Rapid pointer scrolls (zooming)
        for (int i = 0; i < 3; i++) {
          final gesture = await tester.startGesture(center);
          await gesture.moveBy(const Offset(0, -100));
          await tester.pump(const Duration(milliseconds: 50));
          await gesture.moveBy(const Offset(0, 100));
          await tester.pump(const Duration(milliseconds: 50));
          await gesture.up();
        }

        // Aggressive pointer panning (simulating rotating the globe)
        for (int i = 0; i < 5; i++) {
          await tester.dragFrom(center, const Offset(-200, 50));
          await tester.pump(const Duration(milliseconds: 100));
          await tester.dragFrom(center, const Offset(200, -50));
          await tester.pump(const Duration(milliseconds: 100));
        }

        // Visually iterate through some specific nodes in the tree
        for (int i = 0; i < 5; i++) {
           final nodeFinder = find.text('ntt_exchange_$i');
           if (nodeFinder.evaluate().isNotEmpty) {
             await tester.tap(nodeFinder.first);
             for (int j = 0; j < 10; j++) {
               await tester.pump(const Duration(milliseconds: 50));
             }
           }
        }
      }, reportKey: 'viewport_perf');

      await tester.pump(const Duration(seconds: 2));
      await takeScreenshot('perf_gesture_rotated');

      // 5. Output and Thresholds
      final reportData = binding.reportData;
      if (reportData != null && reportData.containsKey('viewport_perf')) {
        final rawTimeline = reportData['viewport_perf'];
        final timeline = driver.Timeline.fromJson(rawTimeline as Map<String, dynamic>);
        final summary = driver.TimelineSummary.summarize(timeline);

        await summary.writeTimelineToFile('viewport_perf', pretty: true);

        // Strict pass/fail criteria to prevent regressions
        expect(
          summary.computeAverageFrameBuildTimeMillis(),
          lessThan(16.0),
          reason: 'Average frame build time must be < 16.0ms for 60 FPS.',
        );
        expect(
          summary.computePercentileFrameBuildTimeMillis(90.0),
          lessThan(16.6),
          reason: '90th percentile frame build time must be < 16.6ms for 60 FPS.',
        );
        expect(
          summary.computeAverageFrameRasterizerTimeMillis(),
          lessThan(16.0),
          reason: 'Average frame rasterizer time must be < 16.0ms for 60 FPS.',
        );
      } else {
        fail('Timeline data was not captured');
      }
    });
  });
}
