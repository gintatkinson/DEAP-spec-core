import 'package:app_flutter/domain/domain_errors.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Result<T>', () {
    test('shouldReturnWrappedValueWhenResultIsSuccess', () {
      const Result<int> result = Success<int>(42);

      expect(result.isSuccess, isTrue);
      expect(result.isFailure, isFalse);
      if (result is Success<int>) {
        expect(result.value, equals(42));
      } else {
        fail('Expected Success instance');
      }
    });

    test('shouldReturnDomainErrorWhenResultIsFailure', () {
      const error = SchemaFieldRequiredError(
        fieldName: 'id',
        schemaName: 'User',
      );
      const Result<int> result = Failure<int>(error);

      expect(result.isSuccess, isFalse);
      expect(result.isFailure, isTrue);
      if (result is Failure<int>) {
        expect(result.error, equals(error));
        expect(result.error, isA<SchemaFieldRequiredError>());
      } else {
        fail('Expected Failure instance');
      }
    });

    test('shouldMatchExhaustivelyWhenUsingSwitchExpression', () {
      const Result<String> success = Success<String>('hello');
      const Result<String> failure = Failure<String>(
        SerializationError(targetType: 'String', reason: 'Invalid bytes'),
      );

      String evaluate(Result<String> res) {
        return switch (res) {
          Success<String>(:final value) => 'Success: $value',
          Failure<String>(:final error) => 'Failure: ${error.runtimeType}',
        };
      }

      expect(evaluate(success), equals('Success: hello'));
      expect(evaluate(failure), equals('Failure: SerializationError'));
    });
  });
}
