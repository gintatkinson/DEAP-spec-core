import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/data/remote/firestore_offline_queue.dart';

void main() {
  group('FirestoreOfflineQueue Tests', () {
    late FirestoreOfflineQueue queue;

    setUp(() {
      queue = FirestoreOfflineQueue();
    });

    test('initial queue is empty', () {
      expect(queue.isEmpty, isTrue);
      expect(queue.queueLength, equals(0));
      expect(queue.pendingOperations, isEmpty);
    });

    test('enqueueOperation accepts FirestoreOperation instance', () {
      final op = FirestoreOperation(
        id: 'op_1',
        action: 'create',
        path: 'nodes/node_1',
        data: {'name': 'Test Node'},
      );

      queue.enqueueOperation(op);

      expect(queue.isEmpty, isFalse);
      expect(queue.queueLength, equals(1));
      expect(queue.pendingOperations.first.id, equals('op_1'));
    });

    test('enqueueOperation accepts raw Map', () {
      queue.enqueueOperation({
        'id': 'op_2',
        'action': 'update',
        'path': 'nodes/node_2',
        'data': {'status': 'active'},
      });

      expect(queue.queueLength, equals(1));
      expect(queue.pendingOperations.first.action, equals('update'));
    });

    test('reconcileQueue flushes operations with executor', () async {
      queue.enqueueOperation({
        'id': 'op_1',
        'action': 'create',
        'path': 'nodes/node_1',
        'data': {'val': 1},
      });
      queue.enqueueOperation({
        'id': 'op_2',
        'action': 'update',
        'path': 'nodes/node_2',
        'data': {'val': 2},
      });

      final processedIds = <String>[];
      final count = await queue.reconcileQueue(
        executor: (op) async {
          processedIds.add(op.id);
          return true;
        },
      );

      expect(count, equals(2));
      expect(processedIds, containsAll(['op_1', 'op_2']));
      expect(queue.isEmpty, isTrue);
    });

    test('reconcileQueue retains operations that fail execution', () async {
      queue.enqueueOperation({'id': 'op_success', 'action': 'create', 'path': 'p1', 'data': {}});
      queue.enqueueOperation({'id': 'op_fail', 'action': 'create', 'path': 'p2', 'data': {}});

      final count = await queue.reconcileQueue(
        executor: (op) async => op.id == 'op_success',
      );

      expect(count, equals(1));
      expect(queue.queueLength, equals(1));
      expect(queue.pendingOperations.first.id, equals('op_fail'));
    });

    test('clearQueue empties pending operations', () {
      queue.enqueueOperation({'id': 'op_1', 'action': 'delete', 'path': 'p', 'data': {}});
      expect(queue.queueLength, equals(1));

      queue.clearQueue();
      expect(queue.isEmpty, isTrue);
    });
  });
}
