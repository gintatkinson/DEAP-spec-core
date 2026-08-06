import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/data/seeds/domain_seed_strategy.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  group('SeedMigrationRunner Tests', () {
    late Database db;

    setUp(() async {
      db = await DatabaseInitializer.create(
        dbPath: inMemoryDatabasePath,
        seed: false,
      );
    });

    tearDown(() async {
      await db.close();
    });

    test('isMigrationNeeded returns true for unseeded database', () async {
      final runner = SeedMigrationRunner();
      final needed = await runner.isMigrationNeeded(db);
      expect(needed, isTrue);
    });

    test('runMigration populates database schemas', () async {
      final runner = SeedMigrationRunner();
      final success = await runner.runMigration(db);
      expect(success, isTrue);

      final needed = await runner.isMigrationNeeded(db);
      expect(needed, isFalse);
    });
  });
}
