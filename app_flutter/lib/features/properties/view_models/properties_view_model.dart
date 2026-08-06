import 'package:flutter/foundation.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';

/// Realises: [Feat-10/PropertiesState]
/// Realises: [UC-03]
/// Realises: [UC-10]
/// Realises: [UC-15]
///
/// Immutable state holder for property panel data and operational use case actions.
@immutable
class PropertiesState {
  /// Creates a [PropertiesState].
  const PropertiesState({
    this.currentType,
    this.lastAction,
    this.actionMessage,
    this.activeNodeId,
  });

  /// The currently loaded [TypeDescriptor], or null.
  final TypeDescriptor? currentType;

  /// The identifier of the last executed operational action.
  final String? lastAction;

  /// Human-readable message associated with the last operational action.
  final String? actionMessage;

  /// Target node ID for the last operational action.
  final String? activeNodeId;

  /// Creates a copy of this state with updated fields.
  PropertiesState copyWith({
    TypeDescriptor? currentType,
    bool clearCurrentType = false,
    String? lastAction,
    bool clearLastAction = false,
    String? actionMessage,
    bool clearActionMessage = false,
    String? activeNodeId,
    bool clearActiveNodeId = false,
  }) {
    return PropertiesState(
      currentType: clearCurrentType ? null : (currentType ?? this.currentType),
      lastAction: clearLastAction ? null : (lastAction ?? this.lastAction),
      actionMessage: clearActionMessage ? null : (actionMessage ?? this.actionMessage),
      activeNodeId: clearActiveNodeId ? null : (activeNodeId ?? this.activeNodeId),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PropertiesState &&
          runtimeType == other.runtimeType &&
          currentType == other.currentType &&
          lastAction == other.lastAction &&
          actionMessage == other.actionMessage &&
          activeNodeId == other.activeNodeId;

  @override
  int get hashCode => Object.hash(currentType, lastAction, actionMessage, activeNodeId);
}

/// Realises: [Feat-10/PropertiesViewModel]
/// Realises: [UC-03]
/// Realises: [UC-10]
/// Realises: [UC-15]
///
/// Loads a [TypeDescriptor] from the data source and exposes its fields to the
/// property grid widget.
///
/// Exists to decouple the property grid from the data-fetching logic. Use this
/// view model whenever the property panel needs to display a node's fields or
/// dispatch operational use case actions.
class PropertiesViewModel extends ChangeNotifier {
  /// Creates a [PropertiesViewModel] with injected [TypeRepository].
  PropertiesViewModel(this._typeRepository);

  final TypeRepository _typeRepository;
  PropertiesState _state = const PropertiesState();
  bool _disposed = false;
  int _requestId = 0;

  /// Current immutable state.
  PropertiesState get state => _state;

  /// The fields of the currently loaded type. Returns an empty list when no
  /// type has been loaded or `loadType` returned `null`.
  List<FieldDescriptor> get fields => _state.currentType?.fields ?? [];

  /// Whether a type has been loaded (i.e., [loadType] completed with a
  /// non-null [TypeDescriptor]).
  bool get hasType => _state.currentType != null;

  /// Fetches the [TypeDescriptor] for [typeName] from the data source and
  /// notifies listeners.
  ///
  /// If the data source returns `null` (unknown type), [_state] is updated with
  /// null type, [fields] becomes empty, and [hasType] becomes false.
  Future<void> loadType(String typeName) async {
    final requestId = ++_requestId;
    final res = await _typeRepository.typeFor(typeName);
    if (_disposed) return;
    if (_requestId != requestId) return;

    switch (res) {
      case Success<TypeDescriptor?>(:final value):
        _state = _state.copyWith(currentType: value, clearCurrentType: value == null);
      case Failure<TypeDescriptor?>():
        _state = _state.copyWith(clearCurrentType: true);
    }
    notifyListeners();
  }

  /// Realises: [UC-03]
  ///
  /// Dispatches the Configure Location operational action for [nodeId].
  void configureLocation(String nodeId) {
    _state = _state.copyWith(
      lastAction: 'configureLocation',
      actionMessage: 'Location configured for node $nodeId',
      activeNodeId: nodeId,
    );
    notifyListeners();
  }

  /// Realises: [UC-10]
  ///
  /// Dispatches the Drill Hierarchy operational action for [nodeId].
  void drillHierarchy(String nodeId) {
    _state = _state.copyWith(
      lastAction: 'drillHierarchy',
      actionMessage: 'Hierarchy drilled for node $nodeId',
      activeNodeId: nodeId,
    );
    notifyListeners();
  }

  /// Realises: [UC-15]
  ///
  /// Dispatches the Provision NE operational action for [nodeId].
  void provisionNe(String nodeId) {
    _state = _state.copyWith(
      lastAction: 'provisionNe',
      actionMessage: 'NE provisioned for node $nodeId',
      activeNodeId: nodeId,
    );
    notifyListeners();
  }

  @override
  void notifyListeners() {
    if (_disposed) return;
    super.notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
