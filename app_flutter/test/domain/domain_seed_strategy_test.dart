import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/seeds/domain_seed_strategy.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  group('DomainSeedStrategy unit tests', () {
    test('seeds database successfully with flat and nested coordinates', () async {
      final db = await openDatabase(inMemoryDatabasePath, version: 1, onCreate: (db, version) async {
        await db.execute('CREATE TABLE type_definitions (type_name TEXT PRIMARY KEY, display_name TEXT, icon_name TEXT);');
        await db.execute('CREATE TABLE type_attributes (type_name TEXT, attr_key TEXT, label TEXT, attr_type TEXT, section_label TEXT, section_order INTEGER, is_required INTEGER);');
        await db.execute('CREATE TABLE type_relations (parent_type_name TEXT, relation_name TEXT, child_type_name TEXT, child_label TEXT);');
        await db.execute('CREATE TABLE properties (node_id TEXT PRIMARY KEY, parent_node_id TEXT, data_json TEXT);');
        await db.execute('CREATE TABLE instances (id TEXT PRIMARY KEY, parent_node_id TEXT, type_name TEXT, data_json TEXT);');
      });

      final strategy = DomainSeedStrategy();
      await strategy.seed(db);

      final count = (await db.rawQuery('SELECT COUNT(*) FROM properties')).first.values.first as int;
      expect(count, greaterThan(0));

      await db.close();
    });
  });
}
