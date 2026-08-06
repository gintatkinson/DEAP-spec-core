import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/features/tables/tabbed_container.dart';
import 'package:app_flutter/features/tables/view_models/tables_view_model.dart';
import 'package:app_flutter/domain/data_source.dart';
import 'package:app_flutter/domain/instance_record.dart';
import 'package:app_flutter/domain/result.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart' show SharedPreferencesThemeService;
import 'package:app_flutter/features/tree/tree_node.dart';
import 'package:app_flutter/features/topology/topology_map.dart' show TopologyData;

/// A [TablesViewModel] subclass that allows setting [tabs] directly for testing.
class _TestViewModel extends TablesViewModel {
  _TestViewModel(DataSource ds) : super(ds, 'test');
  List<TabDescriptor> _testTabs = const [];

  @override
  List<TabDescriptor> get tabs => _testTabs;

  @override
  String? get selectedTabId =>
      _testTabs.isNotEmpty ? _testTabs.first.id : null;

  @override
  bool get loading => false;

  void setTabs(List<TabDescriptor> newTabs) {
    _testTabs = newTabs;
    notifyListeners();
  }

  @override
  Future<void> selectTab(String tabId) async {
    // no-op for test
  }
}

class _StubDataSource implements DataSource {
  @override
  String get name => 'stub';

  @override
  Future<Result<void>> dispose() async => const Result.success(null);

  @override
  Future<Result<List<TypeDescriptor>>> discoverTypes() async => const Result.success([]);

  @override
  Future<Result<TypeDescriptor?>> typeFor(String typeName) async => const Result.success(null);

  @override
  Future<Result<List<(String, String)>>> discoverHierarchy() async => const Result.success([]);

  @override
  Future<Result<Map<String, dynamic>>> fetchProperties(String nodeId) async => const Result.success({});

  @override
  Future<Result<void>> saveProperties(
          String nodeId, Map<String, dynamic> data) async => const Result.success(null);

  @override
  Stream<Result<Map<String, dynamic>>> watchProperties(String nodeId) =>
      const Stream.empty();

  @override
  Future<Result<List<InstanceRecord>>> fetchRelatedInstances({
    required String parentNodeId,
    required TypeDescriptor targetType,
  }) async =>
      const Result.success([]);

  @override
  Future<Result<List<TreeNode>>> fetchRootNodes() async => const Result.success([]);
  @override
  Future<Result<List<TreeNode>>> fetchChildrenForNode(String parentId) async => const Result.success([]);

  @override
  Future<Result<TopologyData>> fetchTopologyData() async =>
      const Result.success(TopologyData(coordinateMapping: {}, nodes: [], links: []));
}

Widget _wrapWithProviders(Widget child, _TestViewModel vm) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider<TablesViewModel>.value(value: vm),
      ChangeNotifierProvider<ThemeController>.value(
        value: ThemeController(SharedPreferencesThemeService()),
      ),
    ],
    child: MaterialApp(home: child),
  );
}

Widget _buildTestApp(_TestViewModel vm) {
  return _wrapWithProviders(const TabbedContainer(), vm);
}

TabDescriptor _makeTab(String id, String label) {
  return TabDescriptor(
    id: id,
    label: label,
    type: TypeDescriptor(
      typeName: id,
      displayName: label,
      iconName: 'folder',
      fields: [],
      childTypes: [],
      relatedTypes: [],
      parentTypes: [],
    ),
  );
}

void main() {
  testWidgets(
    'dispose cleans up deferred-old TabController before super.dispose',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final vm = _TestViewModel(_StubDataSource());

      // Phase 1: mount with 3 tabs, creating TabController A (length=3)
      vm.setTabs([
        _makeTab('a', 'Alpha'),
        _makeTab('b', 'Beta'),
        _makeTab('c', 'Gamma'),
      ]);
      await tester.pumpWidget(_buildTestApp(vm));
      await tester.pump(); // settle post-frame callbacks

      // Phase 2: tap on 'Gamma' to start a tab-switch animation on A.
      // This makes TabController A's internal Ticker ACTIVE.
      await tester.tap(find.widgetWithText(Tab, 'Gamma'));

      // Phase 3: process one frame so the gesture fires animateTo on A.
      // The animation starts, Ticker becomes active, but the animation
      // does NOT complete (default duration 300ms).
      await tester.pump();

      // Phase 4: change tabs while the old controller A still has an active
      // ticker.  This triggers:
      //   listener -> setState -> _updateController
      //   -> defers disposal of A via addPostFrameCallback
      //   -> creates TabController B (length=4, new vsync ticker)
      vm.setTabs([
        _makeTab('w', 'Whiskey'),
        _makeTab('x', 'Xray'),
        _makeTab('y', 'Yankee'),
        _makeTab('z', 'Zulu'),
      ]);
      // _onViewModelChanged ran synchronously inside setTabs.

      // Phase 5: dispose the widget BEFORE the post-frame callback fires.
      // Inside dispose():
      //   1. TabController B is disposed (ticker removed from provider)
      //   2. super.dispose() -> TickerProviderStateMixin.dispose()
      //      -> _WidgetTickerProvider.dispose()
      //      -> iterates remaining tickers, finds A's ticker
      //      -> A's ticker.isActive == true -> THROWS FlutterError
      // The bug manifests as:
      //   "TickerProvider disposed while Ticker is active"
      await tester.pumpWidget(
        _wrapWithProviders(const SizedBox.shrink(), vm),
      );

      // Phase 6: let any queued microtasks and post-frame callbacks settle.
      await tester.pump();

      // If we reach here without a FlutterError, the fix is working.
      // (After the fix is applied, this test should pass.)
    },
  );
}
