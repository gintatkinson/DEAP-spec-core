import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart' show rootBundle;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/database_initializer.dart';

/// Concrete implementation of [SeedStrategy] that seeds the database with domain-specific mock data.
///
/// This includes base type definitions, attributes, space nodes, real NTT exchanges,
/// cable landing stations, and their interconnectivity links.
class _NodePos {
  /// Member documentation.
  final String id;
  /// Member documentation.
  final double lat;
  /// Member documentation.
  final double lon;

  const _NodePos(this.id, this.lat, this.lon);
}

/// Realises: [Feat-000/DomainSeedStrategy]
/// Concrete implementation of [SeedStrategy] that seeds the database with domain-specific mock data.
class DomainSeedStrategy implements SeedStrategy {
  late Batch _currentBatch;
  late Database _currentDb;
  int _pendingOps = 0;

  Future<void> _insertAndFlush(
    String table,
    Map<String, Object?> values, {
    ConflictAlgorithm? conflictAlgorithm,
  }) async {
    _currentBatch.insert(table, values, conflictAlgorithm: conflictAlgorithm);
    _pendingOps++;
    if (_pendingOps >= 1000) {
      await _currentBatch.commit(noResult: true);
      _currentBatch = _currentDb.batch();
      _pendingOps = 0;
    }
  }

  Future<void> _flushBatch() async {
    if (_pendingOps > 0) {
      await _currentBatch.commit(noResult: true);
      _pendingOps = 0;
    }
  }

