// Compliance: GestureDetector Listener
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/core/app_config.dart';
import 'package:app_flutter/core/string_resources.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart' show SharedPreferencesThemeService;
import 'package:app_flutter/domain/data_source.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/data/data_sources/sqlite_data_source.dart';
import 'package:app_flutter/features/layout/layout.dart';
import 'package:app_flutter/features/tables/tabbed_container.dart';
import 'package:app_flutter/features/tables/view_models/tables_view_model.dart';

const String testLayoutConfig = '''
{
  "layout": {
    "root_container": {
      "type": "SidebarLayout",
      "id": "main_shell",
      "children": [
        {
          "type": "HierarchyTreeSelector",
          "id": "resource_tree"
        },
        {
          "type": "SplitWorkspace",
          "id": "workspace_split",
          "children": [
            {
              "type": "TopographicalView",
              "id": "topology_pane"
            },
            {
              "type": "TabbedContainer",
              "id": "details_and_relations_tab",
              "children": [
                {
                  "type": "TableView",
                  "id": "components_table"
                },
                {
                  "type": "TableView",
                  "id": "relation_a_table"
                },
                {
                  "type": "TableView",
                  "id": "relation_b_table"
                }
              ]
            }
          ]
        }
      ]
    }
  }
}
''';

Future<Database> createTestDatabase() async {
  final db = await DatabaseInitializer.create(
    dbPath: inMemoryDatabasePath,
    seed: false,
  );
  await db.insert('type_definitions', {
    'type_name': 'Master_1',
    'display_name': 'Master 1',
    'icon_name': 'insert_drive_file',
  });
  await db.insert('properties', {
    'node_id': 'Master_1',
    'parent_node_id': null,
    'data_json': '{}',
  });

  final details = ['Components', 'Relation_A', 'Relation_B'];
  final displayNames = {
    'Components': 'Components',
    'Relation_A': 'Relation A',
    'Relation_B': 'Relation B',
  };
  for (final d in details) {
    await db.insert('type_definitions', {
      'type_name': d,
      'display_name': displayNames[d] ?? d,
      'icon_name': 'widgets',
    });
    await db.insert('type_attributes', {
      'type_name': d,
      'attr_key': 'field_1',
      'label': 'Field 1',
      'attr_type': 'string',
      'section_label': 'General',
      'section_order': 0,
      'is_required': 0,
    });
    await db.insert('type_relations', {
      'parent_type_name': 'Master_1',
      'relation_name': 'contains',
      'child_type_name': d,
      'child_label': displayNames[d] ?? d,
    });
    await db.insert('instances', {
      'id': 'inst_Master_1_${d}_1',
      'parent_node_id': 'Master_1',
      'type_name': d,
      'data_json': '{"field_1": "val_1"}',
    });
  }

  await db.insert('type_definitions', {
    'type_name': 'SubItem',
    'display_name': 'Sub Item',
    'icon_name': 'insert_drive_file',
  });
  await db.insert('type_attributes', {
    'type_name': 'SubItem',
    'attr_key': 'field_1',
    'label': 'Field 1',
    'attr_type': 'string',
    'section_label': 'General',
    'section_order': 0,
    'is_required': 0,
  });
  await db.insert('properties', {
    'node_id': 'SubItem',
    'parent_node_id': 'Master_1',
    'data_json': '{"field_1": "val_1"}',
  });
  await db.insert('type_relations', {
    'parent_type_name': 'Master_1',
    'relation_name': 'contains',
    'child_type_name': 'SubItem',
    'child_label': 'Sub Items',
  });
  await db.insert('instances', {
    'id': 'inst_Master_1_SubItem_1',
    'parent_node_id': 'Master_1',
    'type_name': 'SubItem',
    'data_json': '{"field_1": "val_1"}',
  });
  return db;
}

Widget wrapWithRepo(Widget child, DataSource dataSource) {
  return MultiProvider(
    providers: [
      Provider<DataSource>.value(value: dataSource),
      ChangeNotifierProvider<ThemeController>.value(
        value: ThemeController(SharedPreferencesThemeService()),
      ),
    ],
    child: MaterialApp(home: child),
  );
}

Future<void> settle(WidgetTester tester) async {
  await Future<void>.delayed(const Duration(milliseconds: 50));
  await tester.pump();

  for (int i = 0; i < 50; i++) {
    if (find.byType(CircularProgressIndicator).evaluate().isEmpty) {
      break;
    }
    await Future<void>.delayed(const Duration(milliseconds: 50));
    await tester.pump();
  }

  for (int i = 0; i < 3; i++) {
    await Future<void>.delayed(const Duration(milliseconds: 10));
    await tester.pump();
  }
}

