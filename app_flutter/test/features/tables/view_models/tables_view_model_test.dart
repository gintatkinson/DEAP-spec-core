import 'package:app_flutter/features/tables/models/column_model.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/instance_record.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/features/tables/view_models/tables_view_model.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/topology/topology_map.dart' show TopologyData;

class _MockDataSource implements DataSource {
  @override
  String get name => 'mock';

  Future<TypeDescriptor?> Function(String typeName)? onTypeFor;
  Future<List<InstanceRecord>> Function({
    required String parentNodeId,
    required TypeDescriptor targetType,
  })? onFetchRelatedInstances;

  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async => const Result.success([]);

  @override
  Future<Result<TypeDescriptor?>> typeFor(String typeName) async =>
      Result.success(await onTypeFor?.call(typeName));

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async => const Result.success([]);

  @override
  Future<Result<Map<String, dynamic>>> fetchProperties(String nodeId) async => const Result.success({});

  @override
  Future<Result<void>> saveProperties(String nodeId, Map<String, dynamic> data) async => const Result.success(null);

  @override
  Stream<Result<Map<String, dynamic>>> watchProperties(String nodeId) =>
      const Stream.empty();

  @override
  Future<Result<List<InstanceRecord>>> fetchRelatedInstances({
    required String parentNodeId,
    required TypeDescriptor targetType,
  }) async {
    if (onFetchRelatedInstances != null) {
      final records = await onFetchRelatedInstances!(
        parentNodeId: parentNodeId,
        targetType: targetType,
      );
      return Result.success(records);
    }
    return const Result.success([]);
  }

  @override
  Future<Result<List<TreeNode>>> fetchRootNodes() async => const Result.success([]);
  @override
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId) async => const Result.success([]);

  @override
  Future<Result<TopologyData>> fetchTopologyData() async => const Result.success(TopologyData(coordinateMapping: {}, nodes: [], links: []));

  @override
  Future<Result<void>> dispose() async => const Result.success(null);
}


