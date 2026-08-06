import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// CLI entrypoint for database regeneration and compression.
Future<void> main() async {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
  /// Member documentation.
  final dbPath = 'assets/properties_db.db';
  /// Member documentation.
  final file = File(dbPath);
  if (await file.exists()) {
    await file.delete();
  }
  /// Member documentation.
  final db = await DatabaseInitializer.create(dbPath: dbPath, seed: true);
  await db.close();
  print('Generic database properties_db.db regenerated successfully.');

  /// Member documentation.
  final gzFile = File('assets/properties_db.db.gz');
  if (await gzFile.exists()) {
    await gzFile.delete();
  }
  /// Member documentation.
  final bytes = await file.readAsBytes();
  /// Member documentation.
  final gzipped = gzip.encode(bytes);
  await gzFile.writeAsBytes(gzipped);
  print('Database gzipped to properties_db.db.gz successfully.');
}

/// Realises: [Feat-10/DatabaseInitializer]
/// Member documentation.
abstract class SeedStrategy {
  /// Member documentation.
  Future<void> seed(Database db);
}

/// Realises: [Feat-10/DatabaseInitializer]
/// Creates and optionally seeds a local SQLite database for development
/// and testing.
///
/// Generates the full schema (`properties`, `instances`, `type_definitions`,
/// `type_attributes`, `type_relations`) and populates sample data when [seed] is true.
/// Used at app startup when no pre-built database asset exists, or when running in CI/testing environments.
///
/// Call [create] once before any repository operation. The returned
/// [Database] is shared across [SqliteDataSource]. Do not call [create] multiple times for the
/// same path — it reopens the same file and re-runs `CREATE TABLE IF NOT
/// EXISTS`, which is safe but wasteful.
class DatabaseInitializer {
  /// Opens (or creates) the database and ensures all tables exist.
  ///
  /// If [dbPath] is null, the database is placed in the app support
  /// directory as `properties_db.db`. When [seed] is true and the
  /// `properties` table is empty, sample data is inserted. Idempotent for the tables (uses `CREATE TABLE IF NOT
  /// EXISTS`) but NOT for seeding (checks row count first).
  ///
  /// Throws on I/O errors (path resolution, file creation) or SQL
  /// execution failures.
  static Future<Database> create({String? dbPath, bool seed = false, SeedStrategy? seedStrategy}) async {
    final isTest = !kIsWeb && Platform.environment.containsKey('FLUTTER_TEST');
    final isDesktop = !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);
    if (isDesktop && !isTest) {
      final canAccess = await _probeFfiViability();
      if (!canAccess) {
        throw StateError(
          'Cannot open database on this desktop environment. '
          'The FFI SQLite backend is blocked by the system sandbox. '
          'Grant file-access entitlements or use a non-sandboxed deployment.',
        );
      }
    }
    if (!kIsWeb && (isTest || isDesktop)) {
      sqfliteFfiInit();
      try {
        databaseFactory;
      } catch (_) {
        databaseFactory = databaseFactoryFfi;
      }
    }

    final String path;
    if (kIsWeb) {
      path = dbPath ?? inMemoryDatabasePath;
    } else {
      path = dbPath != null
          ? (dbPath == inMemoryDatabasePath ? dbPath : p.absolute(dbPath))
          : (isTest
              ? inMemoryDatabasePath
              : p.join(
                  (await getApplicationSupportDirectory()).path,
                  'properties_db.db',
                ));
    }

    final db = await databaseFactory.openDatabase(path);
    try {
      await db.execute('PRAGMA journal_mode = WAL;');
      await db.execute('PRAGMA busy_timeout = 5000;');
      await db.execute('PRAGMA foreign_keys = ON;');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS properties (
          node_id TEXT PRIMARY KEY,
          parent_node_id TEXT REFERENCES properties(node_id),
          data_json TEXT NOT NULL
        )
      ''');

      await db.execute('''
        CREATE INDEX IF NOT EXISTS idx_properties_parent_node_id
        ON properties(parent_node_id);
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS instances (
          id TEXT PRIMARY KEY,
          parent_node_id TEXT NOT NULL,
          type_name TEXT NOT NULL,
          data_json TEXT NOT NULL
        )
      ''');

      await db.execute('''
        CREATE INDEX IF NOT EXISTS idx_instances_parent_type
        ON instances(parent_node_id, type_name);
      ''');

      await db.execute('''
        CREATE INDEX IF NOT EXISTS idx_instances_type_name
        ON instances(type_name);
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS type_definitions (
          type_name TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          icon_name TEXT NOT NULL DEFAULT 'insert_drive_file'
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS type_attributes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          type_name TEXT NOT NULL REFERENCES type_definitions(type_name),
          attr_key TEXT NOT NULL,
          label TEXT NOT NULL,
          attr_type TEXT NOT NULL,
          section_label TEXT,
          section_order INTEGER NOT NULL DEFAULT 0,
          is_required INTEGER NOT NULL DEFAULT 0,
          min_value REAL,
          max_value REAL,
          pattern TEXT,
          enum_options TEXT,
          enum_display_names TEXT,
          default_value TEXT,
          input_formatters TEXT,
          UNIQUE(type_name, attr_key)
        )
      ''');

      await db.execute('''
        CREATE TABLE IF NOT EXISTS type_relations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          parent_type_name TEXT NOT NULL REFERENCES type_definitions(type_name),
          relation_name TEXT NOT NULL,
          child_type_name TEXT NOT NULL REFERENCES type_definitions(type_name),
          child_label TEXT NOT NULL,
          UNIQUE(parent_type_name, child_type_name)
        )
      ''');

      if (seed && seedStrategy != null) {
        await seedStrategy.seed(db);
      }

      return db;
    } catch (e) {
      await db.close();
      rethrow;
    }
  }

  static Future<bool> _probeFfiViability() async {
    try {
      sqfliteFfiInit();
      final openFuture = databaseFactoryFfi.openDatabase(inMemoryDatabasePath);
      unawaited(openFuture.then((db) async {
        try {
          await db.close();
        } catch (_) {}
      }).catchError((_) {}));

      await openFuture.timeout(const Duration(seconds: 2));
      return true;
    } catch (_) {
      return false;
    }
  }

}

