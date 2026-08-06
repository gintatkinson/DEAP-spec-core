import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport_classes.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/properties/property_grid.dart';
import 'package:app_flutter/domain/type_descriptor.dart';

class _FakeThemeService implements ThemeService {
  @override Future<ThemeMode> loadThemeMode() async => ThemeMode.system;
  @override Future<void> saveThemeMode(ThemeMode mode) async {}
  @override Future<int> loadThemeScheme() async => 0;
  @override Future<void> saveThemeScheme(int scheme) async {}
  @override Future<double> loadTextScale() async => 1.0;
  @override Future<void> saveTextScale(double scale) async {}
  @override Future<Axis> loadLayoutSplitAxis() async => Axis.vertical;
  @override Future<void> saveLayoutSplitAxis(Axis axis) async {}
  @override Future<double> loadPanelOpacity() async => 0.85;
  @override Future<void> savePanelOpacity(double opacity) async {}
}

void main() {
  group('Phase 2 Feature Spec Remediation Tests', () {
    test('feat-03: VirtualCameraNormalization extrapolatePosition', () {
      final camera = VirtualCamera.raw(
        dim_0: 35.0,
        dim_1: 139.0,
        dim_2: 1000.0,
        heading: 0.0,
        pitch: -45.0,
        roll: 0.0,
      );

      final extrapolated = camera.extrapolatePosition(
        2.0,
        velocityLat: 0.5,
        velocityLng: -0.25,
        velocityAlt: 50.0,
      );

      expect(extrapolated.dim_0, equals(36.0));
      expect(extrapolated.dim_1, equals(138.5));
      expect(extrapolated.dim_2, equals(1100.0));
      expect(extrapolated.heading, equals(0.0));
      expect(extrapolated.pitch, equals(-45.0));
    });

    test('feat-10: SceneViewState serialization toJson and fromJson', () {
      final state = SceneViewState();
      state.activeStyle = 'Dark Map';
      state.astronomicalBody = 'Mars';
      state.elevationActive = false;
      state.showDevices = false;
      state.showLinks = true;
      state.showLabels = false;
      state.showDropLines = true;
      state.verticalExaggeration = 2.5;
      state.camera = VirtualCamera.raw(
        dim_0: 12.34,
        dim_1: 56.78,
        dim_2: 250000.0,
        heading: 10.0,
        pitch: -30.0,
        roll: 5.0,
      );

      final json = state.toJson();
      expect(json['activeStyle'], equals('Dark Map'));
      expect(json['astronomicalBody'], equals('Mars'));
      expect(json['elevationActive'], isFalse);
      expect(json['verticalExaggeration'], equals(2.5));
      expect(json['camera']['dim_0'], equals(12.34));

      final restored = SceneViewState.fromJson(json);
      expect(restored.activeStyle, equals('Dark Map'));
      expect(restored.astronomicalBody, equals('Mars'));
      expect(restored.elevationActive, isFalse);
      expect(restored.showDevices, isFalse);
      expect(restored.showLinks, isTrue);
      expect(restored.verticalExaggeration, equals(2.5));
      expect(restored.camera.dim_0, equals(12.34));
      expect(restored.camera.dim_1, equals(56.78));
      expect(restored.camera.dim_2, equals(250000.0));
    });

    test('feat-11: Scene3DViewportPainter calculateTileLOD', () {
      final painter = Scene3DViewportPainter();

      // High altitude -> low LOD
      final lodHighAlt = painter.calculateTileLOD(120000000.0);
      expect(lodHighAlt, equals(0));

      // Mid altitude -> mid LOD
      final lodMidAlt = painter.calculateTileLOD(500000.0);
      expect(lodMidAlt, greaterThan(5));

      // Low altitude -> high LOD
      final lodLowAlt = painter.calculateTileLOD(100.0);
      expect(lodLowAlt, greaterThanOrEqualTo(12));
    });

    testWidgets('feat-002: MapConfigPanel coordinate datum selection callbacks', (WidgetTester tester) async {
      String? selectedDatum;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                MapConfigPanel(
                  activeStyle: 'Satellite Map',
                  astronomicalBody: 'Earth',
                  activeDatum: 'WGS84',
                  elevationActive: true,
                  showDevices: true,
                  showLinks: true,
                  showLabels: true,
                  showDropLines: true,
                  onStyleChanged: (_) {},
                  onBodyChanged: (_) {},
                  onDatumChanged: (datum) => selectedDatum = datum,
                  onElevationToggled: (_) {},
                  onDevicesToggled: (_) {},
                  onLinksToggled: (_) {},
                  onLabelsToggled: (_) {},
                  onDropLinesToggled: (_) {},
                  onClose: () {},
                  onResetCamera: () {},
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('COORDINATE DATUM'), findsOneWidget);
      expect(find.text('WGS84'), findsOneWidget);
      expect(find.text('NAD83'), findsOneWidget);
      expect(find.text('WEBMERCATOR'), findsOneWidget);

      await tester.tap(find.text('NAD83'));
      await tester.pump();
      expect(selectedDatum, equals('NAD83'));

      await tester.tap(find.text('WEBMERCATOR'));
      await tester.pump();
      expect(selectedDatum, equals('WebMercator'));
    });

    testWidgets('feat-04: CameraStatsPanel frame-drop metrics counter', (WidgetTester tester) async {
      final controller = CameraController(VirtualCamera.zero);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                CameraStatsPanel(
                  cameraController: controller,
                  onClose: () {},
                  frameDropCount: 42,
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Frame Drops: 42'), findsOneWidget);
    });

    testWidgets('feat-13: PropertyGrid dynamic schema validation callback', (WidgetTester tester) async {
      final fields = [
        const FieldDescriptor(
          key: 'host_name',
          label: 'Host Name',
          type: 'string',
          sectionLabel: 'Network',
        ),
      ];

      String? schemaValidator(String key, dynamic value) {
        if (key == 'host_name' && value.toString().contains('invalid')) {
          return 'Host name contains forbidden keyword';
        }
        return null;
      }

      await tester.pumpWidget(
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController(_FakeThemeService()),
          child: MaterialApp(
            home: Scaffold(
              body: PropertyGrid(
                fields: fields,
                initialValues: const {'host_name': 'invalid_node'},
                validateSchemaProperty: schemaValidator,
              ),
            ),
          ),
        ),
      );

      final textField = find.byType(TextField);
      expect(textField, findsOneWidget);

      await tester.tap(textField);
      await tester.pump();

      // Trigger blur by unfocusing
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pump();

      expect(find.text('Host name contains forbidden keyword'), findsOneWidget);
    });
  });
}
