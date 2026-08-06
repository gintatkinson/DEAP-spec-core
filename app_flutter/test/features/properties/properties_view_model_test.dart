import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/domain_errors.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/features/properties/view_models/properties_view_model.dart';

class _MockTypeRepository implements TypeRepository {
  TypeDescriptor? mockDescriptor;
  bool returnError = false;

  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async {
    return const Result.success([]);
  }

  @override
  Future<Result<TypeDescriptor?>> typeFor(String typeName) async {
    if (returnError) {
      return const Result.failure(SchemaFieldRequiredError(fieldName: 'type', schemaName: 'test'));
    }
    return Result.success(mockDescriptor);
  }

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async {
    return const Result.success([]);
  }
}

void main() {
  group('PropertiesViewModel BDD Unit Tests', () {
    late _MockTypeRepository mockRepo;
    late PropertiesViewModel viewModel;

    setUp(() {
      mockRepo = _MockTypeRepository();
      viewModel = PropertiesViewModel(mockRepo);
    });

    test('shouldReturnEmptyFieldsWhenNoTypeLoaded', () {
      expect(viewModel.fields, isEmpty);
      expect(viewModel.hasType, isFalse);
    });

    test('shouldUpdateStateOnTypeLoadSuccess', () async {
      mockRepo.mockDescriptor = const TypeDescriptor(
        typeName: 'TestNode',
        displayName: 'Test Node',
        iconName: 'node',
        fields: [
          FieldDescriptor(key: 'p1', label: 'Prop 1', type: 'string'),
        ],
        childTypes: [],
        relatedTypes: [],
        parentTypes: [],
      );

      await viewModel.loadType('TestNode');

      expect(viewModel.hasType, isTrue);
      expect(viewModel.fields.length, 1);
      expect(viewModel.fields.first.key, 'p1');
    });

    test('shouldReturnEmptyFieldsOnTypeLoadFailure', () async {
      mockRepo.returnError = true;

      await viewModel.loadType('UnknownNode');

      expect(viewModel.hasType, isFalse);
      expect(viewModel.fields, isEmpty);
    });

    test('shouldSupportImmutableStateCopyWithAndEquality', () {
      const state1 = PropertiesState();
      const state2 = PropertiesState();

      expect(state1, equals(state2));
      expect(state1.hashCode, equals(state2.hashCode));

      const desc = TypeDescriptor(
        typeName: 'NodeA',
        displayName: 'Node A',
        iconName: 'node',
        fields: [],
        childTypes: [],
        relatedTypes: [],
        parentTypes: [],
      );
      final updatedState = state1.copyWith(currentType: desc);

      expect(updatedState.currentType, equals(desc));
      expect(updatedState, isNot(equals(state1)));
    });

    test('shouldUpdateStateOnConfigureLocationAction', () {
      bool listenerCalled = false;
      viewModel.addListener(() {
        listenerCalled = true;
      });

      viewModel.configureLocation('node-123');

      expect(listenerCalled, isTrue);
      expect(viewModel.state.lastAction, equals('configureLocation'));
      expect(viewModel.state.activeNodeId, equals('node-123'));
      expect(viewModel.state.actionMessage, contains('Location configured'));
    });

    test('shouldUpdateStateOnDrillHierarchyAction', () {
      bool listenerCalled = false;
      viewModel.addListener(() {
        listenerCalled = true;
      });

      viewModel.drillHierarchy('node-456');

      expect(listenerCalled, isTrue);
      expect(viewModel.state.lastAction, equals('drillHierarchy'));
      expect(viewModel.state.activeNodeId, equals('node-456'));
      expect(viewModel.state.actionMessage, contains('Hierarchy drilled'));
    });

    test('shouldUpdateStateOnProvisionNeAction', () {
      bool listenerCalled = false;
      viewModel.addListener(() {
        listenerCalled = true;
      });

      viewModel.provisionNe('node-789');

      expect(listenerCalled, isTrue);
      expect(viewModel.state.lastAction, equals('provisionNe'));
      expect(viewModel.state.activeNodeId, equals('node-789'));
      expect(viewModel.state.actionMessage, contains('NE provisioned'));
    });
  });
}
