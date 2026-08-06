import 'package:app_flutter/domain/domain_errors.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';

/// Realises: [Feat-10/Validation]
///
/// Generic validation function that evaluates constraints on a map of input values
/// against a list of [FieldDescriptor] descriptors.
///
/// Returns [Result.success] when all inputs satisfy their constraints.
/// Returns [Result.failure] carrying a typed [DomainError] on the first constraint failure.
Result<void> validateFields(Map<String, dynamic> input, List<FieldDescriptor> descriptors) {
  for (final fd in descriptors) {
    final value = input[fd.key];

    // If missing/empty, check required constraint. Otherwise skip validation if not required.
    if (value == null || (value is String && value.trim().isEmpty)) {
      if (fd.required) {
        return Result.failure(SchemaFieldRequiredError(
          fieldName: fd.key,
          schemaName: fd.key,
        ));
      }
      continue;
    }

    final strVal = value.toString();
    if (fd.type == 'int') {
      final parsed = int.tryParse(strVal);
      if (parsed == null) {
        return Result.failure(SchemaFieldTypeError(
          fieldName: fd.key,
          expectedType: 'int',
          actualType: value.runtimeType.toString(),
        ));
      }
      if (fd.minValue != null && parsed < fd.minValue!) {
        return Result.failure(SchemaFieldRangeError(
          fieldName: fd.key,
          value: parsed,
          min: fd.minValue,
          max: fd.maxValue,
        ));
      }
      if (fd.maxValue != null && parsed > fd.maxValue!) {
        return Result.failure(SchemaFieldRangeError(
          fieldName: fd.key,
          value: parsed,
          min: fd.minValue,
          max: fd.maxValue,
        ));
      }
    } else if (fd.type == 'double' || fd.type == 'real') {
      final parsed = double.tryParse(strVal);
      if (parsed == null) {
        return Result.failure(SchemaFieldTypeError(
          fieldName: fd.key,
          expectedType: fd.type,
          actualType: value.runtimeType.toString(),
        ));
      }
      if (fd.minValue != null && parsed < fd.minValue!) {
        return Result.failure(SchemaFieldRangeError(
          fieldName: fd.key,
          value: parsed,
          min: fd.minValue,
          max: fd.maxValue,
        ));
      }
      if (fd.maxValue != null && parsed > fd.maxValue!) {
        return Result.failure(SchemaFieldRangeError(
          fieldName: fd.key,
          value: parsed,
          min: fd.minValue,
          max: fd.maxValue,
        ));
      }
    } else if (fd.type == 'string') {
      if (fd.pattern != null && fd.pattern!.isNotEmpty) {
        final regex = fd.compiledPattern ?? RegExp(fd.pattern!);
        if (!regex.hasMatch(strVal)) {
          return Result.failure(SchemaFieldPatternError(
            fieldName: fd.key,
            value: strVal,
            pattern: fd.pattern!,
          ));
        }
      }
    } else if (fd.type == 'enum') {
      if (fd.enumOptions != null && !fd.enumOptions!.contains(strVal)) {
        return Result.failure(SchemaFieldEnumError(
          fieldName: fd.key,
          value: strVal,
          allowedValues: fd.enumOptions!,
        ));
      }
    }
  }
  return const Result.success(null);
}
