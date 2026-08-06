import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/database_initializer.dart';

/// Seed strategy version 1 for testing idempotency.
class Version1SeedStrategy implements SeedStrategy {
  @override
  Future<void> seed(Database db) async {
    final batch = db.batch();
    batch.insert('type_definitions', {
      'type_name': 'TypeA',
      'display_name': 'Type A',
      'icon_name': 'widgets',
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
    batch.insert('type_definitions', {
      'type_name': 'TypeB',
      'display_name': 'Type B',
      'icon_name': 'widgets',
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
    await batch.commit(noResult: true);
  }
}

/// Seed strategy version 2 for testing idempotency.
class Version2SeedStrategy implements SeedStrategy {
  @override
  Future<void> seed(Database db) async {
    final batch = db.batch();
    batch.insert('type_definitions', {
      'type_name': 'TypeA',
      'display_name': 'Type A',
      'icon_name': 'widgets',
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
    batch.insert('type_definitions', {
      'type_name': 'TypeB',
      'display_name': 'Type B',
      'icon_name': 'widgets',
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
    batch.insert('type_definitions', {
      'type_name': 'TypeC',
      'display_name': 'Type C',
      'icon_name': 'widgets',
    }, conflictAlgorithm: ConflictAlgorithm.ignore);
    await batch.commit(noResult: true);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  test('REGRESSION: Seed strategy executes idempotently and inserts new seed items across schema evolution', () async {
    final dbFile = File('test_seed_evolution_regression.db');
    if (await dbFile.exists()) {
      await dbFile.delete();
    }

    try {
      // 1. Initial database creation with V1 seed strategy (seeds TypeA, TypeB)
      final db1 = await DatabaseInitializer.create(
        dbPath: dbFile.path,
        seed: true,
        seedStrategy: Version1SeedStrategy(),
      );
      
      final v1CountResult = await db1.rawQuery('SELECT COUNT(*) as count FROM type_definitions');
      expect(v1CountResult.first['count'], equals(2));
      await db1.close();

      // 2. Re-open database with V2 seed strategy (which includes TypeA, TypeB, and NEW TypeC)
      final db2 = await DatabaseInitializer.create(
        dbPath: dbFile.path,
        seed: true,
        seedStrategy: Version2SeedStrategy(),
      );

      final typeCResult = await db2.rawQuery("SELECT COUNT(*) as count FROM type_definitions WHERE type_name = 'TypeC'");
      final typeCCount = typeCResult.first['count'] as int;

      await db2.close();

      // VERIFICATION: TypeC exists after running V2 seed strategy on existing database
      expect(typeCCount, equals(1), reason: 'Newly added seed item TypeC must be inserted cleanly into existing database.');
    } finally {
      if (await dbFile.exists()) {
        await dbFile.delete();
      }
    }
  });
}
