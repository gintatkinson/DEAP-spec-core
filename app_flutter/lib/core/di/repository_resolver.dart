import 'dart:convert';
import 'dart:io';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/data/data_sources/firebase_data_source.dart';
import 'package:app_flutter/data/data_sources/sqlite_data_source.dart';
import 'package:app_flutter/data/database_initializer.dart';
import 'package:app_flutter/data/seeds/domain_seed_strategy.dart';
import 'package:flutter/foundation.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/tile_fetcher.dart';


/// Realises: [Feat-10/RepositoryResolver]
///
/// Resolves the data-access backend at app startup and exposes segregated
/// repository interfaces ([TypeRepository], [PropertyRepository], [TreeRepository],
/// [TopologyRepository], [InstanceRepository]).
///
/// Reads a JSON configuration file (or falls back to defaults) to decide
/// whether to initialise a local SQLite database or connect to Cloud
/// Firestore. Returns a [DataSource] that the app uses for all read/write
/// operations and schema discovery.
@immutable
class RepositoryResolver {
  /// Creates a [RepositoryResolver] wrapping a resolved [DataSource].
  const RepositoryResolver(this.dataSource);

  /// The underlying resolved [DataSource].
  final DataSource dataSource;

  /// Gets the [TypeRepository] interface.
  TypeRepository get typeRepository => dataSource;

  /// Gets the [PropertyRepository] interface.
  PropertyRepository get propertyRepository => dataSource;

  /// Gets the [TreeRepository] interface.
  TreeRepository get treeRepository => dataSource;

  /// Gets the [TopologyRepository] interface.
  TopologyRepository get topologyRepository => dataSource;

  /// Gets the [InstanceRepository] interface.
  InstanceRepository get instanceRepository => dataSource;

  static const _defaultConfig = 'assets/persistence-config.json';
  static const _defaultDbAsset = 'assets/properties_db.db.gz';

  static const _defaultEmulatorHost = 'localhost';
  static const _defaultEmulatorPort = 8080;

  static DataSource? _lastResolved;
  // NOTE: Once set, the Firebase SDK prevents reconfiguring the emulator
  // connection within a single process lifetime (BUG #216 — by design).
  static bool _firebaseEmulatorConfigured = false;

  // _isResolving guards against concurrent resolve() calls creating
  // duplicate connections (BUG #215).
  static bool _isResolving = false;

  /// Resets and disposes any cached resolved instance. Intended for test teardown.
  static Future<void> resetForTesting() async {
    await _lastResolved?.dispose();
    _lastResolved = null;
    _isResolving = false;
  }

  /// Resolves and initialises the appropriate backend.
  ///
  /// Determines the backend type from (in priority order):
  /// 1. [dataSourceType] parameter (if non-null)
  /// 2. JSON config file at [configPath] or the default asset path
  /// 3. Falls back to SQLite if neither is available
  ///
  /// For SQLite: copies the bundled database from [dbAssetPath] to the
  /// app support directory (unless [sqliteInMemory] is true). Creates
  /// the tables if they do not exist via [DatabaseInitializer].
  ///
  /// For Firebase: initialises the Firebase app and optionally connects
  /// to the Firestore emulator at [useEmulator].
  ///
  /// Returns a [DataSource] ready for injection.
  /// Throws on network errors (Firebase init) or file I/O
  /// errors (asset copy failure). Always resolves to a non-null DataSource.
  static Future<DataSource> resolve({
    String? configPath,
    String? dbAssetPath,
    bool sqliteInMemory = false,
    String? dataSourceType,
    bool useEmulator = true,
  }) async {
    if (_isResolving) {
      if (_lastResolved != null) return _lastResolved!;
      while (_isResolving) {
        await Future<void>.delayed(const Duration(milliseconds: 50));
      }
      if (_lastResolved != null) return _lastResolved!;
    }
    _isResolving = true;
    try {
      // Always try reading from config file to load basemaps and resolve repository type
      final path = configPath ?? _defaultConfig;
      Map<String, dynamic>? config;
      try {
        final configJson = await rootBundle.loadString(path);
        config = jsonDecode(configJson) as Map<String, dynamic>;
      } catch (_) {}

      if (config != null && config['basemaps'] != null) {
        TileFetcher.configure(config['basemaps'] as Map<String, dynamic>);
      }

      String type = dataSourceType ?? config?['repository_type'] as String? ?? 'sqlite';

      await _lastResolved?.dispose();
      final DataSource resolved;
      switch (type) {
        case 'firebase':
          resolved = await _createFirebaseAdapter(useEmulator: useEmulator);
        case 'sqlite':
          resolved = await _createSqliteAdapter(
            dbAssetPath: dbAssetPath,
            inMemory: sqliteInMemory,
          );
        default:
          resolved = await _createSqliteAdapter(
            dbAssetPath: dbAssetPath,
            inMemory: sqliteInMemory,
          );
      }
      _lastResolved = resolved;
      return resolved;
    } finally {
      _isResolving = false;
    }
  }