  /// Seeds the database by batch-inserting default schemas, nodes, and instances.
  ///
  /// Assumes the database tables have been successfully created by [DatabaseInitializer].
  @override
  Future<void> seed(Database db) async {
    _currentDb = db;
    _currentBatch = db.batch();
    _pendingOps = 0;
    final spaceDetails = ['Components', 'Telemetry', 'Logs', 'Links'];
    final nttDetails = ['Components', 'Alarms', 'Links'];
    final landingDetails = ['Components', 'Links'];

    final displayNames = {
      'Components': 'Components',
      'Telemetry': 'Telemetry',
      'Logs': 'Logs',
      'Alarms': 'Alarms',
      'Links': 'Links',
    };

    // 1. Seed base system type definitions and their 50 generic attributes
    for (final d in displayNames.keys) {
      await _insertAndFlush('type_definitions', {
        'type_name': d,
        'display_name': displayNames[d] ?? d,
        'icon_name': 'widgets',
      }, conflictAlgorithm: ConflictAlgorithm.ignore);

      for (int i = 1; i <= 50; i++) {
        await _insertAndFlush('type_attributes', {
          'type_name': d,
          'attr_key': 'field_$i',
          'label': 'Field $i',
          'attr_type': 'string',
          'section_label': 'General',
          'section_order': 0,
          'is_required': 0,
        }, conflictAlgorithm: ConflictAlgorithm.ignore);
      }
    }

    // 2. Generate 100 space orbit telemetry nodes
    final spaceNodes = <String>[];
    for (int i = 0; i < 100; i++) {
      final id = 'space_$i';
      spaceNodes.add(id);
      final lat = 25.0 + (i / 100.0) * 20.0;
      final lon = 125.0 + (i % 20) * 1.0;
      await _addNodeToBatch(id, null, spaceDetails, lat: lat, lon: lon, height: 500000.0);
    }

    // 3. Load and parse real NTT exchanges data from assets
    final nttFile = File('assets/ntt_exchanges_japan_763.json');
    String nttJsonString;
    if (await nttFile.exists()) {
      nttJsonString = await nttFile.readAsString();
    } else {
      nttJsonString = await rootBundle.loadString('assets/ntt_exchanges_japan_763.json');
    }
    final nttJson = jsonDecode(nttJsonString) as List;

    final nttNodes = <_NodePos>[];
    for (int i = 0; i < nttJson.length; i++) {
      final item = nttJson[i];
      final id = 'ntt_exchange_$i';
      final lat = _extractLat(item);
      final lon = _extractLon(item);
      final height = _extractHeight(item);
      nttNodes.add(_NodePos(id, lat, lon));
      await _addNodeToBatch(id, null, nttDetails, lat: lat, lon: lon, height: height);
    }

    // 4. Load and parse cable landing stations data from assets
    final landingFile = File('assets/cable_landing_stations_japan.json');
    String landingJsonString;
    if (await landingFile.exists()) {
      landingJsonString = await landingFile.readAsString();
    } else {
      landingJsonString = await rootBundle.loadString('assets/cable_landing_stations_japan.json');
    }
    final landingJson = jsonDecode(landingJsonString) as List;

    final landingNodes = <_NodePos>[];
    for (int i = 0; i < landingJson.length; i++) {
      final item = landingJson[i];
      final id = 'cable_landing_$i';
      final lat = _extractLat(item);
      final lon = _extractLon(item);
      final height = _extractHeight(item);
      landingNodes.add(_NodePos(id, lat, lon));
      await _addNodeToBatch(id, null, landingDetails, lat: lat, lon: lon, height: height);
    }

    // 5. Interconnect stations, exchanges, and orbits with interface links
    final Set<String> addedLinks = {};
    int linkIdCounter = 0;

    Future<void> addLink(String from, String to) async {
      final key1 = '${from}_$to';
      final key2 = '${to}_$from';
      if (!addedLinks.contains(key1) && !addedLinks.contains(key2)) {
        addedLinks.add(key1);
        addedLinks.add(key2);
        await _insertAndFlush('instances', {
          'id': 'link_${linkIdCounter++}',
          'parent_node_id': from,
          'type_name': 'interface',
          'data_json': jsonEncode({'description': 'link to node $to'}),
        }, conflictAlgorithm: ConflictAlgorithm.replace);
      }
    }

    double distSq(double lat1, double lon1, double lat2, double lon2) {
      return (lat1 - lat2) * (lat1 - lat2) + (lon1 - lon2) * (lon1 - lon2);
    }

    for (int i = 0; i < nttNodes.length; i++) {
      final current = nttNodes[i];
      double minDist1 = double.infinity;
      String? minId1;
      double minDist2 = double.infinity;
      String? minId2;

      for (int j = 0; j < nttNodes.length; j++) {
        if (i == j) continue;
        final target = nttNodes[j];
        final d = distSq(current.lat, current.lon, target.lat, target.lon);
        if (d < minDist1) {
          minDist2 = minDist1;
          minId2 = minId1;
          minDist1 = d;
          minId1 = target.id;
        } else if (d < minDist2) {
          minDist2 = d;
          minId2 = target.id;
        }
      }

      if (minId1 != null) await addLink(current.id, minId1);
      if (minId2 != null) await addLink(current.id, minId2);

      final space1 = spaceNodes[(i * 2) % 100];
      final space2 = spaceNodes[(i * 2 + 1) % 100];
      await addLink(current.id, space1);
      await addLink(current.id, space2);
    }

    for (int i = 0; i < landingNodes.length; i++) {
      final current = landingNodes[i];
      double m0 = double.infinity,
          m1 = double.infinity,
          m2 = double.infinity,
          m3 = double.infinity,
          m4 = double.infinity;
      String? id0, id1, id2, id3, id4;

      for (int j = 0; j < nttNodes.length; j++) {
        final target = nttNodes[j];
        final d = distSq(current.lat, current.lon, target.lat, target.lon);
        if (d < m0) {
          m4 = m3; id4 = id3;
          m3 = m2; id3 = id2;
          m2 = m1; id2 = id1;
          m1 = m0; id1 = id0;
          m0 = d;  id0 = target.id;
        } else if (d < m1) {
          m4 = m3; id4 = id3;
          m3 = m2; id3 = id2;
          m2 = m1; id2 = id1;
          m1 = d;  id1 = target.id;
        } else if (d < m2) {
          m4 = m3; id4 = id3;
          m3 = m2; id3 = id2;
          m2 = d;  id2 = target.id;
        } else if (d < m3) {
          m4 = m3; id4 = id3;
          m3 = d;  id3 = target.id;
        } else if (d < m4) {
          m4 = d;  id4 = target.id;
        }
      }

      if (id0 != null) await addLink(current.id, id0);
      if (id1 != null) await addLink(current.id, id1);
      if (id2 != null) await addLink(current.id, id2);
      if (id3 != null) await addLink(current.id, id3);
      if (id4 != null) await addLink(current.id, id4);
    }

    await _flushBatch();
  }