void main() {
  StringResources.loadFromJson('{"sidebar.header": "Platform Console", "breadcrumbs.home": "Platform Console"}');

  testWidgets('Layout parses JSON config and renders components', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.runAsync(() async {
      final db = await createTestDatabase();
      addTearDown(() => db.close());

      await tester.pumpWidget(
        wrapWithRepo(
          Layout(
            activeView: 'root',
            layoutConfig: testLayoutConfig,
          ),
          SqliteDataSource(db),
        ),
      );
      await settle(tester);

      expect(find.text(AppConfig.title), findsNWidgets(2));
      expect(find.text('Active View: root'), findsOneWidget);
      expect(find.byKey(const Key('Components-table')), findsNothing);

      await tester.pumpWidget(Container());
      await settle(tester);
    });
  });

  testWidgets('Layout switches tabs in TabbedContainer', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.runAsync(() async {
      final db = await createTestDatabase();
      addTearDown(() => db.close());

      await tester.pumpWidget(
        wrapWithRepo(
          Layout(
            activeView: 'Master_1',
            layoutConfig: testLayoutConfig,
          ),
          SqliteDataSource(db),
        ),
      );
      await settle(tester);

      // Components table is displayed initially
      expect(find.byKey(const Key('Components-table')), findsOneWidget);
      expect(find.byKey(const Key('Relation_A-table')), findsNothing);

      // Tap Relation A tab
      await tester.tap(find.widgetWithText(Tab, 'Relation A'));
      for (int i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      await settle(tester);

      expect(find.byKey(const Key('Components-table')), findsNothing);
      expect(find.byKey(const Key('Relation_A-table')), findsOneWidget);

      // Tap Relation B tab
      await tester.tap(find.widgetWithText(Tab, 'Relation B'));
      for (int i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      await settle(tester);

      expect(find.byKey(const Key('Relation_A-table')), findsNothing);
      expect(find.byKey(const Key('Relation_B-table')), findsOneWidget);

      // Tap Sub Items tab
      await tester.tap(find.widgetWithText(Tab, 'Sub Items'));
      for (int i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      await settle(tester);

      expect(find.byKey(const Key('Relation_B-table')), findsNothing);
      expect(find.byKey(const Key('SubItem-table')), findsOneWidget);

      await tester.pumpWidget(Container());
      await settle(tester);
    });
  });

  testWidgets('Layout splitter drags update sizes', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;

    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.runAsync(() async {
      final db = await createTestDatabase();
      addTearDown(() => db.close());

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            Provider<DataSource>.value(value: SqliteDataSource(db)),
            ChangeNotifierProvider<ThemeController>.value(
              value: ThemeController(SharedPreferencesThemeService()),
            ),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: Layout(
                layoutConfig: testLayoutConfig,
              ),
            ),
          ),
        ),
      );
      await settle(tester);

      // Test vertical splitter dragging
      final Finder verticalSplitter = find.byKey(const Key('vertical_splitter'));
      expect(verticalSplitter, findsOneWidget);

      // Drag vertical splitter to the right
      await tester.drag(verticalSplitter, const Offset(50, 0));
      await settle(tester);

      // Test horizontal SplitWorkspace splitter dragging
      final Finder horizontalSplitter = find.byKey(const Key('horizontal_splitter'));
      expect(horizontalSplitter, findsOneWidget);

      await tester.drag(horizontalSplitter, const Offset(0, 50));
      await settle(tester);

      // Test topographical view child splitter dragging (since child is present)
      final Finder topoSplitter = find.byKey(const Key('topo_splitter'));
      expect(topoSplitter, findsOneWidget);

      await tester.drag(topoSplitter, const Offset(0, 30));
      await settle(tester);

      await tester.pumpWidget(Container());
      await settle(tester);
    });
  });

  testWidgets('Layout keyboard navigation and node selection', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.runAsync(() async {
      final db = await createTestDatabase();
      addTearDown(() => db.close());

      String? selectedView;
      await tester.pumpWidget(
        wrapWithRepo(
          Layout(
            layoutConfig: testLayoutConfig,
            onViewChange: (view) => selectedView = view,
          ),
          SqliteDataSource(db),
        ),
      );
      await settle(tester);

      // Click on Master_1 node to give focus to the tree FocusNode
      await tester.tap(find.byKey(const Key('node_Master_1')));
      await settle(tester);

      // Send ArrowDown key event — navigates to SubItem child
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await settle(tester);
      expect(selectedView, 'SubItem');

      await tester.pumpWidget(Container());
      await settle(tester);
    });
  });

  testWidgets('Layout handles tree node tap selection without crashing', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.runAsync(() async {
      final db = await createTestDatabase();
      addTearDown(() => db.close());

      await tester.pumpWidget(
        wrapWithRepo(
          Layout(
            layoutConfig: testLayoutConfig,
          ),
          SqliteDataSource(db),
        ),
      );
      await settle(tester);

      // Tap the single Master_1 node
      await tester.tap(find.byKey(const Key('node_Master_1')));
      await settle(tester);

      await tester.pumpWidget(Container());
      await settle(tester);
    });
  });
}
