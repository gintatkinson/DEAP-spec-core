/// A node in the sidebar hierarchy tree representing a selectable view type.
///
/// Each node carries an [id] (unique view identifier), a human-readable
/// [label], and optional [children] for nested sub-types. Leaf nodes have
/// `null` children. The tree structure mirrors the type hierarchy discovered
/// from the data source. Equality is identity-based; no value equality override
/// is provided since nodes are rebuilt on each tree refresh.
///
/// Represents a node in the inventory tree structure.
/// Realises: [Feat-10/TreeNode]
class TreeNode {
  /// Member documentation.
  final String id;
  /// Member documentation.
  final String label;
  /// Member documentation.
  final List<TreeNode>? children;

  /// Member documentation.
  const TreeNode({
    required this.id,
    required this.label,
    this.children,
  });

  /// Member documentation.
  TreeNode copyWith({
    String? id,
    String? label,
    List<TreeNode>? children,
  }) {
    return TreeNode(
      id: id ?? this.id,
      label: label ?? this.label,
      children: children ?? this.children,
    );
  }
}
