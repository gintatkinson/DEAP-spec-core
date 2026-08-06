import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/data/remote/gnmi_telemetry_client.dart';

void main() {
  group('GnmiTelemetryClient Tests', () {
    late GnmiTelemetryClient client;

    setUp(() {
      client = GnmiTelemetryClient();
    });

    tearDown(() async {
      await client.disconnectStream();
    });

    test('initial client state is disconnected', () {
      expect(client.isConnected, isFalse);
      expect(client.activeTarget, isNull);
      expect(client.activePaths, isNull);
    });

    test('connectStream initializes stream session', () {
      final stream = client.connectStream(
        target: '192.168.1.1:50051',
        paths: ['/interfaces/state'],
      );

      expect(client.isConnected, isTrue);
      expect(client.activeTarget, equals('192.168.1.1:50051'));
      expect(client.activePaths, equals(['/interfaces/state']));
      expect(stream, isNotNull);
    });

    test('injectUpdate emits telemetry metrics to active stream listeners', () async {
      final stream = client.connectStream();

      final received = <GnmiTelemetryUpdate>[];
      final subscription = stream.listen(received.add);

      final update = GnmiTelemetryUpdate(
        path: '/interfaces/interface[name=eth0]/state/counters/in-octets',
        value: 2048,
      );

      client.injectUpdate(update);

      await Future.delayed(const Duration(milliseconds: 10));

      expect(received.length, equals(1));
      expect(received.first.path, equals(update.path));
      expect(received.first.value, equals(2048));

      await subscription.cancel();
    });

    test('injectUpdate throws StateError when stream is disconnected', () {
      final update = GnmiTelemetryUpdate(path: '/test', value: 100);
      expect(() => client.injectUpdate(update), throwsStateError);
    });

    test('disconnectStream resets client state and closes stream', () async {
      final stream = client.connectStream();
      bool doneCalled = false;

      stream.listen((_) {}, onDone: () {
        doneCalled = true;
      });

      await client.disconnectStream();

      expect(client.isConnected, isFalse);
      expect(client.activeTarget, isNull);
      expect(client.activePaths, isNull);
      expect(doneCalled, isTrue);
    });
  });
}