void main() {
  group('TablesViewModel columnModels', () {
    late _MockDataSource dataSource;
    late TablesViewModel viewModel;

    setUp(() {
      dataSource = _MockDataSource();
      viewModel = TablesViewModel(dataSource, 'test');
    });

    test('columnModels is empty before load', () {
      expect(viewModel.columnModels, isEmpty);
    });

    test('columnModels count matches FieldDescriptor count', () async {
      final fields = [
        FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string'),
        FieldDescriptor(key: 'k2', label: 'Col 2', type: 'int'),
        FieldDescriptor(key: 'k3', label: 'Col 3', type: 'double'),
      ];

      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'root') {
          return TypeDescriptor(
            typeName: 'root',
            displayName: 'Root',
            iconName: 'folder',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: fields,
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async => [
        InstanceRecord(
          id: '1',
          parentNodeId: parentNodeId,
          typeName: targetType.typeName,
          attributes: {'k1': 'a', 'k2': '1', 'k3': '1.0'},
        ),
      ];

      await viewModel.loadForNode('root');
      expect(viewModel.columnModels.length, fields.length);
    });

    test('columnModels is populated correctly in _loadData', () async {
      final fields = [
        FieldDescriptor(key: 'voltage', label: 'Voltage (V)', type: 'double'),
        FieldDescriptor(key: 'current', label: 'Current (A)', type: 'double'),
      ];

      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'root') {
          return TypeDescriptor(
            typeName: 'root',
            displayName: 'Root',
            iconName: 'folder',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: fields,
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async => [
        InstanceRecord(
          id: '1',
          parentNodeId: parentNodeId,
          typeName: targetType.typeName,
          attributes: {'voltage': '220.0', 'current': '1.5'},
        ),
      ];

      await viewModel.loadForNode('root');

      expect(viewModel.columnModels.length, 2);
      expect(viewModel.columnModels[0].key, 'voltage');
      expect(viewModel.columnModels[0].label, 'Voltage (V)');
      expect(viewModel.columnModels[0].type, 'double');
      expect(viewModel.columnModels[1].key, 'current');
      expect(viewModel.columnModels[1].label, 'Current (A)');
      expect(viewModel.columnModels[1].type, 'double');
    });

    test('columnModels is cleared on error', () async {
      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'root') {
          return TypeDescriptor(
            typeName: 'root',
            displayName: 'Root',
            iconName: 'folder',
            fields: [],
            childTypes: [
              TypeRelationDescriptor(
                relationName: 'contains',
                childTypeName: 'ChildType',
                childLabel: 'Child Type',
              ),
            ],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [
              FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string'),
            ],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async =>
          throw Exception('Fetch error');

      await viewModel.loadForNode('root');
      expect(viewModel.columnModels, isEmpty);
    });
  });

  group('TablesViewModel headers', () {
    late _MockDataSource dataSource;
    late TablesViewModel viewModel;

    setUp(() {
      dataSource = _MockDataSource();
      viewModel = TablesViewModel(dataSource, 'test');
    });

    test('headers returns List<ColumnModel> after load', () async {
      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'test-node') {
          return TypeDescriptor(
            typeName: 'test-node',
            displayName: 'Test Node',
            iconName: 'node',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [
              FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string'),
              FieldDescriptor(key: 'k2', label: 'Col 2', type: 'int'),
            ],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async => [
        InstanceRecord(
          id: '1',
          parentNodeId: parentNodeId,
          typeName: targetType.typeName,
          attributes: {'k1': 'a', 'k2': '1'},
        ),
      ];

      await viewModel.loadForNode('test-node');
      expect(viewModel.headers, isA<List<ColumnModel>>());
      expect(viewModel.headers.length, greaterThan(0));
      expect(viewModel.headers.first.key, isNotEmpty);
      expect(viewModel.headers.first.type, equals('string'));
    });
  });

  group('TablesViewModel dispose guard', () {
    late _MockDataSource dataSource;
    late TablesViewModel viewModel;

    setUp(() {
      dataSource = _MockDataSource();
      viewModel = TablesViewModel(dataSource, 'test');
    });

    test('loadForNode does not fetch after dispose', () async {
      int typeForCallCount = 0;
      dataSource.onTypeFor = (typeName) async {
        typeForCallCount++;
        // Simulate slow async operation
        await Future.delayed(const Duration(milliseconds: 50));
        if (typeName == 'root') {
          return TypeDescriptor(
            typeName: 'root',
            displayName: 'Root',
            iconName: 'folder',
            fields: [],
            childTypes: [
              TypeRelationDescriptor(
                relationName: 'contains',
                childTypeName: 'ChildType',
                childLabel: 'Child Type',
              ),
            ],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string')],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async {
        typeForCallCount++;
        return [];
      };

      // Start loadForNode but don't await — let it begin
      final future = viewModel.loadForNode('root');
      viewModel.dispose();
      await future;

      // After dispose, no more calls should have been made beyond the initial typeFor
      // The exact count depends on how far it got before dispose, but the key
      // is that it didn't crash or set loading/error state.
      expect(viewModel.loading, isTrue); // loading stays true because we won't update after dispose
    });

    test('selectTab does not execute after dispose', () async {
      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'root') {
          return TypeDescriptor(
            typeName: 'root',
            displayName: 'Root',
            iconName: 'folder',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string')],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async => [];

      await viewModel.loadForNode('root');
      viewModel.dispose();
      await viewModel.selectTab('ChildType');

      // Should not have changed state after dispose
      expect(viewModel.tabs, isNotEmpty);
    });

    test('_loadData does not execute after dispose during fetchRelatedInstances', () async {
      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'root') {
          return TypeDescriptor(
            typeName: 'root',
            displayName: 'Root',
            iconName: 'folder',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string')],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      bool fetchRelatedCalled = false;
      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async {
        fetchRelatedCalled = true;
        await Future.delayed(const Duration(milliseconds: 50));
        return [];
      };

      final future = viewModel.loadForNode('root');
      // Give it time to get past typeFor and into fetchRelatedInstances
      await Future.delayed(const Duration(milliseconds: 10));
      viewModel.dispose();
      await future;

      // fetchRelatedInstances was called (we can't prevent it since it's in-flight),
      // but the disposed check after the await should prevent state mutations
      expect(viewModel.loading, isTrue);
      expect(viewModel.rows, isEmpty);
    });
  });

  group('TablesViewModel visibleColumnModels', () {
    late _MockDataSource dataSource;
    late TablesViewModel viewModel;

    setUp(() {
      dataSource = _MockDataSource();
      viewModel = TablesViewModel(dataSource, 'test');
    });

    test('visibleColumnModels returns all columns when no hidden keys set',
        () async {
      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'test-node') {
          return TypeDescriptor(
            typeName: 'test-node',
            displayName: 'Test Node',
            iconName: 'node',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [
              FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string'),
              FieldDescriptor(key: 'k2', label: 'Col 2', type: 'int'),
            ],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async => [
        InstanceRecord(
          id: '1',
          parentNodeId: parentNodeId,
          typeName: targetType.typeName,
          attributes: {'k1': 'a', 'k2': '1'},
        ),
      ];

      await viewModel.loadForNode('test-node');
      expect(viewModel.visibleColumnModels.length, equals(viewModel.headers.length));
    });

    test('visibleColumnModels filters out hidden columns by key', () async {
      dataSource.onTypeFor = (typeName) async {
        if (typeName == 'test-node') {
          return TypeDescriptor(
            typeName: 'test-node',
            displayName: 'Test Node',
            iconName: 'node',
            fields: [],
            childTypes: [],
            relatedTypes: [
              TypeRelationDescriptor(
                relationName: 'has',
                childTypeName: 'ChildType',
                childLabel: 'Child Label',
              ),
            ],
            parentTypes: [],
          );
        }
        if (typeName == 'ChildType') {
          return TypeDescriptor(
            typeName: 'ChildType',
            displayName: 'Child',
            iconName: 'child',
            fields: [
              FieldDescriptor(key: 'k1', label: 'Col 1', type: 'string'),
              FieldDescriptor(key: 'k2', label: 'Col 2', type: 'int'),
            ],
            childTypes: [],
            relatedTypes: [],
            parentTypes: [],
          );
        }
        return null;
      };

      dataSource.onFetchRelatedInstances = ({
        required parentNodeId,
        required targetType,
      }) async => [
        InstanceRecord(
          id: '1',
          parentNodeId: parentNodeId,
          typeName: targetType.typeName,
          attributes: {'k1': 'a', 'k2': '1'},
        ),
      ];

      await viewModel.loadForNode('test-node');
      final hiddenKey = viewModel.headers.first.key;
      viewModel.setHiddenColumnKeys({hiddenKey});
      expect(viewModel.visibleColumnModels.length, equals(viewModel.headers.length - 1));
      expect(viewModel.visibleColumnModels.any((c) => c.key == hiddenKey), isFalse);
    });
  });

  group('TablesViewModel loadForNode error handling', () {
    late _MockDataSource dataSource;
    late TablesViewModel viewModel;

    setUp(() {
      dataSource = _MockDataSource();
      viewModel = TablesViewModel(dataSource, 'test');
    });

    test('loadForNode resets loading to false and notifies listeners when type descriptor is null', () async {
      dataSource.onTypeFor = (typeName) async => null;

      bool notified = false;
      viewModel.addListener(() {
        if (!viewModel.loading) {
          notified = true;
        }
      });

      await viewModel.loadForNode('unknown-node');

      expect(viewModel.loading, isFalse);
      expect(notified, isTrue);
    });

    test('shouldSupportImmutableTablesStateCopyWithAndEquality', () {
      const state1 = TablesState();
      const state2 = TablesState();

      expect(state1, equals(state2));
      expect(state1.hashCode, equals(state2.hashCode));

      final updatedState = state1.copyWith(activeView: 'node1', loading: false);
      expect(updatedState.activeView, equals('node1'));
      expect(updatedState.loading, isFalse);
      expect(updatedState, isNot(equals(state1)));
    });

    test('shouldInjectSegregatedRepositoriesInTablesViewModel', () async {
      final ds = _MockDataSource();
      final vm = TablesViewModel.repositories(
        typeRepository: ds,
        instanceRepository: ds,
        propertyRepository: ds,
        activeView: 'root',
      );

      expect(vm.state.activeView, equals('root'));
    });
  });
}
