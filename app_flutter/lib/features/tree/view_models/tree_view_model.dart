import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/tree/tree_defaults.dart';

/// Realises: [Feat-10/TreeState]
///
/// Immutable state holder for sidebar tree view model.
@immutable
class TreeState {
  /// Member documentation.
  const TreeState({
    this.treeData = const [],
    this.currentView = '',
    this.expanded = const {},
    this.loadingNodes = const {},
    this.flightTarget,
  });

  /// Current tree nodes.
  final List<TreeNode> treeData;

  /// Currently selected view ID.
  final String currentView;

  /// Map of node expansion state.
  final Map<String, bool> expanded;

  /// Map of node loading state.
  final Map<String, bool> loadingNodes;

  /// Camera flight target node ID.
  final String? flightTarget;

  /// Creates a copy of this state with updated values.
  TreeState copyWith({
    List<TreeNode>? treeData,
    String? currentView,
    Map<String, bool>? expanded,
    Map<String, bool>? loadingNodes,
    String? flightTarget,
    bool clearFlightTarget = false,
  }) {
    return TreeState(
      treeData: treeData ?? this.treeData,
      currentView: currentView ?? this.currentView,
      expanded: expanded ?? this.expanded,
      loadingNodes: loadingNodes ?? this.loadingNodes,
      flightTarget: clearFlightTarget ? null : (flightTarget ?? this.flightTarget),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TreeState &&
          runtimeType == other.runtimeType &&
          listEquals(treeData, other.treeData) &&
          currentView == other.currentView &&
          mapEquals(expanded, other.expanded) &&
          mapEquals(loadingNodes, other.loadingNodes) &&
          flightTarget == other.flightTarget;

  @override
  int get hashCode => Object.hash(
        Object.hashAll(treeData),
        currentView,
        Object.hashAll(expanded.keys),
        Object.hashAll(expanded.values),
        flightTarget,
      );
}

/// Realises: [Feat-10/TreeViewModel]
///
/// Determines if a [node] represents a primitive leaf attribute descriptor
/// that should be filtered out from root tree navigation.
bool isPrimitiveAttribute(TreeNode node) {
  final _labelLower = node.label.toLowerCase();
  final _idLower = node.id.toLowerCase();
  const _primitives = {
    'as number', 'cartesian coordinate', 'counter 32', 'domain name',
    'ellipsoid coordinate', 'email address', 'gauge 32', 'geo location',
    'geodetic system', 'hours 32', 'ip version', 'ipv4 address',
    'ipv4 prefix', 'ipv6 address', 'mac address', 'oid', 'physical address',
    'port number', 'reference frame', 'time ticks', 'uri', 'velocity',
    'yang date time',
  };
  return _primitives.contains(_labelLower) || _primitives.contains(_idLower);
}

/// Realises: [Feat-10/TreeViewModel]
///
/// Determines if a [node] is a container entity eligible for root tree navigation.
bool isContainerEntity(TreeNode node) {
  return !isPrimitiveAttribute(node);
}

/// Realises: [Feat-10/TreeViewModel]
///
/// View model driving the sidebar tree: data loading, navigation, focus,
/// and keyboard-driven expansion/selection.
class TreeViewModel extends ChangeNotifier {
  /// Member documentation.
  TreeViewModel(this._treeRepository, {
    String initialView = '',
    this.onViewSelected,
  }) : _state = TreeState(currentView: initialView);

  final TreeRepository _treeRepository;

  /// Member documentation.
  final ValueChanged<String>? onViewSelected;

  TreeState _state;
  final FocusNode _treeFocusNode = FocusNode();
  final Map<String, GlobalKey> _nodeKeys = {};
  bool _disposed = false;

  /// Current immutable state.
  TreeState get state => _state;

  /// Member documentation.
  List<TreeNode> get treeData => _state.treeData;

  /// Member documentation.
  String get currentView => _state.currentView;

  /// Member documentation.
  Map<String, bool> get expanded => _state.expanded;

  /// Member documentation.
  Map<String, bool> get loadingNodes => _state.loadingNodes;

  /// Member documentation.
  FocusNode get focusNode => _treeFocusNode;

  /// Member documentation.
  GlobalKey? nodeKey(String id) => _nodeKeys[id];

  /// Member documentation.
  String? get flightTarget => _state.flightTarget;

  /// Loads the type hierarchy from the data source and initialises tree data,
  /// current view, expanded nodes, and node keys.
  Future<void> loadTree() async {
    final rootRes = await _treeRepository.fetchRootNodes();
    if (_disposed) return;

    final List<TreeNode> roots;
    switch (rootRes) {
      case Success<List<TreeNode>>(:final value):
        roots = value;
      case Failure<List<TreeNode>>():
        roots = <TreeNode>[];
    }

    final loadedTreeData = (roots.isNotEmpty
            ? List<TreeNode>.from(roots)
            : List<TreeNode>.from(defaultTreeData))
        .where(isContainerEntity)
        .toList();
    _sortNodesRecursively(loadedTreeData);

    _nodeKeys.clear();

    String view = _state.currentView;
    if (view.isEmpty && loadedTreeData.isNotEmpty) {
      view = loadedTreeData.first.id;
    }

    final newExpanded = <String, bool>{};
    _expandParentsPath(loadedTreeData, view, newExpanded);

    _state = _state.copyWith(
      treeData: loadedTreeData,
      currentView: view,
      expanded: newExpanded,
      loadingNodes: const {},
    );

    final currentNode = _findNodeById(loadedTreeData, view);
    if (currentNode != null && currentNode.children != null) {
      await expandNode(currentNode);
    }

    _buildNodeKeys(_state.treeData);
    notifyListeners();
  }

  /// Selects [viewId] as the current view, expands its ancestors, scrolls it
  /// into view, and notifies listeners.
  void selectView(String viewId) {
    if (_state.currentView == viewId) return;
    final newExpanded = Map<String, bool>.from(_state.expanded);
    _expandParentsPath(_state.treeData, viewId, newExpanded);

    _state = _state.copyWith(
      currentView: viewId,
      expanded: newExpanded,
    );

    final node = _findNodeById(_state.treeData, viewId);
    if (node != null && node.children != null && _state.expanded[viewId] != true) {
      expandNode(node);
    }
    _scrollToNode(viewId);
    notifyListeners();
    onViewSelected?.call(viewId);
  }

  /// Member documentation.
  void triggerFlight(String nodeId) {
    _state = _state.copyWith(flightTarget: nodeId);
    notifyListeners();
  }

  /// Member documentation.
  void clearFlightTarget() {
    _state = _state.copyWith(clearFlightTarget: true);
  }

  /// Updates the current view (without firing [selectView]'s external callback).
  void updateCurrentView(String viewId) {
    if (_state.currentView == viewId) return;
    final newExpanded = Map<String, bool>.from(_state.expanded);
    _expandParentsPath(_state.treeData, viewId, newExpanded);

    _state = _state.copyWith(
      currentView: viewId,
      expanded: newExpanded,
    );

    final node = _findNodeById(_state.treeData, viewId);
    if (node != null && node.children != null && _state.expanded[viewId] != true) {
      expandNode(node);
    }
    _scrollToNode(viewId);
    notifyListeners();
  }

  /// Toggles expansion state of the node with [id] and lazily loads children.
  void toggleExpand(String id) {
    final node = _findNodeById(_state.treeData, id);
    if (node != null) {
      expandNode(node);
    } else {
      final newExpanded = Map<String, bool>.from(_state.expanded);
      newExpanded[id] = !(newExpanded[id] ?? false);
      _state = _state.copyWith(expanded: newExpanded);
      notifyListeners();
    }
  }

  /// Recursively expands a node, loading its children if necessary.
  Future<void> expandNode(TreeNode node) async {
    if (_state.expanded[node.id] == true) {
      final newExpanded = Map<String, bool>.from(_state.expanded);
      newExpanded[node.id] = false;
      _state = _state.copyWith(expanded: newExpanded);
      notifyListeners();
      return;
    }

    if (node.children != null && node.children!.isEmpty) {
      if (_state.loadingNodes[node.id] == true) return;

      final newLoading = Map<String, bool>.from(_state.loadingNodes);
      newLoading[node.id] = true;
      _state = _state.copyWith(loadingNodes: newLoading);
      notifyListeners();

      try {
        final childRes = await _treeRepository.fetchChildrenForNode(node.id);
        if (_disposed) return;
        if (!_state.loadingNodes.containsKey(node.id)) return;

        final List<TreeNode> children;
        switch (childRes) {
          case Success<List<TreeNode>>(:final value):
            children = value;
          case Failure<List<TreeNode>>():
            children = <TreeNode>[];
        }

        _sortNodesRecursively(children);
        final newTreeData = List<TreeNode>.from(_state.treeData);
        _replaceNodeInList(newTreeData, node.id, children);
        _buildNodeKeys(children);

        final updatedLoading = Map<String, bool>.from(_state.loadingNodes)..remove(node.id);
        _state = _state.copyWith(treeData: newTreeData, loadingNodes: updatedLoading);
      } catch (e) {
        debugPrint('Error loading children: $e');
        final updatedLoading = Map<String, bool>.from(_state.loadingNodes)..remove(node.id);
        _state = _state.copyWith(loadingNodes: updatedLoading);
      }
    }

    if (_disposed) return;
    final newExpanded = Map<String, bool>.from(_state.expanded);
    newExpanded[node.id] = true;
    _state = _state.copyWith(expanded: newExpanded);
    notifyListeners();
  }

  TreeNode? _findNodeById(List<TreeNode> nodes, String id) {
    for (final node in nodes) {
      if (node.id == id) return node;
      if (node.children != null) {
        final found = _findNodeById(node.children!, id);
        if (found != null) return found;
      }
    }
    return null;
  }

  /// Moves selection to the next visible node (depth-first order).
  void handleArrowDown() {
    final visible = _getVisibleNodes();
    final currentIndex = visible.indexWhere((n) => n.id == _state.currentView);
    final nextIndex = currentIndex + 1;
    if (nextIndex < visible.length) {
      selectView(visible[nextIndex].id);
    }
  }

  /// Moves selection to the previous visible node (depth-first order).
  void handleArrowUp() {
    final visible = _getVisibleNodes();
    final currentIndex = visible.indexWhere((n) => n.id == _state.currentView);
    final prevIndex = currentIndex - 1;
    if (prevIndex >= 0) {
      selectView(visible[prevIndex].id);
    }
  }

  /// Expands the current node or, if already expanded, selects its first child.
  void handleArrowRight() {
    final visible = _getVisibleNodes();
    final currentIndex = visible.indexWhere((n) => n.id == _state.currentView);
    if (currentIndex == -1) return;
    final currentNode = visible[currentIndex];
    if (currentNode.children != null) {
      if (_state.expanded[currentNode.id] != true) {
        expandNode(currentNode);
      } else if (currentNode.children!.isNotEmpty) {
        final firstChild = currentNode.children![0];
        selectView(firstChild.id);
      }
    }
  }

  /// Collapses the current node or, if already collapsed or a leaf, selects
  /// its parent.
  void handleArrowLeft() {
    final visible = _getVisibleNodes();
    final currentIndex = visible.indexWhere((n) => n.id == _state.currentView);
    if (currentIndex == -1) return;
    final currentNode = visible[currentIndex];
    if (currentNode.children != null &&
        _state.expanded[currentNode.id] == true) {
      final newExpanded = Map<String, bool>.from(_state.expanded);
      newExpanded[currentNode.id] = false;
      _state = _state.copyWith(expanded: newExpanded);
      notifyListeners();
    } else {
      TreeNode? findParent(List<TreeNode> nodes, String targetId, TreeNode? parent) {
        for (final node in nodes) {
          if (node.id == targetId) return parent;
          if (node.children != null) {
            final found = findParent(node.children!, targetId, node);
            if (found != null) return found;
          }
        }
        return null;
      }

      final parent = findParent(_state.treeData, currentNode.id, null);
      if (parent != null) {
        selectView(parent.id);
      }
    }
  }

  @override
  void notifyListeners() {
    if (_disposed) return;
    super.notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _treeFocusNode.dispose();
    super.dispose();
  }

  void _buildNodeKeys(List<TreeNode> nodes) {
    for (final node in nodes) {
      _nodeKeys[node.id] = GlobalKey();
      if (node.children != null) {
        _buildNodeKeys(node.children!);
      }
    }
  }

  void _expandParentsPath(List<TreeNode> nodes, String targetId, Map<String, bool> expandedMap) {
    bool findAndExpand(List<TreeNode> currentNodes, String id, List<String> path) {
      for (final node in currentNodes) {
        if (node.id == id) {
          for (final ancestorId in path) {
            expandedMap[ancestorId] = true;
          }
          return true;
        }
        if (node.children != null) {
          if (findAndExpand(node.children!, id, [...path, node.id])) {
            return true;
          }
        }
      }
      return false;
    }
    findAndExpand(nodes, targetId, []);
  }

  List<TreeNode> _getVisibleNodes() {
    final List<TreeNode> result = [];
    void traverse(TreeNode node) {
      result.add(node);
      if (node.children != null && _state.expanded[node.id] == true) {
        node.children!.forEach(traverse);
      }
    }
    _state.treeData.forEach(traverse);
    return result;
  }

  void _scrollToNode(String viewId) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final context = _nodeKeys[viewId]?.currentContext;
      if (context != null) {
        Scrollable.ensureVisible(
          context,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
        );
      }
    });
  }

  void _sortNodesRecursively(List<TreeNode> nodes) {
    nodes.sort((a, b) => _naturalCompare(a.id, b.id));
    for (final node in nodes) {
      if (node.children != null && node.children!.isNotEmpty) {
        _sortNodesRecursively(node.children!);
      }
    }
  }

  bool _replaceNodeInList(List<TreeNode> nodes, String targetId, List<TreeNode> newChildren) {
    for (int i = 0; i < nodes.length; i++) {
      if (nodes[i].id == targetId) {
        nodes[i] = nodes[i].copyWith(children: newChildren);
        return true;
      }
      if (nodes[i].children != null) {
        if (_replaceNodeInList(nodes[i].children!, targetId, newChildren)) return true;
      }
    }
    return false;
  }

  int _naturalCompare(String a, String b) {
    final bool isChildOrGcA = a.contains('_Child_') || a.contains('_Grandchild_');
    final bool isChildOrGcB = b.contains('_Child_') || b.contains('_Grandchild_');
    
    if (isChildOrGcA != isChildOrGcB) {
      return isChildOrGcA ? 1 : -1;
    }

    final RegExp regExp = RegExp(r'(\d+)|(\D+)');
    final Iterable<Match> matchesA = regExp.allMatches(a);
    final Iterable<Match> matchesB = regExp.allMatches(b);
    
    final List<String> chunksA = matchesA.map((m) => m.group(0)!).toList();
    final List<String> chunksB = matchesB.map((m) => m.group(0)!).toList();
    
    final int minLen = chunksA.length < chunksB.length ? chunksA.length : chunksB.length;
    for (int i = 0; i < minLen; i++) {
      final String chunkA = chunksA[i];
      final String chunkB = chunksB[i];
      
      final bool isDigitA = RegExp(r'^\d+$').hasMatch(chunkA);
      final bool isDigitB = RegExp(r'^\d+$').hasMatch(chunkB);
      
      if (isDigitA && isDigitB) {
        final int valA = int.parse(chunkA);
        final int valB = int.parse(chunkB);
        final int cmp = valA.compareTo(valB);
        if (cmp != 0) return cmp;
      } else {
        final int cmp = chunkA.compareTo(chunkB);
        if (cmp != 0) return cmp;
      }
    }
    return chunksA.length.compareTo(chunksB.length);
  }
}
