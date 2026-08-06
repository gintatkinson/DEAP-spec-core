import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/domain/instance_record.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/topology/topology_map.dart' show TopologyData, TopologyNode, TopologyLink, TopologyNodePosition;

/// Realises: [Feat-10/DataSource]
/// [DataSource] implementation backed by the local SQLite database.
class SqliteDataSource implements DataSource {
  /// Member documentation.
  SqliteDataSource(this._db);
  final Database _db;
  final StreamController<Map<String, dynamic>> _propertiesController =
      StreamController<Map<String, dynamic>>.broadcast();
  List<TypeDescriptor>? _cachedTypes;

  @override
  String get name => 'sqlite';

  @override
  Future<Result<void>> dispose() async {
    _cachedTypes = null;
    await _propertiesController.close();
    await _db.close();
    return const Result.success(null);
  }

  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async {
    if (_cachedTypes != null) return Result.success(_cachedTypes!);
    try {
      final typeRows = await _db.query('type_definitions');
      final allAttrRows = await _db.query('type_attributes', orderBy: 'section_order, id');
      final allRelRows = await _db.query('type_relations');

      final attrsByType = <String, List<Map<String, dynamic>>>{};
      for (final row in allAttrRows) {
        final tn = row['type_name'] as String;
        (attrsByType[tn] ??= []).add(row);
      }
      final relsByType = <String, List<Map<String, dynamic>>>{};
      for (final row in allRelRows) {
        final tn = row['parent_type_name'] as String;
        (relsByType[tn] ??= []).add(row);
      }

      final types = typeRows.map((typeRow) {
        final typeName = typeRow['type_name'] as String;
        final attrRows = attrsByType[typeName] ?? [];
        final relRows = relsByType[typeName] ?? [];
        final childRows = relRows.where((r) => r['relation_name'] == 'contains');
        final relatedRows = relRows.where((r) => r['relation_name'] != 'contains');
        return TypeDescriptor(
          typeName: typeName,
          displayName: typeRow['display_name'] as String,
          iconName: typeRow['icon_name'] as String,
          fields: attrRows.map(_parseField).toList(),
          childTypes: childRows.map((r) => TypeRelationDescriptor(
            relationName: r['relation_name'] as String,
            childTypeName: r['child_type_name'] as String,
            childLabel: r['child_label'] as String,
          )).toList(),
          relatedTypes: relatedRows.map((r) => TypeRelationDescriptor(
            relationName: r['relation_name'] as String,
            childTypeName: r['child_type_name'] as String,
            childLabel: r['child_label'] as String,
          )).toList(),
          parentTypes: [],
        );
      }).toList();
      _cachedTypes = types;
      return Result.success(types);
    } catch (e, stackTrace) {
      debugPrint('Error in discoverTypes: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<TypeDescriptor?>> typeFor(String typeName) async {
    try {
      var rows = await _db.query('type_definitions',
          where: 'type_name = ?', whereArgs: [typeName]);
      if (rows.isEmpty) {
        List<Map<String, dynamic>> instanceRows = [];
        try {
          instanceRows = await _db.query('instances',
              columns: ['type_name'], where: 'node_id = ?', whereArgs: [typeName]);
        } catch (_) {
          instanceRows = await _db.query('instances',
              columns: ['type_name'], where: 'id = ?', whereArgs: [typeName]);
        }
        if (instanceRows.isNotEmpty && instanceRows.first['type_name'] != null) {
          final resolvedType = instanceRows.first['type_name'] as String;
          rows = await _db.query('type_definitions',
              where: 'type_name = ?', whereArgs: [resolvedType]);
        }
      }
      if (rows.isEmpty) return const Result.success(null);
      final descriptor = await _buildType(rows.first);
      return Result.success(descriptor);
    } catch (e, stackTrace) {
      debugPrint('Error in typeFor($typeName): $e\n$stackTrace');
      return const Result.success(null);
    }
  }

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async {
    try {
      final rows = await _db.query(
        'type_relations',
        where: "relation_name = 'contains'",
      );
      final hierarchy = rows.map((r) => (
        r['parent_type_name'] as String,
        r['child_type_name'] as String,
      )).toList();
      return Result.success(hierarchy);
    } catch (e, stackTrace) {
      debugPrint('Error in discoverHierarchy: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<Map<String, dynamic>>> fetchProperties(String nodeId) async {
    final props = await _fetchPropertiesRaw(nodeId);
    return Result.success(props);
  }

  Future<Map<String, dynamic>> _fetchPropertiesRaw(String nodeId) async {
    try {
      final maps = await _db.query(
        'properties',
        columns: ['data_json'],
        where: 'node_id = ?',
        whereArgs: [nodeId],
      );
      if (maps.isEmpty) return {};
      final dataJson = maps.first['data_json'] as String?;
      if (dataJson == null) return {};
      final decoded = Map<String, dynamic>.from(jsonDecode(dataJson) as Map);
      return _flatten(decoded);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchProperties($nodeId): $e\n$stackTrace');
      return {};
    }
  }

  @override
  Future<Result<void>> saveProperties(String nodeId, Map<String, dynamic> data) async {
    try {
      final unflattened = _unflatten(data);
      final dataJson = jsonEncode(unflattened);
      await _db.rawInsert('''
        INSERT INTO properties (node_id, data_json)
        VALUES (?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
          data_json = excluded.data_json
      ''', [nodeId, dataJson]);
      _propertiesController.add({'nodeId': nodeId, 'data': data});
      return const Result.success(null);
    } catch (e, stackTrace) {
      debugPrint('Error in saveProperties($nodeId): $e\n$stackTrace');
      return const Result.success(null);
    }
  }

  @override
  Stream<Result<Map<String, dynamic>>> watchProperties(String nodeId) async* {
    yield Result.success(await _fetchPropertiesRaw(nodeId));
    await for (final event in _propertiesController.stream) {
      if (event['nodeId'] == nodeId) {
        yield Result.success(event['data'] as Map<String, dynamic>);
      }
    }
  }

  @override
  Future<Result<List<InstanceRecord>>> fetchRelatedInstances({
    required String parentNodeId,
    required TypeDescriptor targetType,
  }) async {
    try {
      final rows = await _db.query(
        'instances',
        where: 'parent_node_id = ? AND type_name = ?',
        whereArgs: [parentNodeId, targetType.typeName],
      );
      final records = await compute(
        (args) => (args[0] as List<Map<String, dynamic>>)
            .map((r) => InstanceRecord.fromMap(r, args[1] as String))
            .toList(),
        [rows, targetType.typeName],
      );
      return Result.success(records);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchRelatedInstances: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<List<TreeNode>>> fetchRootNodes() async {
    try {
      final rows = await _db.rawQuery('''
        SELECT p.node_id, td.display_name,
          (SELECT COUNT(*) FROM properties c WHERE c.parent_node_id = p.node_id) > 0 as has_children
        FROM properties p
        LEFT JOIN type_definitions td ON p.node_id = td.type_name
        WHERE p.parent_node_id IS NULL
        ORDER BY p.node_id
      ''');
      final roots = rows.map((r) {
        final id = r['node_id'] as String;
        final label = (r['display_name'] as String?) ?? id.replaceAll('_', ' ');
        final hasChildren = (r['has_children'] as int? ?? 0) > 0;
        return TreeNode(
          id: id,
          label: label,
          children: hasChildren ? const [] : null,
        );
      }).toList();
      return Result.success(roots);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchRootNodes: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId) async {
    try {
      final rows = await _db.rawQuery('''
        SELECT node_id, display_name, has_children FROM (
          SELECT p.node_id as node_id, td.display_name as display_name,
            (SELECT COUNT(*) FROM properties c WHERE c.parent_node_id = p.node_id) > 0 as has_children
          FROM properties p
          LEFT JOIN type_definitions td ON p.node_id = td.type_name
          WHERE p.parent_node_id = ?

          UNION ALL

          SELECT r.child_type_name as node_id, td.display_name as display_name,
            0 as has_children
          FROM type_relations r
          LEFT JOIN type_definitions td ON r.child_type_name = td.type_name
          WHERE r.parent_type_name = ? AND r.relation_name = 'contains'
            AND r.child_type_name NOT IN ('Components', 'Relation_A', 'Relation_B')
            AND r.child_type_name NOT IN (SELECT node_id FROM properties WHERE parent_node_id = ?)
            AND r.child_type_name IN (SELECT type_name FROM instances WHERE parent_node_id = ?)
        )
        ORDER BY (CASE WHEN node_id LIKE '%_Child_%' OR node_id LIKE '%_Grandchild_%' THEN 1 ELSE 0 END), node_id
      ''', [parentId, parentId, parentId, parentId]);
      final children = rows.map((r) {
        final id = r['node_id'] as String;
        final label = (r['display_name'] as String?) ?? id.replaceAll('_', ' ');
        final hasChildren = (r['has_children'] as int? ?? 0) > 0;
        return TreeNode(
          id: id,
          label: label,
          children: hasChildren ? const [] : null,
        );
      }).toList();
      return Result.success(children);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchChildrenForNode: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  Future<TypeDescriptor> _buildType(Map<String, dynamic> typeRow) async {
    final typeName = typeRow['type_name'] as String;
    final attrRows = await _db.query('type_attributes',
        where: 'type_name = ?',
        whereArgs: [typeName],
        orderBy: 'section_order, id');
    final relRows = await _db.query('type_relations',
        where: 'parent_type_name = ?', whereArgs: [typeName]);

    final childRows = relRows.where((r) => r['relation_name'] == 'contains');
    final relatedRows = relRows.where((r) => r['relation_name'] != 'contains');

    return TypeDescriptor(
      typeName: typeName,
      displayName: typeRow['display_name'] as String,
      iconName: typeRow['icon_name'] as String,
      fields: attrRows.map(_parseField).toList(),
      childTypes: childRows.map((r) => TypeRelationDescriptor(
        relationName: r['relation_name'] as String,
        childTypeName: r['child_type_name'] as String,
        childLabel: r['child_label'] as String,
      )).toList(),
      relatedTypes: relatedRows.map((r) => TypeRelationDescriptor(
        relationName: r['relation_name'] as String,
        childTypeName: r['child_type_name'] as String,
        childLabel: r['child_label'] as String,
      )).toList(),
      parentTypes: [],
    );
  }

  FieldDescriptor _parseField(Map<String, dynamic> row) {
    List<String>? parseJsonList(String? raw) {
      if (raw == null || raw.isEmpty) return null;
      return (jsonDecode(raw) as List).cast<String>();
    }

    return FieldDescriptor(
      key: row['attr_key'] as String,
      label: row['label'] as String,
      type: row['attr_type'] as String,
      sectionLabel: row['section_label'] as String?,
      sectionOrder: row['section_order'] as int? ?? 0,
      required: (row['is_required'] as int? ?? 0) == 1,
      minValue: row['min_value'] as num?,
      maxValue: row['max_value'] as num?,
      pattern: row['pattern'] as String?,
      enumOptions: parseJsonList(row['enum_options'] as String?),
      enumDisplayNames: parseJsonList(row['enum_display_names'] as String?),
      defaultValue: row['default_value'],
      inputFormatters: parseJsonList(row['input_formatters'] as String?),
    );
  }

  Map<String, dynamic> _flatten(Map<String, dynamic> map, {String prefix = ''}) {
    final result = <String, dynamic>{};
    map.forEach((key, value) {
      final newKey = prefix.isEmpty ? key : '$prefix.$key';
      if (value is Map) {
        result.addAll(_flatten(Map<String, dynamic>.from(value), prefix: newKey));
      } else {
        result[newKey] = value;
      }
    });
    return result;
  }

  Map<String, dynamic> _unflatten(Map<String, dynamic> map) {
    final result = <String, dynamic>{};
    map.forEach((key, value) {
      final parts = key.split('.');
      Map<String, dynamic> current = result;
      for (int i = 0; i < parts.length - 1; i++) {
        final part = parts[i];
        if (!current.containsKey(part) || current[part] is! Map) {
          current[part] = <String, dynamic>{};
        }
        current = current[part] as Map<String, dynamic>;
      }
      current[parts.last] = value;
    });
    return result;
  }

  @override
  Future<Result<TopologyData>> fetchTopologyData() async {
    try {
      final rows = await _db.query('properties');
      final interfaceRows = await _db.query(
        'instances',
        where: "type_name = 'interface'",
      );
      final topologyData = await compute(_parseTopologyData, <dynamic>[rows, interfaceRows]);
      return Result.success(topologyData);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchTopologyData: $e\n$stackTrace');
      return const Result.success(TopologyData(coordinateMapping: {}, nodes: [], links: []));
    }
  }

  static String? _findPathToKey(Map<dynamic, dynamic> map, String targetKey) {
    for (final entry in map.entries) {
      final keyStr = entry.key.toString();
      if (keyStr == targetKey) {
        return keyStr;
      }
      if (entry.value is Map) {
        final subPath = _findPathToKey(entry.value as Map, targetKey);
        if (subPath != null) {
          return '$keyStr/$subPath';
        }
      }
    }
    return null;
  }

  static double? _resolveCoordinateValue(Map<dynamic, dynamic> properties, String path) {
    final parts = path.split('/');
    dynamic current = properties;
    for (final part in parts) {
      if (current is Map) {
        current = current[part];
      } else {
        return null;
      }
    }
    if (current != null) {
      return double.tryParse(current.toString());
    }
    return null;
  }

  static TopologyData _parseTopologyData(List<dynamic> args) {
    final rows = args[0] as List<Map<String, dynamic>>;
    final interfaceRows = args[1] as List<Map<String, dynamic>>;
    final List<TopologyNode> nodes = [];
    final List<TopologyLink> links = [];

    String? globalLatPath;
    String? globalLngPath;
    String? globalAltPath;

    for (final r in rows) {
      final nodeId = r['node_id'] as String;
      final dataJson = r['data_json'] as String?;
      if (dataJson == null || dataJson.isEmpty || dataJson == '{}') continue;

      try {
        final decoded = Map<String, dynamic>.from(jsonDecode(dataJson) as Map);

        final latPath = _findPathToKey(decoded, 'latitude');
        final lngPath = _findPathToKey(decoded, 'longitude');
        final altPath = _findPathToKey(decoded, 'height') ?? _findPathToKey(decoded, 'altitude');

        if (latPath == null || lngPath == null) continue;

        globalLatPath ??= latPath;
        globalLngPath ??= lngPath;
        globalAltPath ??= altPath;

        final latVal = _resolveCoordinateValue(decoded, latPath);
        final lngVal = _resolveCoordinateValue(decoded, lngPath);
        final altVal = altPath != null ? _resolveCoordinateValue(decoded, altPath) : null;

        if (latVal == null || lngVal == null) continue;

        nodes.add(TopologyNode(
          id: nodeId,
          label: decoded['name']?.toString() ?? nodeId,
          position: TopologyNodePosition(
            dim0: lngVal,
            dim1: latVal,
            dim2: altVal ?? 0.0,
            timeIndex: 0,
            vector: const [],
          ),
          status: decoded['status']?.toString() ?? 'Active',
          rawProperties: decoded,
        ));
      } catch (_) {}
    }

    final regExp = RegExp(r'link to node\s+([\w\-]+)');
    for (final row in interfaceRows) {
      final parentNodeId = row['parent_node_id'] as String;
      final dataJson = row['data_json'] as String?;
      if (dataJson == null || dataJson.isEmpty || dataJson == '{}') continue;

      try {
        final decoded = Map<String, dynamic>.from(jsonDecode(dataJson) as Map);
        final description = decoded['description']?.toString();
        if (description != null) {
          final match = regExp.firstMatch(description);
          if (match != null) {
            final targetNodeId = match.group(1)!;
            links.add(TopologyLink(
              source: parentNodeId,
              target: targetNodeId,
              type: 'interface',
            ));
          }
        }
      } catch (_) {}
    }

    final coordinateMapping = <String, String>{};
    if (globalLngPath != null) {
      coordinateMapping['x'] = globalLngPath;
    }
    if (globalLatPath != null) {
      coordinateMapping['y'] = globalLatPath;
    }
    if (globalAltPath != null) {
      coordinateMapping['z'] = globalAltPath;
    }

    return TopologyData(
      coordinateMapping: coordinateMapping,
      nodes: nodes,
      links: links,
    );
  }
}

