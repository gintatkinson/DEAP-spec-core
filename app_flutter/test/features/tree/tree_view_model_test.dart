import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/domain_errors.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/tree/view_models/tree_view_model.dart';

class _MockTreeRepository implements TreeRepository {
  List<TreeNode> roots = [];
  Map<String, List<TreeNode>> childrenMap = {};
  bool returnError = false;

  @override
  Future<Result<List<TreeNode>>> fetchRootNodes() async {
    if (returnError) return const Result.failure(SchemaFieldRequiredError(fieldName: 'root', schemaName: 'tree'));
    return Result.success(roots);
  }

  @override
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId) async {
    if (returnError) return const Result.failure(SchemaFieldRequiredError(fieldName: 'children', schemaName: 'tree'));
    return Result.success(childrenMap[parentId] ?? []);
  }
}

void main() {
  group('TreeViewModel BDD Unit Tests', () {
    late _MockTreeRepository mockRepo;
    late TreeViewModel viewModel;

    setUp(() {
      mockRepo = _MockTreeRepository();
      viewModel = TreeViewModel(mockRepo);
    });

    test('shouldReturnEmptyTreeDataInitially', () {
      expect(viewModel.treeData, isEmpty);
      expect(viewModel.currentView, isEmpty);
    });

    test('shouldLoadTreeRootsSuccess', () async {
      mockRepo.roots = const [
        TreeNode(id: 'node1', label: 'Node 1'),
      ];

      await viewModel.loadTree();

      expect(viewModel.treeData.length, 1);
      expect(viewModel.treeData.first.id, 'node1');
      expect(viewModel.currentView, 'node1');
    });

    test('shouldSupportImmutableTreeStateCopyWithAndEquality', () {
      const state1 = TreeState();
      const state2 = TreeState();

      expect(state1, equals(state2));
      expect(state1.hashCode, equals(state2.hashCode));

      final updatedState = state1.copyWith(currentView: 'node1');
      expect(updatedState.currentView, equals('node1'));
      expect(updatedState, isNot(equals(state1)));
    });

    test('shouldTriggerFlightAndClearFlightTarget', () {
      viewModel.triggerFlight('nodeA');
      expect(viewModel.flightTarget, equals('nodeA'));

      viewModel.clearFlightTarget();
      expect(viewModel.flightTarget, isNull);
    });

    test('shouldIdentifyPrimitiveAttributesAndContainerEntities', () {
      const macNode = TreeNode(id: 'mac_1', label: 'MAC Address');
      const ipVersionNode = TreeNode(id: 'IP Version', label: 'ip_ver');
      const asNumberNode = TreeNode(id: 'as_num', label: 'AS Number');
      const gaugeNode = TreeNode(id: 'gauge32_node', label: 'Gauge 32');
      const counterNode = TreeNode(id: 'counter_node', label: 'Counter 32');
      const ipv4Node = TreeNode(id: 'ipv4_addr', label: 'IPv4 Address');
      const ipv6Node = TreeNode(id: 'ipv6_addr', label: 'IPv6 Address');

      const rackNode = TreeNode(id: 'rack_1', label: 'Rack');
      const neNode = TreeNode(id: 'ne_1', label: 'NetworkElement');
      const compNode = TreeNode(id: 'comp_1', label: 'Component');
      const locNode = TreeNode(id: 'loc_1', label: 'Location');

      expect(isPrimitiveAttribute(macNode), isTrue);
      expect(isPrimitiveAttribute(ipVersionNode), isTrue);
      expect(isPrimitiveAttribute(asNumberNode), isTrue);
      expect(isPrimitiveAttribute(gaugeNode), isTrue);
      expect(isPrimitiveAttribute(counterNode), isTrue);
      expect(isPrimitiveAttribute(ipv4Node), isTrue);
      expect(isPrimitiveAttribute(ipv6Node), isTrue);

      expect(isContainerEntity(rackNode), isTrue);
      expect(isContainerEntity(neNode), isTrue);
      expect(isContainerEntity(compNode), isTrue);
      expect(isContainerEntity(locNode), isTrue);

      expect(isContainerEntity(macNode), isFalse);
    });

    test('shouldFilterOutPrimitiveAttributesFromRootTreeNodes', () async {
      mockRepo.roots = const [
        TreeNode(id: 'ne_1', label: 'NetworkElement'),
        TreeNode(id: 'mac_1', label: 'MAC Address'),
        TreeNode(id: 'rack_1', label: 'Rack'),
        TreeNode(id: 'ipv4_1', label: 'IPv4 Address'),
        TreeNode(id: 'comp_1', label: 'Component'),
        TreeNode(id: 'loc_1', label: 'Location'),
        TreeNode(id: 'as_1', label: 'AS Number'),
      ];

      await viewModel.loadTree();

      final rootIds = viewModel.treeData.map((n) => n.id).toList();
      expect(rootIds, containsAll(['comp_1', 'loc_1', 'ne_1', 'rack_1']));
      expect(rootIds, isNot(contains('mac_1')));
      expect(rootIds, isNot(contains('ipv4_1')));
      expect(rootIds, isNot(contains('as_1')));
      expect(viewModel.treeData.length, equals(4));
    });
  });
}
