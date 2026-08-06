import 'package:app_flutter/domain/domain_errors.dart';
import 'package:app_flutter/domain/instance_record.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('InstanceRecord', () {
    test('shouldReturnSuccessWhenAllAttributesConformToConstraints', () {
      final fields = [
        const FieldDescriptor(key: 'name', label: 'Name', type: 'string', required: true),
        const FieldDescriptor(key: 'voltage', label: 'Voltage', type: 'double', minValue: 0.0, maxValue: 1000.0),
        const FieldDescriptor(key: 'status', label: 'Status', type: 'enum', enumOptions: ['Active', 'Inactive']),
      ];

      final record = InstanceRecord(
        id: 'inst-1',
        parentNodeId: 'root',
        typeName: 'TestType',
        attributes: const {
          'name': 'Power Module',
          'voltage': 240.5,
          'status': 'Active',
        },
      );

      final res = record.validate(fields);
      expect(res.isSuccess, isTrue);
    });

    test('shouldReturnFailureWhenRequiredAttributeIsMissingOrEmpty', () {
      final fields = [
        const FieldDescriptor(key: 'name', label: 'Name', type: 'string', required: true),
      ];

      final missingRecord = InstanceRecord(
        id: 'inst-1',
        parentNodeId: 'root',
        typeName: 'TestType',
        attributes: const {},
      );
      final missingRes = missingRecord.validate(fields);
      expect(missingRes.isFailure, isTrue);
      expect((missingRes as Failure<void>).error, isA<SchemaFieldRequiredError>());

      final emptyRecord = InstanceRecord(
        id: 'inst-1',
        parentNodeId: 'root',
        typeName: 'TestType',
        attributes: const {'name': '   '},
      );
      final emptyRes = emptyRecord.validate(fields);
      expect(emptyRes.isFailure, isTrue);
      expect((emptyRes as Failure<void>).error, isA<SchemaFieldRequiredError>());
    });

    test('shouldReturnFailureWhenIntegerOrDoubleOutOfBounds', () {
      final fields = [
        const FieldDescriptor(key: 'count', label: 'Count', type: 'int', minValue: 5, maxValue: 10),
      ];

      final belowRecord = InstanceRecord(
        id: 'inst-1',
        parentNodeId: 'root',
        typeName: 'TestType',
        attributes: const {'count': 4},
      );
      final belowRes = belowRecord.validate(fields);
      expect(belowRes.isFailure, isTrue);
      expect((belowRes as Failure<void>).error, isA<SchemaFieldRangeError>());
    });

    test('shouldParseInstanceRecordFromMapCorrectly', () {
      final map = {
        'id': 'inst-123',
        'parent_node_id': 'root',
        'data_json': '{"name":"Correct"}',
      };

      final record = InstanceRecord.tryParse(map, 'TestType');
      expect(record, isNotNull);
      expect(record!.id, 'inst-123');
      expect(record.attributes['name'], 'Correct');
    });

    test('shouldSupportCopyWithAndStructuralEquality', () {
      final r1 = InstanceRecord(
        id: 'inst-1',
        parentNodeId: 'root',
        typeName: 'TestType',
        attributes: const {'key': 'val'},
      );
      final r2 = InstanceRecord(
        id: 'inst-1',
        parentNodeId: 'root',
        typeName: 'TestType',
        attributes: const {'key': 'val'},
      );

      expect(r1, equals(r2));
      expect(r1.hashCode, equals(r2.hashCode));

      final r3 = r1.copyWith(typeName: 'UpdatedType');
      expect(r3.typeName, 'UpdatedType');
      expect(r3, isNot(equals(r1)));
    });
  });
}
