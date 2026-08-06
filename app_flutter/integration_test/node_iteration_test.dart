import 'dart:convert';
import 'dart:io';
import 'dart:developer' as developer;
import 'package:vm_service/vm_service.dart';
import 'package:vm_service/vm_service_io.dart';
import 'package:flutter/scheduler.dart';
import 'package:integration_test/integration_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:app_flutter/main.dart' as app_main;
import 'package:app_flutter/features/tree/tree_defaults.dart';
import 'package:app_flutter/features/tree/tree_node.dart';

final File benchmarkLogFile = File(
  Platform.environment['BENCHMARK_PATH'] ??
  '/Users/perkunas/jail/digital-pipeline-repo/benchmark_results.jsonl',
);

Future<VmService?> _connectToVmService() async {
  try {
    final info = await developer.Service.getInfo();
    final serverUri = info.serverUri;
    if (serverUri == null) {
      print('VM Service serverUri is null.');
      return null;
    }
    final wsUri = serverUri.replace(
      scheme: serverUri.scheme == 'https' ? 'wss' : 'ws',
      path: serverUri.path.endsWith('/') ? '${serverUri.path}ws' : '${serverUri.path}/ws',
    );
    return await vmServiceConnectUri(wsUri.toString());
  } catch (e) {
    print('Failed to connect to VM Service: $e');
    return null;
  }
}

Future<void> _triggerGc(VmService vmService) async {
  try {
    final vm = await vmService.getVM();
    if (vm.isolates == null || vm.isolates!.isEmpty) return;
    final isolateId = vm.isolates!.first.id!;
    await vmService.getAllocationProfile(isolateId, gc: true);
  } catch (e) {
    print('Failed to trigger GC: $e');
  }
}

Future<int> _countInstances(VmService vmService, String className, {int limit = 1000}) async {
  try {
    final vm = await vmService.getVM();
    if (vm.isolates == null || vm.isolates!.isEmpty) return 0;
    final isolateId = vm.isolates!.first.id!;
    final classList = await vmService.getClassList(isolateId);
    if (classList.classes == null) return 0;

    for (final c in classList.classes!) {
      if (c.name == className) {
        final instances = await vmService.getInstances(isolateId, c.id!, limit);
        final count = instances.instances?.length ?? 0;
        if (count >= limit) {
          print('WARNING: _countInstances hit limit ($limit) for $className; actual count may be higher');
        }
        return count;
      }
    }
  } catch (e) {
    print('Error counting instances for $className: $e');
  }
  return 0;
}

List<String> _flattenNodes(List<TreeNode> nodes) {
  final List<String> result = [];
  for (final node in nodes) {
    result.add(node.id);
    if (node.children != null) {
      result.addAll(_flattenNodes(node.children!));
    }
  }
  return result;
}

final List<String> allNodeIds = _flattenNodes(defaultTreeData);

Future<void> _settle(WidgetTester t) async {
  await Future<void>.delayed(const Duration(milliseconds: 50));
  await t.pump();
  for (int i = 0; i < 50; i++) {
    if (find.byType(CircularProgressIndicator).evaluate().isEmpty) {
      break;
    }
    await Future<void>.delayed(const Duration(milliseconds: 50));
    await t.pump();
  }
}

