/// Realises: [UC-03]
/// Realises: [UC-10]
/// Realises: [UC-15]
/// Realises: [Feat-10/PropertiesPanel]
///
/// BDD UI acceptance test for Operational Use Case Action Bar.
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

/// Realises: [Feat-10/PropertiesPanel]
///
/// Ephemeral theme service for BDD widget tests.
class EphemeralThemeService implements ThemeService {
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

/// Realises: [Feat-10/PropertiesPanel]
///
/// In-memory type repository for Operational Use Case Action Bar BDD tests.
class InMemoryTypeRepository implements TypeRepository {
  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async {
    return const Result.success(<TypeDescriptor>[]);
  }

  @override
  Future<Result<TypeDescriptor?>> typeFor(String typeName) async {
    return const Result.success(null);
  }

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async {
    return const Result.success(<(String, String)>[]);
  }
}

void main() {
  group('Feature: Operational Use Case Action Bar', () {
    late InMemoryTypeRepository mockRepo;
    late PropertiesViewModel viewModel;

    setUp(() {
      mockRepo = InMemoryTypeRepository();
      viewModel = PropertiesViewModel(mockRepo);
    });

    testWidgets(
        'Scenario: Given a PropertiesPanel with Use Case Action Bar buttons, '
        'When user taps each action button, '
        'Then the corresponding ViewModel action event is dispatched and LUI state updates cleanly',
        (WidgetTester tester) async {
      String? lastCallbackNodeId;
      String? lastCallbackAction;

      // Given: A PropertiesPanel rendered with Use Case Action Bar buttons
      await tester.pumpWidget(
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController(EphemeralThemeService()),
          child: MaterialApp(
            home: Scaffold(
              body: PropertiesPanel(
                activeView: 'node-loc-100',
                currentNodeId: 'node-loc-100',
                viewModel: viewModel,
                onConfigureLocation: (String nodeId) {
                  lastCallbackNodeId = nodeId;
                  lastCallbackAction = 'UC-03';
                },
                onDrillHierarchy: (String nodeId) {
                  lastCallbackNodeId = nodeId;
                  lastCallbackAction = 'UC-10';
                },
                onProvisionNe: (String nodeId) {
                  lastCallbackNodeId = nodeId;
                  lastCallbackAction = 'UC-15';
                },
              ),
            ),
          ),
        ),
      );

      // Verify initial rendering of Action Bar buttons
      expect(find.byKey(const Key('uc_03_configure_location_button')), findsOneWidget);
      expect(find.byKey(const Key('uc_10_drill_hierarchy_button')), findsOneWidget);
      expect(find.byKey(const Key('uc_15_provision_ne_button')), findsOneWidget);

      // Action 1: User Taps UC-03: Configure Location
      await tester.tap(find.byKey(const Key('uc_03_configure_location_button')));
      await tester.pumpAndSettle();

      // Assert 1: ViewModel Action Event -> State Change -> LUI Render
      expect(lastCallbackAction, equals('UC-03'));
      expect(lastCallbackNodeId, equals('node-loc-100'));
      expect(viewModel.state.lastAction, equals('configureLocation'));
      expect(viewModel.state.activeNodeId, equals('node-loc-100'));
      expect(viewModel.state.actionMessage, equals('Location configured for node node-loc-100'));
      expect(find.byKey(const Key('properties_action_status_message')), findsOneWidget);
      expect(find.text('Location configured for node node-loc-100'), findsOneWidget);

      // Action 2: User Taps UC-10: Drill Hierarchy
      await tester.tap(find.byKey(const Key('uc_10_drill_hierarchy_button')));
      await tester.pumpAndSettle();

      // Assert 2: ViewModel Action Event -> State Change -> LUI Render
      expect(lastCallbackAction, equals('UC-10'));
      expect(lastCallbackNodeId, equals('node-loc-100'));
      expect(viewModel.state.lastAction, equals('drillHierarchy'));
      expect(viewModel.state.activeNodeId, equals('node-loc-100'));
      expect(viewModel.state.actionMessage, equals('Hierarchy drilled for node node-loc-100'));
      expect(find.byKey(const Key('properties_action_status_message')), findsOneWidget);
      expect(find.text('Hierarchy drilled for node node-loc-100'), findsOneWidget);

      // Action 3: User Taps UC-15: Provision NE
      await tester.tap(find.byKey(const Key('uc_15_provision_ne_button')));
      await tester.pumpAndSettle();

      // Assert 3: ViewModel Action Event -> State Change -> LUI Render
      expect(lastCallbackAction, equals('UC-15'));
      expect(lastCallbackNodeId, equals('node-loc-100'));
      expect(viewModel.state.lastAction, equals('provisionNe'));
      expect(viewModel.state.activeNodeId, equals('node-loc-100'));
      expect(viewModel.state.actionMessage, equals('NE provisioned for node node-loc-100'));
      expect(find.byKey(const Key('properties_action_status_message')), findsOneWidget);
      expect(find.text('NE provisioned for node node-loc-100'), findsOneWidget);
    });
  });
}
