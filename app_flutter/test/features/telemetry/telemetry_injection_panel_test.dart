import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/data/remote/gnmi_telemetry_client.dart';
import 'package:app_flutter/features/telemetry/telemetry_injection_panel.dart';

void main() {
  group('TelemetryInjectionPanel Widget Tests', () {
    late GnmiTelemetryClient client;

    setUp(() {
      client = GnmiTelemetryClient();
    });

    tearDown(() async {
      await client.disconnectStream();
    });

    testWidgets('renders telemetry injection panel controls', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TelemetryInjectionPanel(client: client),
          ),
        ),
      );

      expect(find.text('Telemetry Injection Panel'), findsOneWidget);
      expect(find.text('gNMI Target Path'), findsOneWidget);
      expect(find.text('Metric Value'), findsOneWidget);
      expect(find.text('Connect Stream'), findsOneWidget);
      expect(find.byKey(const Key('inject_telemetry_button')), findsOneWidget);
    });

    testWidgets('connect stream button toggles stream state', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TelemetryInjectionPanel(client: client),
          ),
        ),
      );

      expect(find.text('Disconnected'), findsOneWidget);

      await tester.tap(find.text('Connect Stream'));
      await tester.pump();

      expect(client.isConnected, isTrue);
      expect(find.text('Streaming'), findsOneWidget);

      await tester.tap(find.text('Disconnect'));
      await tester.pump();

      expect(client.isConnected, isFalse);
      expect(find.text('Disconnected'), findsOneWidget);
    });

    testWidgets('inject telemetry button triggers callback and adds to recent updates', (WidgetTester tester) async {
      GnmiTelemetryUpdate? injectedUpdate;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TelemetryInjectionPanel(
              client: client,
              onTelemetryInjected: (u) => injectedUpdate = u,
            ),
          ),
        ),
      );

      // Connect stream first so injection works
      await tester.tap(find.text('Connect Stream'));
      await tester.pump();

      await tester.tap(find.byKey(const Key('inject_telemetry_button')));
      await tester.pump();

      expect(injectedUpdate, isNotNull);
      expect(find.text('Recent Updates:'), findsOneWidget);
    });
  });
}
