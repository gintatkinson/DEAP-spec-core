import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/domain/validation.dart';

/// Realises: [Feat-10/InstanceRecord]
///
/// Represents an instance record of a specific type.
@immutable
class InstanceRecord {
  /// Unique identifier of the instance.
  final String id;

  /// Identifier of the parent node.
  final String parentNodeId;

  /// The name of the type of this instance.
  final String typeName;

  /// Attributes of the instance represented as key-value pairs.
  final Map<String, dynamic> attributes;

  /// Creates a new [InstanceRecord] instance.
  const InstanceRecord({
    required this.id,
    required this.parentNodeId,
    required this.typeName,
    required this.attributes,
  });

  /// Creates an [InstanceRecord] from a raw map database entry.
  factory InstanceRecord.fromMap(Map<String, dynamic> map, String typeName) {
    Map<String, dynamic> attrs = {};
    if (map['data_json'] != null) {
      try {
        final decoded = jsonDecode(map['data_json'] as String);
        if (decoded is Map<String, dynamic>) {
          attrs = decoded;
        }
      } catch (_) {}
    } else {
      attrs = Map<String, dynamic>.from(map);
    }
    return InstanceRecord(
      id: map['id']?.toString() ?? attrs['id']?.toString() ?? '',
      parentNodeId: map['parent_node_id']?.toString() ?? attrs['parent_node_id']?.toString() ?? '',
      typeName: map['type_name']?.toString() ?? typeName,
      attributes: attrs,
    );
  }

  /// Attempts to parse an [InstanceRecord] from a raw map database entry.
  ///
  /// Returns `null` if parsing fails.
  static InstanceRecord? tryParse(Map<String, dynamic> map, String typeName) {
    try {
      return InstanceRecord.fromMap(map, typeName);
    } catch (_) {
      return null;
    }
  }

  /// Validates all attributes against the provided [fields] descriptors constraints.
  ///
  /// Returns [Result.success] if valid, or [Result.failure] with a [DomainError] on failure.
  Result<void> validate(List<FieldDescriptor> fields) {
    return validateFields(attributes, fields);
  }

  /// Creates a copy of this [InstanceRecord] with the given fields replaced.
  InstanceRecord copyWith({
    String? id,
    String? parentNodeId,
    String? typeName,
    Map<String, dynamic>? attributes,
  }) {
    return InstanceRecord(
      id: id ?? this.id,
      parentNodeId: parentNodeId ?? this.parentNodeId,
      typeName: typeName ?? this.typeName,
      attributes: attributes ?? this.attributes,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is InstanceRecord &&
        other.id == id &&
        other.parentNodeId == parentNodeId &&
        other.typeName == typeName &&
        mapEquals(other.attributes, attributes);
  }

  @override
  int get hashCode {
    return Object.hash(
      id,
      parentNodeId,
      typeName,
      Object.hashAll(attributes.keys),
      Object.hashAll(attributes.values),
    );
  }
}
