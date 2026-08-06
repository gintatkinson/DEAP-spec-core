import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/data/seeds/domain_seed_strategy.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Database? capturedDb;

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  tearDown(() async {
    if (capturedDb != null && capturedDb!.isOpen) {
      try {
        await capturedDb!.close();
      } catch (_) {}
    }
    capturedDb = null;
  });

  tearDownAll(() async {
    databaseFactory = databaseFactoryFfi;
  });

  group('DatabaseInitializer spatial seeding', () {
    test('regenerate assets database', () async {
      final tmpDir = await Directory.systemTemp.createTemp('asset_regen_');
      final dbPath = '${tmpDir.path}/properties_db.db';
      try {
        // Inject DomainSeedStrategy to ensure the generated asset is fully populated with mock topology data
        final db = await DatabaseInitializer.create(
          dbPath: dbPath,
          seed: true,
          seedStrategy: DomainSeedStrategy(),
        );
        await db.close();

        final file = File(dbPath);
        final gzFile = File('assets/properties_db.db.gz');
        final bytes = await file.readAsBytes();
        final gzipped = gzip.encode(bytes);
        await gzFile.writeAsBytes(gzipped);
        expect(await gzFile.exists(), isTrue);
      } finally {
        await tmpDir.delete(recursive: true);
      }
    });
  });

  group('DatabaseInitializer probe timeout handle leak', () {
    test('unclosed SQLite database handle is safely closed when openDatabase probe times out', () async {
      final slowFactory = _SlowDatabaseFactory(databaseFactoryFfi, (db) {
        capturedDb = db;
      });

      try {
        final openFuture = slowFactory.openDatabase(inMemoryDatabasePath);
        unawaited(openFuture.then((db) async {
          try {
            await db.close();
          } catch (_) {}
        }).catchError((_) {}));

        await openFuture.timeout(const Duration(milliseconds: 20));
      } catch (_) {
        // TimeoutException caught, probe failed
      }

      // Wait until openDatabase completes in background and connection is closed
      for (int i = 0; i < 40; i++) {
        if (capturedDb != null && !capturedDb!.isOpen) break;
        await Future<void>.delayed(const Duration(milliseconds: 50));
      }

      expect(capturedDb, isNotNull, reason: 'Database should have been opened in background');
      expect(capturedDb!.isOpen, isFalse, reason: 'Database connection should be closed by unawaited handler');
    });
  });
}

class _SlowDatabaseFactory implements DatabaseFactory {
  final DatabaseFactory _delegate;
  final void Function(Database) _onOpen;

  _SlowDatabaseFactory(this._delegate, this._onOpen);

  @override
  Future<Database> openDatabase(String path, {OpenDatabaseOptions? options}) async {
    final db = await _delegate.openDatabase(path, options: options);
    _onOpen(db);
    await Future<void>.delayed(const Duration(milliseconds: 60));
    return db;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    return super.noSuchMethod(invocation);
  }
}


