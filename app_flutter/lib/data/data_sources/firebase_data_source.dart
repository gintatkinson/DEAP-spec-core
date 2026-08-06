import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:app_flutter/domain/instance_record.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/topology/topology_map.dart' show TopologyData, TopologyNode, TopologyNodePosition, TopologyLink;

/// Realises: [Feat-10/DataSource]
/// [DataSource] implementation backed by Cloud Firestore.
class FirebaseDataSource implements DataSource {
  /// Creates a [FirebaseDataSource] connected to the given [Firestore] instance.
  FirebaseDataSource(this._firestore);
  final FirebaseFirestore _firestore;
  List<TypeDescriptor>? _cachedTypes;

  @override
  String get name => 'firebase';

  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async {
    if (_cachedTypes != null) return Result.success(_cachedTypes!);
    try {
      final snapshot = await _firestore.collection('schema').doc('types').get();
      final data = snapshot.data();
      if (data == null) return const Result.success([]);
      final fields = data['fields'] as Map<String, dynamic>? ?? {};
      final types = <TypeDescriptor>[];
      for (final entry in fields.entries) {
        final typeName = entry.key;
        final def = entry.value as Map<String, dynamic>;
        types.add(TypeDescriptor(
          typeName: typeName,
          displayName: def['displayName'] as String? ?? typeName,
          iconName: def['iconName'] as String? ?? 'insert_drive_file',
          fields: _parseFields(def['fields'] as List<dynamic>?),
          childTypes: _parseRelations(def['childTypes'] as List<dynamic>?),
          relatedTypes: _parseRelations(def['relatedTypes'] as List<dynamic>?),
          parentTypes: _parseRelations(def['parentTypes'] as List<dynamic>?),
        ));
      }
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
      final res = await discoverTypes();
      final types = res.isSuccess ? (res as Success<List<TypeDescriptor>>).value : <TypeDescriptor>[];
      for (final t in types) {
        if (t.typeName == typeName) return Result.success(t);
      }
      return const Result.success(null);
    } catch (e, stackTrace) {
      debugPrint('Error in typeFor($typeName): $e\n$stackTrace');
      return const Result.success(null);
    }
  }

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async {
    try {
      final snapshot = await _firestore.collection('schema').doc('hierarchy').get();
      final data = snapshot.data();
      if (data == null) return const Result.success([]);
      final pairs = data['pairs'] as List<dynamic>? ?? [];
      final resultPairs = pairs.map((p) {
        final pair = p as List<dynamic>;
        return (pair[0] as String, pair[1] as String);
      }).toList();
      return Result.success(resultPairs);
    } catch (e, stackTrace) {
      debugPrint('Error in discoverHierarchy: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<Map<String, dynamic>>> fetchProperties(String nodeId) async {
    try {
      final doc = await _firestore.collection('data').doc(nodeId).get();
      final data = doc.data();
      if (data == null) return const Result.success({});
      return Result.success(Map<String, dynamic>.from(data));
    } catch (e, stackTrace) {
      debugPrint('Error in fetchProperties($nodeId): $e\n$stackTrace');
      return const Result.success({});
    }
  }

  @override
  Future<Result<void>> saveProperties(String nodeId, Map<String, dynamic> data) async {
    try {
      await _firestore.collection('data').doc(nodeId).set(data, SetOptions(merge: true));
      return const Result.success(null);
    } catch (e, stackTrace) {
      debugPrint('Error in saveProperties($nodeId): $e\n$stackTrace');
      return const Result.success(null);
    }
  }

  @override
  Stream<Result<Map<String, dynamic>>> watchProperties(String nodeId) {
    return _firestore
        .collection('data')
        .doc(nodeId)
        .snapshots()
        .map((snapshot) {
          final data = Map<String, dynamic>.from(snapshot.data() as Map? ?? {});
          return Result.success(data);
        });
  }

  @override
  Future<Result<List<InstanceRecord>>> fetchRelatedInstances({
    required String parentNodeId,
    required TypeDescriptor targetType,
  }) async {
    try {
      final snapshot = await _firestore
          .collection('instances')
          .where('parent_node_id', isEqualTo: parentNodeId)
          .where('type_name', isEqualTo: targetType.typeName)
          .get();
      final rawDocs = snapshot.docs.map((d) => {
        'id': d.id,
        'data': d.data(),
      }).toList();
      final records = await compute(
        (args) {
          final docs = args[0] as List<Map<String, dynamic>>;
          final pId = args[1] as String;
          final tName = args[2] as String;
          return docs.map((doc) {
            return InstanceRecord(
              id: doc['id'] as String,
              parentNodeId: pId,
              typeName: tName,
              attributes: doc['data'] as Map<String, dynamic>,
            );
          }).toList();
        },
        [rawDocs, parentNodeId, targetType.typeName],
      );
      return Result.success(records);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchRelatedInstances: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  List<FieldDescriptor> _parseFields(List<dynamic>? fields) {
    if (fields == null) return [];
    return fields.map((f) {
      final map = f as Map<String, dynamic>;
      return FieldDescriptor(
        key: map['key'] as String,
        label: map['label'] as String,
        type: map['type'] as String,
        sectionLabel: map['sectionLabel'] as String?,
        sectionOrder: map['sectionOrder'] as int? ?? 0,
        required: map['required'] as bool? ?? false,
        minValue: map['minValue'] as num?,
        maxValue: map['maxValue'] as num?,
        pattern: map['pattern'] as String?,
        enumOptions: map['enumOptions'] != null
            ? List<String>.from(map['enumOptions'] as List)
            : null,
        enumDisplayNames: map['enumDisplayNames'] != null
            ? List<String>.from(map['enumDisplayNames'] as List)
            : null,
        defaultValue: map['defaultValue'],
        inputFormatters: map['inputFormatters'] != null
            ? List<String>.from(map['inputFormatters'] as List)
            : null,
      );
    }).toList();
  }

  List<TypeRelationDescriptor> _parseRelations(List<dynamic>? relations) {
    if (relations == null) return [];
    return relations.map((r) {
      final map = r as Map<String, dynamic>;
      return TypeRelationDescriptor(
        relationName: map['relationName'] as String,
        childTypeName: map['childTypeName'] as String,
        childLabel: map['childLabel'] as String,
      );
    }).toList();
  }

  @override
  Future<Result<List<TreeNode>>> fetchRootNodes() async {
    try {
      final typesRes = await discoverTypes();
      final types = typesRes.isSuccess ? (typesRes as Success<List<TypeDescriptor>>).value : <TypeDescriptor>[];
      final typeMap = {for (final t in types) t.typeName: t};

      final snapshot = await _firestore
          .collection('data')
          .where('parent_node_id', isNull: true)
          .get();

      final List<TreeNode> roots = [];
      for (final doc in snapshot.docs) {
        final id = doc.id;
        final docData = doc.data();
        final typeName = docData['type_name'] as String? ?? id;
        final displayNameFromDoc = docData['name']?.toString() ?? docData['displayName']?.toString();
        final typeDesc = typeMap[id] ?? typeMap[typeName];
        final label = displayNameFromDoc ?? typeDesc?.displayName ?? id.replaceAll('_', ' ');

        final hasChildren = docData['has_children'] as bool? ?? false;

        roots.add(TreeNode(
          id: id,
          label: label,
          children: hasChildren ? const [] : null,
        ));
      }

      roots.sort((a, b) => a.id.compareTo(b.id));
      return Result.success(roots);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchRootNodes: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId) async {
    try {
      final typesRes = await discoverTypes();
      final types = typesRes.isSuccess ? (typesRes as Success<List<TypeDescriptor>>).value : <TypeDescriptor>[];
      final typeMap = {for (final t in types) t.typeName: t};

      final parentDoc = await _firestore.collection('data').doc(parentId).get();
      final parentData = parentDoc.data();
      final parentTypeName = parentData?['type_name']?.toString() ?? parentId;

      final childrenSnapshot = await _firestore
          .collection('data')
          .where('parent_node_id', isEqualTo: parentId)
          .get();

      final List<TreeNode> nodes = [];
      final Set<String> childIdsInProperties = {};

      for (final doc in childrenSnapshot.docs) {
        final id = doc.id;
        childIdsInProperties.add(id);
        final docData = doc.data();
        final typeName = docData['type_name'] as String? ?? id;
        final displayNameFromDoc = docData['name']?.toString() ?? docData['displayName']?.toString();
        final typeDesc = typeMap[id] ?? typeMap[typeName];
        final label = displayNameFromDoc ?? typeDesc?.displayName ?? id.replaceAll('_', ' ');

        final hasChildren = docData['has_children'] as bool? ?? false;

        nodes.add(TreeNode(
          id: id,
          label: label,
          children: hasChildren ? const [] : null,
        ));
      }

      final parentType = typeMap[parentTypeName];
      if (parentType != null) {
        for (final relation in parentType.childTypes) {
          final childTypeName = relation.childTypeName;
          if (const ['Components', 'Relation_A', 'Relation_B'].contains(childTypeName)) {
            continue;
          }
          if (childIdsInProperties.contains(childTypeName)) {
            continue;
          }

          final instancesSnapshot = await _firestore
              .collection('instances')
              .where('parent_node_id', isEqualTo: parentId)
              .where('type_name', isEqualTo: childTypeName)
              .limit(1)
              .get();

          if (instancesSnapshot.docs.isNotEmpty) {
            nodes.add(TreeNode(
              id: childTypeName,
              label: relation.childLabel,
              children: null,
            ));
          }
        }
      }

      nodes.sort((a, b) {
        final aMatches = a.id.contains('_Child_') || a.id.contains('_Grandchild_');
        final bMatches = b.id.contains('_Child_') || b.id.contains('_Grandchild_');
        if (aMatches != bMatches) {
          return aMatches ? 1 : -1;
        }
        return a.id.compareTo(b.id);
      });

      return Result.success(nodes);
    } catch (e, stackTrace) {
      debugPrint('Error in fetchChildrenForNode: $e\n$stackTrace');
      return const Result.success([]);
    }
  }

  @override
  Future<Result<TopologyData>> fetchTopologyData() async {
    try {
      final snapshot = await _firestore
          .collection('data')
          .where('has_location', isEqualTo: true)
          .get();
      final List<TopologyNode> nodes = [];
      final List<TopologyLink> links = [];

      String? globalLatPath;
      String? globalLngPath;
      String? globalAltPath;

      for (final doc in snapshot.docs) {
        final nodeId = doc.id;
        final decoded = doc.data();
        if (decoded.isEmpty) continue;

        try {
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

      final interfaceSnapshot = await _firestore
          .collection('instances')
          .where('type_name', isEqualTo: 'interface')
          .get();

      final regExp = RegExp(r'link to node\s+([\w\-]+)');
      for (final doc in interfaceSnapshot.docs) {
        final parentNodeId = doc.data()['parent_node_id']?.toString() ?? '';
        final description = doc.data()['description']?.toString();
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

      return Result.success(TopologyData(
        coordinateMapping: coordinateMapping,
        nodes: nodes,
        links: links,
      ));
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

  @override
  Future<Result<void>> dispose() async => const Result.success(null);
}

