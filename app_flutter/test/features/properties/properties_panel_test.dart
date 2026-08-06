import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/features/properties/properties_panel.dart';
import 'package:app_flutter/features/properties/view_models/properties_view_model.dart';

class _FakeThemeService implements ThemeService {
  @override
  Future<ThemeMode> loadThemeMode() async => ThemeMode.system;
  @override
  Future<void> saveThemeMode(ThemeMode mode) async {}
  @override
  Future<int> loadThemeScheme() async => 0;
  @override
  Future<void> saveThemeScheme(int scheme) async {}
  @override
  Future<double> loadTextScale() async => 1.0;
  @override
  Future<void> saveTextScale(double scale) async {}
  @override
  Future<Axis> loadLayoutSplitAxis() async => Axis.vertical;
  @override
  Future<void> saveLayoutSplitAxis(Axis axis) async {}
  @override
  Future<double> loadPanelOpacity() async => 0.85;
  @override
  Future<void> savePanelOpacity(double opacity) async {}
}

class _MockTypeRepository implements TypeRepository {
  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async {
    return const Result.success([]);
  }

  @override
  Future<Result<TypeDescriptor?>> typeFor(String typeName) async {
    return const Result.success(null);
  }

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async {
    return const Result.success([]);
  }
}

void main() {
  group('PropertiesPanel Widget Tests', () {
    late _MockTypeRepository mockRepo;
    late PropertiesViewModel viewModel;

    setUp(() {
      mockRepo = _MockTypeRepository();
      viewModel = PropertiesViewModel(mockRepo);
    });

    testWidgets('shouldRenderOperationalUseCaseActionBarButtons', (tester) async {
      await tester.pumpWidget(
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController(_FakeThemeService()),
          child: MaterialApp(
            home: Scaffold(
              body: PropertiesPanel(
                activeView: 'node-1',
                currentNodeId: 'node-1',
                viewModel: viewModel,
              ),
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('uc_03_configure_location_button')), findsOneWidget);
      expect(find.byKey(const Key('uc_10_drill_hierarchy_button')), findsOneWidget);
      expect(find.byKey(const Key('uc_15_provision_ne_button')), findsOneWidget);
      expect(find.text('UC-03: Configure Location'), findsOneWidget);
      expect(find.text('UC-10: Drill Hierarchy'), findsOneWidget);
      expect(find.text('UC-15: Provision NE'), findsOneWidget);
    });

    testWidgets('shouldInvokeCallbackAndDispatchConfigureLocationOnClick', (tester) async {
      String? configuredNodeId;

      await tester.pumpWidget(
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController(_FakeThemeService()),
          child: MaterialApp(
            home: Scaffold(
              body: PropertiesPanel(
                activeView: 'node-101',
                currentNodeId: 'node-101',
                viewModel: viewModel,
                onConfigureLocation: (id) {
                  configuredNodeId = id;
                },
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('uc_03_configure_location_button')));
      await tester.pump();

      expect(configuredNodeId, equals('node-101'));
      expect(viewModel.state.lastAction, equals('configureLocation'));
      expect(viewModel.state.activeNodeId, equals('node-101'));
      expect(find.byKey(const Key('properties_action_status_message')), findsOneWidget);
    });

    testWidgets('shouldInvokeCallbackAndDispatchDrillHierarchyOnClick', (tester) async {
      String? drilledNodeId;

      await tester.pumpWidget(
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController(_FakeThemeService()),
          child: MaterialApp(
            home: Scaffold(
              body: PropertiesPanel(
                activeView: 'node-202',
                currentNodeId: 'node-202',
                viewModel: viewModel,
                onDrillHierarchy: (id) {
                  drilledNodeId = id;
                },
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('uc_10_drill_hierarchy_button')));
      await tester.pump();

      expect(drilledNodeId, equals('node-202'));
      expect(viewModel.state.lastAction, equals('drillHierarchy'));
      expect(viewModel.state.activeNodeId, equals('node-202'));
      expect(find.byKey(const Key('properties_action_status_message')), findsOneWidget);
    });

    testWidgets('shouldInvokeCallbackAndDispatchProvisionNeOnClick', (tester) async {
      String? provisionedNodeId;

      await tester.pumpWidget(
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController(_FakeThemeService()),
          child: MaterialApp(
            home: Scaffold(
              body: PropertiesPanel(
                activeView: 'node-303',
                currentNodeId: 'node-303',
                viewModel: viewModel,
                onProvisionNe: (id) {
                  provisionedNodeId = id;
                },
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const Key('uc_15_provision_ne_button')));
      await tester.pump();

      expect(provisionedNodeId, equals('node-303'));
      expect(viewModel.state.lastAction, equals('provisionNe'));
      expect(viewModel.state.activeNodeId, equals('node-303'));
      expect(find.byKey(const Key('properties_action_status_message')), findsOneWidget);
    });
  });
}