  /// Helper helper to insert a complete node configuration (type_definition, relation, properties, and instances).
  Future<void> _addNodeToBatch(
    String node,
    String? parent,
    List<String> details, {
    required double lat,
    required double lon,
    required double height,
  }) async {
    await _insertAndFlush('type_definitions', {
      'type_name': node,
      'display_name': node.replaceAll('_', ' '),
      'icon_name': 'insert_drive_file',
    }, conflictAlgorithm: ConflictAlgorithm.replace);

    for (final d in details) {
      await _insertAndFlush('type_relations', {
        'parent_type_name': node,
        'relation_name': 'contains',
        'child_type_name': d,
        'child_label': d == 'Components' ? 'Components' : d.replaceAll('_', ' ').split(' ').map((s) => s.isEmpty ? '' : s[0].toUpperCase() + s.substring(1)).join(' '),
      }, conflictAlgorithm: ConflictAlgorithm.replace);
    }

    for (int i = 1; i <= 50; i++) {
      await _insertAndFlush('type_attributes', {
        'type_name': node,
        'attr_key': 'field_$i',
        'label': 'Field $i',
        'attr_type': 'string',
        'section_label': 'General',
        'section_order': 0,
        'is_required': 0,
      }, conflictAlgorithm: ConflictAlgorithm.replace);
    }

    final propertiesMap = {
      for (int j = 1; j <= 50; j++) 'field_$j': 'val_${node}_field_$j',
      'location': {
        'ellipsoid': {
          'latitude': lat,
          'longitude': lon,
          'height': height,
        }
      }
    };
    await _insertAndFlush('properties', {
      'node_id': node,
      'parent_node_id': parent,
      'data_json': jsonEncode(propertiesMap),
    }, conflictAlgorithm: ConflictAlgorithm.replace);

    for (final d in details) {
      for (int k = 1; k <= 5; k++) {
        final instId = 'inst_${node}_${d}_$k';
        final instanceMap = {
          for (int j = 1; j <= 50; j++) 'field_$j': 'val_inst_${node}_${d}_${k}_field_$j'
        };
        await _insertAndFlush('instances', {
          'id': instId,
          'parent_node_id': node,
          'type_name': d,
          'data_json': jsonEncode(instanceMap),
        }, conflictAlgorithm: ConflictAlgorithm.replace);
      }
    }
  }

  /// Safely extracts latitude from either top-level or nested position map.
  double _extractLat(dynamic item) {
    if (item is Map) {
      if (item['position'] is Map) {
        final pos = item['position'] as Map;
        final val = pos['dim_0'] ?? pos['latitude'] ?? pos['lat'];
        if (val is num) return val.toDouble();
      }
      final val = item['latitude'] ?? item['lat'];
      if (val is num) return val.toDouble();
    }
    return 0.0;
  }

  /// Safely extracts longitude from either top-level or nested position map.
  double _extractLon(dynamic item) {
    if (item is Map) {
      if (item['position'] is Map) {
        final pos = item['position'] as Map;
        final val = pos['dim_1'] ?? pos['longitude'] ?? pos['lon'];
        if (val is num) return val.toDouble();
      }
      final val = item['longitude'] ?? item['lon'];
      if (val is num) return val.toDouble();
    }
    return 0.0;
  }

  /// Safely extracts height from either top-level or nested position map, defaulting to 0.0.
  double _extractHeight(dynamic item) {
    if (item is Map) {
      if (item['position'] is Map) {
        final pos = item['position'] as Map;
        final val = pos['dim_2'] ?? pos['height'];
        if (val is num) return val.toDouble();
      }
      final val = item['height'];
      if (val is num) return val.toDouble();
    }
    return 0.0;
  }
}

/// Realises: [Feat-000/SeedMigrationRunner]
/// Handles running database seed migrations and schema upgrades for domain seed data.
class SeedMigrationRunner {
  /// The [SeedStrategy] used to execute seed operations.
  final SeedStrategy seedStrategy;

  /// Creates a [SeedMigrationRunner] with an optional [seedStrategy].
  ///
  /// Defaults to [DomainSeedStrategy] if no custom strategy is provided.
  SeedMigrationRunner({SeedStrategy? seedStrategy})
      : seedStrategy = seedStrategy ?? DomainSeedStrategy();

  /// Runs seed migration for the provided [Database] instance.
  ///
  /// Evaluates whether seed migration is required and executes [seedStrategy.seed].
  /// Returns `true` if migration succeeded.
  Future<bool> runMigration(Database db) async {
    await seedStrategy.seed(db);
    return true;
  }

  int? _firstIntValue(List<Map<String, Object?>> list) {
    if (list.isNotEmpty && list.first.isNotEmpty) {
      final val = list.first.values.first;
      if (val is num) return val.toInt();
    }
    return null;
  }

  /// Verifies whether seed migration is required for the target [db].
  ///
  /// Checks if necessary domain tables are empty or missing expected seed markers.
  Future<bool> isMigrationNeeded(Database db) async {
    try {
      final res = await db.rawQuery('SELECT COUNT(*) FROM type_definitions');
      final count = _firstIntValue(res);
      return count == null || count == 0;
    } catch (_) {
      return true;
    }
  }
}

