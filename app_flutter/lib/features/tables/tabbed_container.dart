import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/features/tables/view_models/tables_view_model.dart';
import 'package:app_flutter/features/tables/table_view_widget.dart';

/// Realises: [Feat-10/TabbedContainer]
///
/// Renders a tabbed view whose labels, columns, and data are driven by a
/// [TablesViewModel].
///
/// Exists to display child/related types of the currently selected tree node in
/// separate tabs, removing the need for hardcoded tab definitions. Use this
/// widget anywhere the UI needs data-source-driven tab navigation.
@immutable
class TabbedContainer extends StatefulWidget {
  /// Member documentation.
  const TabbedContainer({super.key});

  @override
  State<TabbedContainer> createState() => _TabbedContainerState();
}

class _TabbedContainerState extends State<TabbedContainer>
    with TickerProviderStateMixin {
  TabController? _tabController;
  TablesViewModel? _viewModel;
  int? _lastIndex;
  final List<TabController> _pendingDispose = [];

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final newViewModel = Provider.of<TablesViewModel>(context);
    if (newViewModel != _viewModel) {
      _viewModel?.removeListener(_onViewModelChanged);
      _viewModel = newViewModel;
      _viewModel?.addListener(_onViewModelChanged);
      _updateController();
    }
  }

  void _onViewModelChanged() {
    if (mounted) {
      setState(() {
        _updateController();
      });
    }
  }

  void _updateController() {
    final tabs = _viewModel?.tabs ?? [];
    if (tabs.isEmpty) {
      _tabController?.removeListener(_onTabTick);
      _tabController?.dispose();
      _tabController = null;
      return;
    }
    if (_tabController == null || _tabController!.length != tabs.length) {
      final oldController = _tabController;
      if (oldController != null) {
        oldController.removeListener(_onTabTick);
        _pendingDispose.add(oldController);
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_pendingDispose.contains(oldController)) {
            _pendingDispose.remove(oldController);
            oldController.dispose();
          }
        });
      }
      _tabController = TabController(length: tabs.length, vsync: this);
      final initialIndex =
          tabs.indexWhere((t) => t.id == _viewModel?.selectedTabId);
      if (initialIndex > 0) _tabController!.index = initialIndex;
      _tabController!.addListener(_onTabTick);
      _lastIndex = _tabController!.index;
    }
  }

  void _onTabTick() {
    if (_tabController != null) {
      if (_tabController!.index != _lastIndex) {
        _lastIndex = _tabController!.index;
        setState(() {});
      }
      if (!_tabController!.indexIsChanging) {
        final tabs = _viewModel?.tabs ?? [];
        if (_tabController!.index < tabs.length) {
          final tab = tabs[_tabController!.index];
          _viewModel?.selectTab(tab.id);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_viewModel == null) return const SizedBox.shrink();
    final tabs = _viewModel!.tabs;

    if (tabs.isEmpty) {
      if (_viewModel!.error != null) {
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              _viewModel!.error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        );
      }
      if (_viewModel!.loading) {
        return const Center(child: CircularProgressIndicator());
      }
      return const SizedBox.shrink();
    }

    if (_tabController == null) {
      return const SizedBox.shrink();
    }

    final panelOpacity = context.watch<ThemeController>().panelOpacity;
    return Container(
      color: Theme.of(context).cardColor.withOpacity(panelOpacity),
      child: Column(
        children: [
          Material(
            color: Colors.transparent,
            child: TabBar(
              controller: _tabController!,
              tabs: tabs.map((t) => Tab(text: t.label)).toList(),
            ),
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController!,
              children: List.generate(tabs.length, (idx) {
                return LazyTab(
                  isSelected: _tabController!.index == idx,
                  child: const TableViewWidget(),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _viewModel?.removeListener(_onViewModelChanged);
    _tabController?.removeListener(_onTabTick);
    _tabController?.dispose();
    for (final c in _pendingDispose) {
      c.dispose();
    }
    _pendingDispose.clear();
    super.dispose();
  }
}

/// Realises: [Feat-10/LazyTab]
///
/// Keeps an offstage tab alive lazily when selected.
@immutable
class LazyTab extends StatefulWidget {
  /// Member documentation.
  const LazyTab({super.key, required this.child, required this.isSelected});
  /// Member documentation.
  final Widget child;
  /// Member documentation.
  final bool isSelected;
  @override
  State<LazyTab> createState() => _LazyTabState();
}

class _LazyTabState extends State<LazyTab> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Offstage(offstage: !widget.isSelected, child: widget.child);
  }
}