  /// Initialies Firebase and returns a Firestore-backed DataSource.
  ///
  /// Calls [Firebase.initializeApp] first (idempotent if already called).
  /// When [useEmulator] is true, redirects Firestore to the local emulator
  /// at localhost:8080 — useful for development without a real Firebase
  /// project. Throws if Firebase initialisation fails (missing config, etc.).
  static Future<FirebaseDataSource> _createFirebaseAdapter({
    bool useEmulator = true,
  }) async {
    await Firebase.initializeApp();
    final firestore = FirebaseFirestore.instance;
    if (useEmulator && !_firebaseEmulatorConfigured) {
      firestore.useFirestoreEmulator(_defaultEmulatorHost, _defaultEmulatorPort);
      _firebaseEmulatorConfigured = true;
    }
    return FirebaseDataSource(firestore);
  }

  /// Initialises SQLite FFI and returns an SQLite-backed DataSource.
  ///
  /// When [inMemory] is true, creates a transient in-memory database
  /// (data is lost on app restart). Otherwise, copies the asset database
  /// from [dbAssetPath] (or the default asset) to the app support directory
  /// and opens it.
  /// Throws on file I/O errors or database corruption.
  static Future<DataSource> _createSqliteAdapter({
    String? dbAssetPath,
    bool inMemory = false,
  }) async {
    final String dbPath;
    if (kIsWeb) {
      dbPath = inMemoryDatabasePath;
    } else {
      final dir = await getApplicationSupportDirectory();
      dbPath = inMemory ? inMemoryDatabasePath : p.join(dir.path, 'properties_db.db');
    }

      if (!kIsWeb && !inMemory) {
        final dbFile = File(dbPath);
        bool isOutdated = false;
        final exists = await dbFile.exists();
        
        List<int>? decodedAssetBytes;
        try {
          final assetPath = dbAssetPath ?? _defaultDbAsset;
          final bytes = await rootBundle.load(assetPath);
          decodedAssetBytes = bytes.buffer.asUint8List(
            bytes.offsetInBytes,
            bytes.lengthInBytes,
          );
          if (assetPath.endsWith('.gz')) {
            decodedAssetBytes = gzip.decode(decodedAssetBytes);
          }
        } catch (e) {
          debugPrint('Failed to load asset database: $e');
        }

        if (exists && decodedAssetBytes != null) {
          final currentSize = await dbFile.length();
          if (currentSize != decodedAssetBytes.length) {
            isOutdated = true;
          } else {
            final currentBytes = await dbFile.readAsBytes();
            for (int i = 0; i < currentSize; i++) {
              if (currentBytes[i] != decodedAssetBytes[i]) {
                isOutdated = true;
                break;
              }
            }
          }
        }

        if (!exists || isOutdated) {
          if (exists) {
            try {
              await dbFile.delete();
            } catch (e) {
              debugPrint('Failed to delete outdated database file: $e');
            }
          }
          if (decodedAssetBytes != null) {
            try {
              await dbFile.writeAsBytes(decodedAssetBytes);
            } catch (e) {
              debugPrint('Failed to write database file "$dbPath": $e');
            }
          }
        }
      }

    // Initialize the SQLite database and inject DomainSeedStrategy to seed mock properties
    final db = await DatabaseInitializer.create(
      dbPath: dbPath,
      seed: true,
      seedStrategy: DomainSeedStrategy(),
    );
    return SqliteDataSource(db);
  }
}
