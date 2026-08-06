import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/features/properties/property_grid.dart';
import 'package:app_flutter/features/properties/view_models/properties_view_model.dart';

/// Realises: [Feat-10/PropertiesPanel]
/// Realises: [UC-03]
/// Realises: [UC-10]
/// Realises: [UC-15]
///
/// Workspace panel widget that wraps [PropertyGrid] and renders an Operational
/// Use Case Action Bar toolbar.
///
/// Exists to allow operators to trigger high-level operational actions
/// (`Configure Location`, `Drill Hierarchy`, `Provision NE`) directly from the
/// properties panel while viewing or editing property fields.
@immutable
class PropertiesPanel extends StatelessWidget {
  /// Creates a [PropertiesPanel].
  const PropertiesPanel({
    super.key,
    this.child,
    this.fields = const [],
    this.initialValues = const {},
    this.activeView = 'root',
    this.currentNodeId,
    this.onSave,
    this.onConfigureLocation,
    this.onDrillHierarchy,
    this.onProvisionNe,
    this.viewModel,
  });

  /// Optional custom child widget (e.g. pre-configured [PropertyGrid]). When null,
  /// a default [PropertyGrid] is rendered using [fields] and [initialValues].
  final Widget? child;

  /// List of field descriptors to display in the default [PropertyGrid].
  final List<FieldDescriptor> fields;

  /// Initial property values passed to the default [PropertyGrid].
  final Map<String, Object?> initialValues;

  /// The active view identifier.
  final String activeView;

  /// The target node ID associated with operational use case actions.
  final String? currentNodeId;

  /// Callback executed when property grid edits are committed.
  final void Function(Map<String, Object?>)? onSave;

  /// Callback executed when `UC-03: Configure Location` is triggered.
  final void Function(String nodeId)? onConfigureLocation;

  /// Callback executed when `UC-10: Drill Hierarchy` is triggered.
  final void Function(String nodeId)? onDrillHierarchy;

  /// Callback executed when `UC-15: Provision NE` is triggered.
  final void Function(String nodeId)? onProvisionNe;

  /// Optional explicit [PropertiesViewModel] instance.
  final PropertiesViewModel? viewModel;

  PropertiesViewModel? _resolveViewModel(BuildContext context) {
    if (viewModel != null) return viewModel;
    try {
      return context.read<PropertiesViewModel>();
    } catch (_) {
      return null;
    }
  }

  void _triggerConfigureLocation(BuildContext context) {
    final targetId = currentNodeId ?? activeView;
    onConfigureLocation?.call(targetId);
    _resolveViewModel(context)?.configureLocation(targetId);
  }

  void _triggerDrillHierarchy(BuildContext context) {
    final targetId = currentNodeId ?? activeView;
    onDrillHierarchy?.call(targetId);
    _resolveViewModel(context)?.drillHierarchy(targetId);
  }

  void _triggerProvisionNe(BuildContext context) {
    final targetId = currentNodeId ?? activeView;
    onProvisionNe?.call(targetId);
    _resolveViewModel(context)?.provisionNe(targetId);
  }

  @override
  Widget build(BuildContext context) {
    final vm = viewModel ?? (context.watch<PropertiesViewModel?>());
    if (vm != null) {
      return ListenableBuilder(
        listenable: vm,
        builder: (BuildContext context, Widget? child) {
          return _buildContent(context, vm);
        },
      );
    }
    return _buildContent(context, null);
  }

  Widget _buildContent(BuildContext context, PropertiesViewModel? vm) {
    final effectiveFields = fields.isNotEmpty
        ? fields
        : (vm?.fields ?? const <FieldDescriptor>[]);
    final actionMessage = vm?.state.actionMessage;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Operational Use Case Action Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.5),
            border: Border(
              bottom: BorderSide(
                color: Theme.of(context).dividerColor,
                width: 1.0,
              ),
            ),
          ),
          child: Wrap(
            spacing: 8.0,
            runSpacing: 8.0,
            alignment: WrapAlignment.start,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              OutlinedButton.icon(
                key: const Key('uc_03_configure_location_button'),
                onPressed: () => _triggerConfigureLocation(context),
                icon: const Icon(Icons.edit_location_alt, size: 16),
                label: const Text('UC-03: Configure Location'),
              ),
              OutlinedButton.icon(
                key: const Key('uc_10_drill_hierarchy_button'),
                onPressed: () => _triggerDrillHierarchy(context),
                icon: const Icon(Icons.account_tree, size: 16),
                label: const Text('UC-10: Drill Hierarchy'),
              ),
              OutlinedButton.icon(
                key: const Key('uc_15_provision_ne_button'),
                onPressed: () => _triggerProvisionNe(context),
                icon: const Icon(Icons.router, size: 16),
                label: const Text('UC-15: Provision NE'),
              ),
            ],
          ),
        ),
        if (actionMessage != null && actionMessage.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0),
            color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
            child: Text(
              actionMessage,
              key: const Key('properties_action_status_message'),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
        Expanded(
          child: child ??
              PropertyGrid(
                activeView: activeView,
                fields: effectiveFields,
                initialValues: initialValues,
                onSave: onSave,
              ),
        ),
      ],
    );
  }
}
