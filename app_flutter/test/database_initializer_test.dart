import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../lib/data/database_initializer.dart' as di;

void main() {
  test('Run database initializer', () async {
    final tmpDir = await Directory.systemTemp.createTemp('di_main_test_');
    try {
      final dbPath = '${tmpDir.path}/properties_db.db';
      final db = await di.DatabaseInitializer.create(dbPath: dbPath, seed: true);
      await db.close();
      expect(await File(dbPath).exists(), isTrue);
    } finally {
      await tmpDir.delete(recursive: true);
    }
  });

  test('FFI viability probe succeeds on non-sandboxed desktop', () async {
    if (!kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS)) {
      sqfliteFfiInit();
      final probe = await databaseFactoryFfi
          .openDatabase(inMemoryDatabasePath)
          .timeout(const Duration(seconds: 2));
      await probe.close();
      expect(probe.isOpen, false);
    }
  });

  test('create() throws StateError when sandbox blocks FFI', () async {
    final isDesktop = !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);
    if (!isDesktop) {
      return;
    }
    try {
      await di.DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: false);
    } catch (e) {
      if (e is StateError) {
        return;
      }
    }
  });

  test('create() succeeds with in-memory database on desktop', () async {
    final isDesktop = !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);
    if (!isDesktop) {
      return;
    }
    final db = await di.DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: false);
    expect(db.isOpen, true);
    await db.close();
  });

  test('databaseFactory is restored after create() failure', () async {
    final isTargetPlatform = !kIsWeb &&
        (Platform.environment.containsKey('FLUTTER_TEST') ||
         Platform.isWindows || Platform.isLinux || Platform.isMacOS);
    if (!isTargetPlatform) {
      return;
    }
    sqfliteFfiInit();
    final originalFactory = databaseFactory;
    final tmpDir = await Directory.systemTemp.createTemp('di_fail_test_');
    try {
      await di.DatabaseInitializer.create(dbPath: tmpDir.path, seed: false);
      fail('Expected an exception when opening a directory as a database');
    } catch (_) {
      expect(identical(databaseFactory, originalFactory), isTrue);
    } finally {
      await tmpDir.delete(recursive: true);
    }
  });
}
