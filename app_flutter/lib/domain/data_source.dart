import 'package:flutter/foundation.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/topology/topology_map.dart' show TopologyData;
import 'instance_record.dart';
import 'result.dart';
import 'type_descriptor.dart';

/// Realises: [Feat-10/TypeRepository]
///
/// Repository interface for type discovery and schema management.
abstract interface class TypeRepository {
  /// Discover all object types known to this data source.
  Future<Result<List<TypeDescriptor>>> discoverTypes();

  /// Get the [TypeDescriptor] for a specific type by its [typeName].
  Future<Result<TypeDescriptor?>> typeFor(String typeName);

  /// Discover the tree hierarchy: parent-child relationships.
  Future<Result<List<(String, String)>>> discoverHierarchy();
}

/// Realises: [Feat-10/PropertyRepository]
///
/// Repository interface for node property read and write operations.
abstract interface class PropertyRepository {
  /// Fetches the property map for the node identified by [nodeId].
  Future<Result<Map<String, dynamic>>> fetchProperties(String nodeId);

  /// Persists [data] as the properties for [nodeId].
  Future<Result<void>> saveProperties(String nodeId, Map<String, dynamic> data);

  /// Returns a broadcast stream emitting property updates for [nodeId].
  Stream<Result<Map<String, dynamic>>> watchProperties(String nodeId);
}

/// Realises: [Feat-10/TreeRepository]
///
/// Repository interface for tree hierarchy queries.
abstract interface class TreeRepository {
  /// Fetches root nodes for display in the tree view.
  Future<Result<List<TreeNode>>> fetchRootNodes();

  /// Fetches child nodes for a given parent node.
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId);
}

/// Realises: [Feat-10/TopologyRepository]
///
/// Repository interface for topology data queries.
abstract interface class TopologyRepository {
  /// Fetches all active nodes and links for topology mapping.
  Future<Result<TopologyData>> fetchTopologyData();
}

/// Realises: [Feat-10/InstanceRepository]
///
/// Repository interface for instance record queries.
abstract interface class InstanceRepository {
  /// Fetches related instances of [targetType] under [parentNodeId].
  Future<Result<List<InstanceRecord>>> fetchRelatedInstances({
    required String parentNodeId,
    required TypeDescriptor targetType,
  });
}

/// Realises: [Feat-10/DataSource]
///
/// Abstract interface for a swappable data backend composed of segregated repositories.
///
/// Implementations: [SqliteDataSource], [FirebaseDataSource], [GrpcDataSource].
abstract class DataSource
    implements
        TypeRepository,
        PropertyRepository,
        TreeRepository,
        TopologyRepository,
        InstanceRepository {
  /// Human-readable name, e.g. "sqlite", "firebase", "grpc".
  String get name;

  /// Releases all resources held by this data source.
  Future<Result<void>> dispose();
}