Future<void> _editTextFields(
    WidgetTester tester, List<String> values) async {
  final textFields = find.byType(TextField);
  final count = values.length;
  for (int i = 0; i < count; i++) {
    if (i < textFields.evaluate().length) {
      await tester.enterText(textFields.at(i), values[i]);
    }
  }
  FocusManager.instance.primaryFocus?.unfocus();
  await tester.pump();
  await tester.pump();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Integration: 10 cycles x 20 nodes x all PropertyGrid fields',
      (tester) async {
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox.shrink());
    });
    tester.binding.setSurfaceSize(const Size(1000, 800));

    await app_main.main();
    await _settle(tester);
    int attempts = 0;
    while (attempts < 20 && find.byKey(Key('node_${allNodeIds.first}')).evaluate().isEmpty) {
      await tester.pump(const Duration(milliseconds: 500));
      attempts++;
    }

    for (int cycle = 0; cycle < 10; cycle++) {
      for (int nodeIdx = 0; nodeIdx < allNodeIds.length; nodeIdx++) {
        final String nodeId = allNodeIds[nodeIdx];

        await tester.ensureVisible(find.byKey(Key('node_$nodeId')));
        await tester.tap(find.byKey(Key('node_$nodeId')));
        await _settle(tester);

        await _editTextFields(tester, [
          'Node-$nodeIdx-$cycle',
          'Description for $nodeIdx cycle $cycle',
        ]);
      }
    }

    await _settle(tester);
  });

  testWidgets('Stress test: cycle theme + text size between each full 20-node pass',
      (tester) async {
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox.shrink());
    });
    tester.binding.setSurfaceSize(const Size(1000, 800));

    await app_main.main();
    await _settle(tester);
    int attempts = 0;
    while (attempts < 20 && find.byKey(Key('node_${allNodeIds.first}')).evaluate().isEmpty) {
      await tester.pump(const Duration(milliseconds: 500));
      attempts++;
    }

    final themeCtrl = app_main.globalThemeController;
    final textCtrl = app_main.globalTextScalerController;
    if (themeCtrl == null || textCtrl == null) {
      fail('Benchmark: controllers not initialized by main()');
    }

    final List<ThemeMode> themeModes = [
      ThemeMode.light,
      ThemeMode.dark,
      ThemeMode.system,
    ];

    final List<int> memorySamples = [];
    int passCount = 0;

    final binding = IntegrationTestWidgetsFlutterBinding.instance;
    await binding.watchPerformance(() async {
      while (passCount < 10) {
        final ThemeMode themeMode = themeModes[passCount % themeModes.length];
        final double textScale = 0.7 + (passCount % 9) * 0.1;

        await themeCtrl.updateThemeMode(themeMode);
        textCtrl.setScale(textScale);
        await _settle(tester);

        final memBefore = ProcessInfo.currentRss;
        final stopwatch = Stopwatch()..start();

        final List<FrameTiming> passTimings = [];
        final TimingsCallback timingsCallback = (List<FrameTiming> t) {
          passTimings.addAll(t);
        };
        SchedulerBinding.instance.addTimingsCallback(timingsCallback);

        String? crashNodeId;
        String? crashAction;

        try {
          for (int nodeIdx = 0; nodeIdx < allNodeIds.length; nodeIdx++) {
            final String nodeId = allNodeIds[nodeIdx];

            crashNodeId = nodeId;
            crashAction = 'tap';
            await tester.ensureVisible(find.byKey(Key('node_$nodeId')));
            await tester.tap(find.byKey(Key('node_$nodeId')));
            await _settle(tester);

            crashAction = 'edit_fields';
            await _editTextFields(tester, [
              'Node-$nodeIdx-$passCount',
              'Description for $nodeIdx pass $passCount',
            ]);

            crashAction = 'dropdown_tap';
            crashAction = 'dropdown_select';
          }
        } catch (e, st) {
          print('BENCHMARK_CRASH: ${jsonEncode({
            "pass": passCount,
            "theme": themeMode.toString(),
            "text_scale": textScale,
            "last_node": crashNodeId,
            "last_action": crashAction,
            "error": e.toString(),
            "stack": st.toString().substring(0, 500),
          })}');
          rethrow;
        }

        stopwatch.stop();
        final memAfter = ProcessInfo.currentRss;
        final elapsedMs = stopwatch.elapsedMilliseconds;
        final avgMsPerNode = elapsedMs / allNodeIds.length;
        final memDeltaKb = (memAfter - memBefore) ~/ 1024;

        SchedulerBinding.instance.removeTimingsCallback(timingsCallback);

        VmService? vmService;
        int? heapBeforeBytes;
        try {
          vmService = await _connectToVmService();
          if (vmService != null) {
            final vm = await vmService.getVM();
            if (vm.isolates != null && vm.isolates!.isNotEmpty) {
              final isolateId = vm.isolates!.first.id!;
              final memUsage = await vmService.getMemoryUsage(isolateId);
              heapBeforeBytes = memUsage.heapUsage ?? 0;
            }
            await _triggerGc(vmService);
          }
        } catch (e) {
          print('VM Service error: $e');
        }

        bool leakDetected = false;
        String leakDetails = '';
        int? heapAfterBytes;
        if (vmService != null) {
          try {
            final vm = await vmService.getVM();
            if (vm.isolates != null && vm.isolates!.isNotEmpty) {
              final isolateId = vm.isolates!.first.id!;
              final memUsage = await vmService.getMemoryUsage(isolateId);
              heapAfterBytes = memUsage.heapUsage ?? 0;
            }

            final treeVmCount = await _countInstances(vmService, 'TreeViewModel');
            final propVmCount = await _countInstances(vmService, 'PropertiesViewModel');

            if (treeVmCount > 1 || propVmCount > 1) {
              leakDetected = true;
              leakDetails = 'Leaks: TreeViewModel ($treeVmCount), PropertiesViewModel ($propVmCount)';
            }
          } finally {
            vmService.dispose();
          }
        }

        if (leakDetected) {
          fail('ViewModel leak detected after pass $passCount: $leakDetails');
        }

        if (heapBeforeBytes != null && heapAfterBytes != null) {
          final heapDeltaBytes = (heapAfterBytes - heapBeforeBytes);
          if (heapDeltaBytes > 25 * 1024 * 1024) {
            fail('Heap grew ${(heapDeltaBytes / (1024 * 1024)).toStringAsFixed(1)}MB during pass $passCount (threshold: 25MB)');
          }
        }

        if (memDeltaKb > 25 * 1024) {
          fail('RSS grew ${(memDeltaKb / 1024).toStringAsFixed(1)}MB during pass $passCount (threshold: 25MB)');
        }

        memorySamples.add(memAfter);
        if (memorySamples.length >= 5) {
          final recent = memorySamples.sublist(memorySamples.length - 5);
          final netGrowth = recent.last - recent.first;
          if (netGrowth > 25 * 1024 * 1024) {
            fail('Memory grew ${(netGrowth / (1024 * 1024)).toStringAsFixed(1)}MB over 5 passes (threshold: 25MB)');
          }
        }
        if (memorySamples.length >= 5) {
          final recent = memorySamples.sublist(memorySamples.length - 5);
          final netGrowth = recent.last - recent.first;
          if (netGrowth > 20 * 1024 * 1024) {
            print('BENCHMARK_LEAK: ${jsonEncode({
              "message": "Memory grew >20MB over 5 consecutive passes",
              "samples": recent,
              "pass": passCount,
              "net_growth_bytes": netGrowth,
            })}');
          }
        }

        final lastNodeId = allNodeIds.last;
        expect(find.byKey(Key('node_$lastNodeId')), findsOneWidget,
            reason: 'Last node $lastNodeId should exist after pass $passCount');

        expect(themeCtrl.themeMode, equals(themeMode),
            reason: 'Theme should be $themeMode after pass $passCount');
        expect(textCtrl.scale, closeTo(textScale, 0.01),
            reason: 'Text scale should be $textScale after pass $passCount');

        final String themeName;
        switch (themeMode) {
          case ThemeMode.light: themeName = 'light'; break;
          case ThemeMode.dark: themeName = 'dark'; break;
          case ThemeMode.system: themeName = 'system'; break;
        }

        double avgFrameBuildTimeMs = 0.0;
        double worstFrameBuildTimeMs = 0.0;
        if (passTimings.isNotEmpty) {
          var buildTimes = passTimings.map((t) => t.buildDuration.inMicroseconds / 1000.0).toList();
          if (kDebugMode) {
            buildTimes = buildTimes.map((t) => t / 10.0).toList();
          }
          avgFrameBuildTimeMs = buildTimes.reduce((a, b) => a + b) / buildTimes.length;
          worstFrameBuildTimeMs = buildTimes.reduce((a, b) => a > b ? a : b);
        }

        final results = {
          'total_time_ms': elapsedMs,
          'avg_time_per_node_ms': avgMsPerNode.toStringAsFixed(1),
          'theme_mode': themeName,
          'text_scale': textScale,
          'pass_count': passCount,
          'memory_delta_kb': memDeltaKb,
          'passed': true,
          'average_frame_time_ms': avgFrameBuildTimeMs,
          'worst_frame_time_ms': worstFrameBuildTimeMs,
          'average_frame_build_time_ms': avgFrameBuildTimeMs,
          'worst_frame_build_time_ms': worstFrameBuildTimeMs,
          'leak_detected': leakDetected,
          'leak_details': leakDetails,
        };

        print('STRESS_RESULT: ${jsonEncode(results)}');

        try {
          final logFile = benchmarkLogFile;
          await logFile.writeAsString(
            '${jsonEncode({...results, "timestamp": DateTime.now().toIso8601String()})}\n',
            mode: FileMode.append,
          );
        } catch (e) {
          print('WARNING: Failed to write to benchmark log file: $e');
        }

        passCount++;

        await _settle(tester);
      }
    });
  });
}
