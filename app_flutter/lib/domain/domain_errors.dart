import 'package:flutter/foundation.dart';

/// Realises: [Feat-10/DomainError]
///
/// Sealed base class representing domain-level errors with structured context.
@immutable
sealed class DomainError {
  /// Abstract const constructor for [DomainError].
  const DomainError();
}

/// Realises: [Feat-10/DomainError]
/// Error raised when a mandatory schema field is missing.
@immutable
final class SchemaFieldRequiredError extends DomainError {
  /// Creates a [SchemaFieldRequiredError] for [fieldName] in [schemaName].
  const SchemaFieldRequiredError({
    required this.fieldName,
    required this.schemaName,
  });

  /// The name of the required field.
  final String fieldName;

  /// The name or identifier of the target schema.
  final String schemaName;
}

/// Realises: [Feat-10/DomainError]
/// Error raised when a schema field value has an unexpected type.
@immutable
final class SchemaFieldTypeError extends DomainError {
  /// Creates a [SchemaFieldTypeError].
  const SchemaFieldTypeError({
    required this.fieldName,
    required this.expectedType,
    required this.actualType,
  });

  /// The name of the field with invalid type.
  final String fieldName;

  /// The expected type identifier or name.
  final String expectedType;

  /// The actual type received or encountered.
  final String actualType;
}

/// Realises: [Feat-10/DomainError]
/// Error raised when a schema field value falls outside allowed numeric ranges.
@immutable
final class SchemaFieldRangeError extends DomainError {
  /// Creates a [SchemaFieldRangeError].
  const SchemaFieldRangeError({
    required this.fieldName,
    required this.value,
    this.min,
    this.max,
  });

  /// The name of the out-of-range field.
  final String fieldName;

  /// The value that violated the range constraint.
  final num value;

  /// The minimum allowable value, if bounded below.
  final num? min;

  /// The maximum allowable value, if bounded above.
  final num? max;
}

/// Realises: [Feat-10/DomainError]
/// Error raised when a schema field value fails string regex pattern validation.
@immutable
final class SchemaFieldPatternError extends DomainError {
  /// Creates a [SchemaFieldPatternError].
  const SchemaFieldPatternError({
    required this.fieldName,
    required this.value,
    required this.pattern,
  });

  /// The name of the field failing pattern match.
  final String fieldName;

  /// The string value that failed regex matching.
  final String value;

  /// The regex pattern string that was evaluated against.
  final String pattern;
}

/// Realises: [Feat-10/DomainError]
/// Error raised when a schema field value is not among allowed enum values.
@immutable
final class SchemaFieldEnumError extends DomainError {
  /// Creates a [SchemaFieldEnumError].
  const SchemaFieldEnumError({
    required this.fieldName,
    required this.value,
    required this.allowedValues,
  });

  /// The name of the enum field.
  final String fieldName;

  /// The actual invalid enum value provided.
  final String value;

  /// The list of valid permitted enum string representations.
  final List<String> allowedValues;
}

/// Realises: [Feat-10/DomainError]
/// Error raised when serialization or deserialization fails.
@immutable
final class SerializationError extends DomainError {
  /// Creates a [SerializationError].
  const SerializationError({
    required this.targetType,
    required this.reason,
    this.payload,
  });

  /// The target type attempted during serialization/deserialization.
  final String targetType;

  /// The structured rationale or cause description.
  final String reason;

  /// Optional raw payload data associated with the failure.
  final Object? payload;
}
