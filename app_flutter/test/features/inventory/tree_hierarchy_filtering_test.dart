/// Realises: [Feat-10/TreeViewModel]
///
/// BDD acceptance test for Tree Hierarchy Filtering (Container-Only Root Nodes).
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/tree/view_models/tree_view_model.dart';

/// Realises: [Feat-10/TreeViewModel]
///
/// In-memory repository simulating data source for tree hierarchy filtering BDD acceptance tests.
class InMemoryTreeRepository implements TreeRepository {
  /// Member documentation.
  List<TreeNode> roots = <TreeNode>[];

  @override
  Future<Result<List<TreeNode>>> fetchRootNodes() async {
    return Result.success(roots);
  }

  @override
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId) async {
    return const Result.success(<TreeNode>[]);
  }
}

void main() {
  group('Feature: Tree Hierarchy Filtering (Container-Only Root Nodes)', () {
    late InMemoryTreeRepository mockRepo;
    late TreeViewModel viewModel;

    setUp(() {
      mockRepo = InMemoryTreeRepository();
      viewModel = TreeViewModel(mockRepo);
    });

    test(
        'Scenario: Given a data repository containing container entities and primitive leaf attribute descriptors, '
        'When TreeViewModel.loadTree() is executed, Then only container entities appear as root navigation nodes '
        'and primitive leaf attribute descriptors are hidden', () async {
      // Given: A data repository containing container entities and primitive leaf attribute descriptors
      mockRepo.roots = const <TreeNode>[
        TreeNode(id: 'ne_01', label: 'NetworkElement'),
        TreeNode(id: 'mac_01', label: 'MAC Address'),
        TreeNode(id: 'rack_01', label: 'Rack'),
        TreeNode(id: 'ip_ver_01', label: 'IP Version'),
        TreeNode(id: 'comp_01', label: 'Component'),
        TreeNode(id: 'as_num_01', label: 'AS Number'),
        TreeNode(id: 'loc_01', label: 'Location'),
        TreeNode(id: 'gauge_01', label: 'Gauge 32'),
        TreeNode(id: 'counter_01', label: 'Counter 32'),
      ];

      // When: TreeViewModel.loadTree() is executed
      await viewModel.loadTree();

      // Then: Only container entities appear as root navigation nodes and primitive leaf attribute descriptors are hidden
      final List<String> rootNodeIds = viewModel.treeData.map((TreeNode node) => node.id).toList();
      final List<String> rootNodeLabels = viewModel.treeData.map((TreeNode node) => node.label).toList();

      // Container entities must be present
      expect(rootNodeLabels, containsAll(<String>['Component', 'Location', 'NetworkElement', 'Rack']));
      expect(rootNodeIds, containsAll(<String>['comp_01', 'loc_01', 'ne_01', 'rack_01']));

      // Primitive leaf attribute descriptors must NOT be present
      expect(rootNodeLabels, isNot(contains('MAC Address')));
      expect(rootNodeLabels, isNot(contains('IP Version')));
      expect(rootNodeLabels, isNot(contains('AS Number')));
      expect(rootNodeLabels, isNot(contains('Gauge 32')));
      expect(rootNodeLabels, isNot(contains('Counter 32')));

      // Total count of root nodes must be exactly 4 container entities
      expect(viewModel.treeData.length, equals(4));

      // Each root node in treeData must satisfy isContainerEntity and not isPrimitiveAttribute
      for (final TreeNode node in viewModel.treeData) {
        expect(isContainerEntity(node), isTrue);
        expect(isPrimitiveAttribute(node), isFalse);
      }
    });
  });
}
