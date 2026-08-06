import 'package:app_flutter/domain/type_descriptor.dart';

/// Represents a column definition in table views.
///
/// Realises: [Feat-10/ColumnModel]
class ColumnModel {
  /// Unique key matching the schema field identifier.
  final String key;
  /// Human-readable column header label.
  final String label;
  /// Data type string (e.g. "string", "int", "double", "enum", "date").
  final String type;
  /// Column display width in pixels, or null for default sizing.
  final double? width;
  /// Whether the column can be sorted by clicking the header.
  final bool sortable;
  /// Whether the column is frozen to the left side of the table.
  final bool frozen;
  /// Whether the column is visible in the table.
  final bool visible;

  /// Creates a [ColumnModel] instance.
  const ColumnModel({
    required this.key,
    required this.label,
    required this.type,
    this.width,
    this.sortable = true,
    this.frozen = false,
    this.visible = true,
  });

  /// Creates a [ColumnModel] from a [FieldDescriptor].
  ///
  /// Derives column header label dynamically from [fd.key] if [fd.label] is
  /// empty or starts with fallback patterns like "Field ".
  factory ColumnModel.fromFieldDescriptor(FieldDescriptor fd) {
    return ColumnModel(
      key: fd.key,
      label: resolveColumnLabel(fd),
      type: fd.type,
    );
  }

  /// Derives column header label dynamically from [fd.key] if [fd.label] is
  /// empty or starts with fallback patterns like "Field ".
  static String resolveColumnLabel(FieldDescriptor fd) {
    final labelStr = fd.label.trim();
    if (labelStr.isEmpty || labelStr.startsWith('Field ')) {
      return deriveLabelFromKey(fd.key);
    }
    return fd.label;
  }

  /// Formats a schema key into a human-readable title/label.
  static String deriveLabelFromKey(String key) {
    final trimmed = key.trim();
    if (trimmed.isEmpty) return trimmed;

    if (trimmed.contains('_')) {
      final parts = trimmed.split('_').where((p) => p.isNotEmpty);
      return parts
          .map((p) => p[0].toUpperCase() + p.substring(1))
          .join(' ');
    }

    final exp = RegExp(r'(?<=[a-z0-9])(?=[A-Z])');
    final words = trimmed.split(exp);
    return words
        .map((w) => w.isNotEmpty ? (w[0].toUpperCase() + w.substring(1)) : '')
        .join(' ');
  }

  @override
  bool operator ==(Object other) =>
      other is ColumnModel &&
      other.key == key &&
      other.label == label &&
      other.type == type &&
      other.width == width &&
      other.sortable == sortable &&
      other.frozen == frozen &&
      other.visible == visible;

  @override
  int get hashCode => Object.hash(key, label, type, width, sortable, frozen, visible);
}
