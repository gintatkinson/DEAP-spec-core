import 'package:app_flutter/domain/domain_errors.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/validation.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('validateFields', () {
    test('shouldReturnSuccessWhenRequiredFieldIsProvided', () {
      final desc = <FieldDescriptor>[
        const FieldDescriptor(key: 'name', label: 'Name', type: 'string', required: true),
      ];
      final successRes = validateFields({'name': 'John'}, desc);
      expect(successRes.isSuccess, isTrue);

      final emptyRes = validateFields({'name': ''}, desc);
      expect(emptyRes.isFailure, isTrue);
      expect((emptyRes as Failure<void>).error, isA<SchemaFieldRequiredError>());

      final missingRes = validateFields({}, desc);
      expect(missingRes.isFailure, isTrue);
      expect((missingRes as Failure<void>).error, isA<SchemaFieldRequiredError>());
    });

    test('shouldReturnSuccessWhenOptionalFieldIsEmpty', () {
      final desc = <FieldDescriptor>[
        const FieldDescriptor(key: 'name', label: 'Name', type: 'string', required: false, pattern: r'^[A-Z]{3}$'),
      ];
      expect(validateFields({}, desc).isSuccess, isTrue);
      expect(validateFields({'name': ''}, desc).isSuccess, isTrue);
      expect(validateFields({'name': 'ABC'}, desc).isSuccess, isTrue);
      
      final patternRes = validateFields({'name': 'ab'}, desc);
      expect(patternRes.isFailure, isTrue);
      expect((patternRes as Failure<void>).error, isA<SchemaFieldPatternError>());
    });

    test('shouldReturnSuccessWhenIntegerWithinRangeAndFailureOtherwise', () {
      final desc = <FieldDescriptor>[
        const FieldDescriptor(key: 'age', label: 'Age', type: 'int', required: true, minValue: 18, maxValue: 99),
      ];
      expect(validateFields({'age': 20}, desc).isSuccess, isTrue);
      expect(validateFields({'age': '20'}, desc).isSuccess, isTrue);

      final belowMinRes = validateFields({'age': 17}, desc);
      expect(belowMinRes.isFailure, isTrue);
      expect((belowMinRes as Failure<void>).error, isA<SchemaFieldRangeError>());

      final aboveMaxRes = validateFields({'age': 100}, desc);
      expect(aboveMaxRes.isFailure, isTrue);
      expect((aboveMaxRes as Failure<void>).error, isA<SchemaFieldRangeError>());

      final typeRes = validateFields({'age': 'not_an_int'}, desc);
      expect(typeRes.isFailure, isTrue);
      expect((typeRes as Failure<void>).error, isA<SchemaFieldTypeError>());
    });

    test('shouldReturnSuccessWhenDoubleWithinRangeAndFailureOtherwise', () {
      final desc = <FieldDescriptor>[
        const FieldDescriptor(key: 'score', label: 'Score', type: 'double', required: true, minValue: 1.5, maxValue: 5.0),
      ];
      expect(validateFields({'score': 3.14}, desc).isSuccess, isTrue);
      expect(validateFields({'score': '3.14'}, desc).isSuccess, isTrue);

      final belowMinRes = validateFields({'score': 1.4}, desc);
      expect(belowMinRes.isFailure, isTrue);
      expect((belowMinRes as Failure<void>).error, isA<SchemaFieldRangeError>());

      final aboveMaxRes = validateFields({'score': 5.1}, desc);
      expect(aboveMaxRes.isFailure, isTrue);
      expect((aboveMaxRes as Failure<void>).error, isA<SchemaFieldRangeError>());

      final typeRes = validateFields({'score': 'invalid'}, desc);
      expect(typeRes.isFailure, isTrue);
      expect((typeRes as Failure<void>).error, isA<SchemaFieldTypeError>());
    });

    test('shouldReturnSuccessWhenPatternMatchesAndFailureOtherwise', () {
      final desc = <FieldDescriptor>[
        const FieldDescriptor(key: 'code', label: 'Code', type: 'string', required: true, pattern: r'^[A-Z]{2}$'),
      ];
      expect(validateFields({'code': 'FI'}, desc).isSuccess, isTrue);
      expect(validateFields({'code': 'US'}, desc).isSuccess, isTrue);

      final lowerRes = validateFields({'code': 'us'}, desc);
      expect(lowerRes.isFailure, isTrue);
      expect((lowerRes as Failure<void>).error, isA<SchemaFieldPatternError>());

      final lenRes = validateFields({'code': 'USA'}, desc);
      expect(lenRes.isFailure, isTrue);
      expect((lenRes as Failure<void>).error, isA<SchemaFieldPatternError>());
    });

    test('shouldReturnSuccessWhenEnumOptionIsValidAndFailureOtherwise', () {
      final desc = <FieldDescriptor>[
        const FieldDescriptor(
          key: 'status',
          label: 'Status',
          type: 'enum',
          required: true,
          enumOptions: ['ACTIVE', 'INACTIVE'],
        ),
      ];
      expect(validateFields({'status': 'ACTIVE'}, desc).isSuccess, isTrue);
      expect(validateFields({'status': 'INACTIVE'}, desc).isSuccess, isTrue);

      final invalidRes = validateFields({'status': 'PENDING'}, desc);
      expect(invalidRes.isFailure, isTrue);
      expect((invalidRes as Failure<void>).error, isA<SchemaFieldEnumError>());
    });
  });
}
