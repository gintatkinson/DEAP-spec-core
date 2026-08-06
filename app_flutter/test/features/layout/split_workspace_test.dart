import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/features/layout/split_workspace.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart' show SharedPreferencesThemeService;

void main() {
  testWidgets('SplitWorkspace deferred resizing sets state correctly', (WidgetTester tester) async {
    double draggedSize = 0.0;
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ThemeController>(create: (_) => ThemeController(SharedPreferencesThemeService())),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: SplitWorkspace(
              direction: Axis.horizontal,
              minFirstPaneSize: 50.0,
              initialRatio: 0.5,
              splitterKey: const Key('splitter'),
              leading: const Text('Leading'),
              trailing: const Text('Trailing'),
              onDrag: (size) {
                draggedSize = size;
              },
            ),
          ),
        ),
      ),
    );
    
    final splitter = find.byKey(const Key('splitter'));
    expect(splitter, findsOneWidget);

    await tester.drag(splitter, const Offset(100.0, 0.0));
    await tester.pumpAndSettle();
    
    expect(draggedSize, greaterThan(400.0));
  });
}
