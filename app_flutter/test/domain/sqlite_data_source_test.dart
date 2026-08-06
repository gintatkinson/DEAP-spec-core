import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/data/data_sources/sqlite_data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  test('shouldPreserveParentNodeIdWhenSavePropertiesIsCalled', () async {
    final db = await DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: false);

    await db.insert('properties', {
      'node_id': 'parent_node',
      'parent_node_id': null,
      'data_json': '{}',
    });

    await db.insert('properties', {
      'node_id': 'child_node',
      'parent_node_id': 'parent_node',
      'data_json': '{}',
    });

    final initialRows = await db.query(
      'properties',
      where: 'node_id = ?',
      whereArgs: ['child_node'],
    );
    expect(initialRows.first['parent_node_id'], equals('parent_node'));

    final dataSource = SqliteDataSource(db);
    final res = await dataSource.saveProperties('child_node', {'field_1': 'new_value'});
    expect(res.isSuccess, isTrue);

    final afterRows = await db.query(
      'properties',
      where: 'node_id = ?',
      whereArgs: ['child_node'],
    );
    expect(afterRows.first['parent_node_id'], equals('parent_node'));

    await db.close();
  });

  test('shouldCreateIndexNamesDuringDatabaseInitialization', () async {
    final db = await DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: false);

    final results = await db.rawQuery(
      "SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_instances_parent_type', 'idx_instances_type_name')"
    );

    final indexNames = results.map((row) => row['name'] as String).toList();
    expect(indexNames, contains('idx_instances_parent_type'));
    expect(indexNames, contains('idx_instances_type_name'));

    await db.close();
  });

  test('shouldResolveInstanceNodeIdToUnderlyingTypeDescriptor', () async {
    final db = await DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: false);

    await db.insert('type_definitions', {
      'type_name': 'ManagedElement',
      'display_name': 'Managed Element',
      'icon_name': 'router',
    });

    await db.insert('instances', {
      'id': 'Master_1',
      'parent_node_id': 'root',
      'type_name': 'ManagedElement',
      'data_json': '{}',
    });

    final dataSource = SqliteDataSource(db);
    final res = await dataSource.typeFor('Master_1');
    expect(res.isSuccess, isTrue);

    final descriptor = (res as Success<TypeDescriptor?>).value;
    expect(descriptor, isNotNull);
    expect(descriptor!.typeName, equals('ManagedElement'));
    expect(descriptor.displayName, equals('Managed Element'));

    await db.close();
  });
}
