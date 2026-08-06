import 'package:app_flutter/domain/domain_errors.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DomainError Hierarchy', () {
    test('shouldStoreStructuredContextWhenSchemaFieldRequiredErrorInstantiated', () {
      const error = SchemaFieldRequiredError(
        fieldName: 'title',
        schemaName: 'Document',
      );

      expect(error.fieldName, equals('title'));
      expect(error.schemaName, equals('Document'));
      expect(error, isA<DomainError>());
    });

    test('shouldStoreStructuredContextWhenSchemaFieldTypeErrorInstantiated', () {
      const error = SchemaFieldTypeError(
        fieldName: 'age',
        expectedType: 'int',
        actualType: 'String',
      );

      expect(error.fieldName, equals('age'));
      expect(error.expectedType, equals('int'));
      expect(error.actualType, equals('String'));
      expect(error, isA<DomainError>());
    });

    test('shouldStoreStructuredContextWhenSchemaFieldRangeErrorInstantiated', () {
      const error = SchemaFieldRangeError(
        fieldName: 'score',
        value: 105,
        min: 0,
        max: 100,
      );

      expect(error.fieldName, equals('score'));
      expect(error.value, equals(105));
      expect(error.min, equals(0));
      expect(error.max, equals(100));
      expect(error, isA<DomainError>());
    });

    test('shouldStoreStructuredContextWhenSchemaFieldPatternErrorInstantiated', () {
      const error = SchemaFieldPatternError(
        fieldName: 'email',
        value: 'invalid-email',
        pattern: r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$',
      );

      expect(error.fieldName, equals('email'));
      expect(error.value, equals('invalid-email'));
      expect(error.pattern, equals(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$'));
      expect(error, isA<DomainError>());
    });

    test('shouldStoreStructuredContextWhenSchemaFieldEnumErrorInstantiated', () {
      const error = SchemaFieldEnumError(
        fieldName: 'status',
        value: 'UNKNOWN',
        allowedValues: ['ACTIVE', 'INACTIVE', 'PENDING'],
      );

      expect(error.fieldName, equals('status'));
      expect(error.value, equals('UNKNOWN'));
      expect(error.allowedValues, equals(['ACTIVE', 'INACTIVE', 'PENDING']));
      expect(error, isA<DomainError>());
    });

    test('shouldStoreStructuredContextWhenSerializationErrorInstantiated', () {
      const payload = {'raw': 123};
      const error = SerializationError(
        targetType: 'InstanceRecord',
        reason: 'Malformed JSON key',
        payload: payload,
      );

      expect(error.targetType, equals('InstanceRecord'));
      expect(error.reason, equals('Malformed JSON key'));
      expect(error.payload, equals(payload));
      expect(error, isA<DomainError>());
    });

    test('shouldSupportExhaustivePatternMatchingWhenEvaluatingDomainError', () {
      final List<DomainError> errors = [
        const SchemaFieldRequiredError(fieldName: 'f', schemaName: 's'),
        const SchemaFieldTypeError(fieldName: 'f', expectedType: 'int', actualType: 'String'),
        const SchemaFieldRangeError(fieldName: 'f', value: 10),
        const SchemaFieldPatternError(fieldName: 'f', value: 'v', pattern: 'p'),
        const SchemaFieldEnumError(fieldName: 'f', value: 'e', allowedValues: ['e']),
        const SerializationError(targetType: 't', reason: 'r'),
      ];

      for (final err in errors) {
        final description = switch (err) {
          SchemaFieldRequiredError(:final fieldName, :final schemaName) =>
            'Required: $fieldName in $schemaName',
          SchemaFieldTypeError(:final fieldName, :final expectedType, :final actualType) =>
            'Type: $fieldName ($expectedType != $actualType)',
          SchemaFieldRangeError(:final fieldName, :final value) =>
            'Range: $fieldName = $value',
          SchemaFieldPatternError(:final fieldName, :final value, :final pattern) =>
            'Pattern: $fieldName ($value !~ $pattern)',
          SchemaFieldEnumError(:final fieldName, :final value, :final allowedValues) =>
            'Enum: $fieldName ($value not in $allowedValues)',
          SerializationError(:final targetType, :final reason) =>
            'Serialization: $targetType ($reason)',
        };

        expect(description, isNotEmpty);
      }
    });
  });
}
