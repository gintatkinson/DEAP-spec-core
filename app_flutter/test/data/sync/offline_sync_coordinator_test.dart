import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/data/sync/offline_sync_coordinator.dart';

void main() {
  group('OfflineSyncCoordinator', () {
    late OfflineSyncCoordinator coordinator;

    setUp(() {
      coordinator = OfflineSyncCoordinator();
    });

    group('queueLocalChange', () {
      test('adds change to pending list', () {
        final LocalChange change = LocalChange(
          entityId: 'item-1',
          payload: <String, dynamic>{'name': 'a'},
        );

        coordinator.queueLocalChange(change);

        expect(coordinator.pendingChanges, hasLength(1));
        expect(coordinator.pendingChanges.first.entityId, equals('item-1'));
      });

      test('queues multiple changes', () {
        coordinator.queueLocalChange(
          LocalChange(entityId: 'a', payload: <String, dynamic>{}),
        );
        coordinator.queueLocalChange(
          LocalChange(entityId: 'b', payload: <String, dynamic>{}),
        );

        expect(coordinator.pendingChanges, hasLength(2));
      });

      test('pendingChanges is unmodifiable', () {
        coordinator.queueLocalChange(
          LocalChange(entityId: 'a', payload: <String, dynamic>{}),
        );

        expect(
          () => coordinator.pendingChanges.add(
            LocalChange(entityId: 'x', payload: <String, dynamic>{}),
          ),
          throwsA(isA<UnsupportedError>()),
        );
      });
    });

    group('reconcileWithRemote', () {
      test('returns local-only changes when no remote overlap', () {
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'local'},
          ),
        );

        final Map<String, Map<String, dynamic>> result =
            coordinator.reconcileWithRemote(<LocalChange>[]);

        expect(result['item-1'], equals(<String, dynamic>{'v': 'local'}));
      });

      test('returns remote-only changes when no local overlap', () {
        final Map<String, Map<String, dynamic>> result =
            coordinator.reconcileWithRemote(<LocalChange>[
          LocalChange(
            entityId: 'item-2',
            payload: <String, dynamic>{'v': 'remote'},
          ),
        ]);

        expect(result['item-2'], equals(<String, dynamic>{'v': 'remote'}));
      });

      test('local wins when local timestamp is later', () {
        final DateTime now = DateTime.now();
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'local'},
            timestamp: now.add(const Duration(seconds: 10)),
          ),
        );

        final Map<String, Map<String, dynamic>> result =
            coordinator.reconcileWithRemote(<LocalChange>[
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'remote'},
            timestamp: now,
          ),
        ]);

        expect(result['item-1'], equals(<String, dynamic>{'v': 'local'}));
      });

      test('remote wins when remote timestamp is later', () {
        final DateTime now = DateTime.now();
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'local'},
            timestamp: now,
          ),
        );

        final Map<String, Map<String, dynamic>> result =
            coordinator.reconcileWithRemote(<LocalChange>[
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'remote'},
            timestamp: now.add(const Duration(seconds: 10)),
          ),
        ]);

        expect(result['item-1'], equals(<String, dynamic>{'v': 'remote'}));
      });

      test('local wins when timestamps are equal', () {
        final DateTime now = DateTime.now();
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'local'},
            timestamp: now,
          ),
        );

        final Map<String, Map<String, dynamic>> result =
            coordinator.reconcileWithRemote(<LocalChange>[
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{'v': 'remote'},
            timestamp: now,
          ),
        ]);

        expect(result['item-1'], equals(<String, dynamic>{'v': 'local'}));
      });

      test('clears pending queue after reconciliation', () {
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'item-1',
            payload: <String, dynamic>{},
          ),
        );

        coordinator.reconcileWithRemote(<LocalChange>[]);

        expect(coordinator.pendingChanges, isEmpty);
      });

      test('handles mixed local, remote, and conflicting changes', () {
        final DateTime now = DateTime.now();
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'local-only',
            payload: <String, dynamic>{'src': 'local'},
            timestamp: now,
          ),
        );
        coordinator.queueLocalChange(
          LocalChange(
            entityId: 'conflict',
            payload: <String, dynamic>{'src': 'local'},
            timestamp: now.add(const Duration(seconds: 5)),
          ),
        );

        final Map<String, Map<String, dynamic>> result =
            coordinator.reconcileWithRemote(<LocalChange>[
          LocalChange(
            entityId: 'remote-only',
            payload: <String, dynamic>{'src': 'remote'},
            timestamp: now,
          ),
          LocalChange(
            entityId: 'conflict',
            payload: <String, dynamic>{'src': 'remote'},
            timestamp: now,
          ),
        ]);

        expect(result['local-only'], equals(<String, dynamic>{'src': 'local'}));
        expect(
            result['remote-only'], equals(<String, dynamic>{'src': 'remote'}));
        // Local timestamp is later so local wins.
        expect(result['conflict'], equals(<String, dynamic>{'src': 'local'}));
      });
    });

    group('resolveConflict', () {
      test('returns localWins when local is after remote', () {
        final DateTime now = DateTime.now();
        final ConflictResult result = coordinator.resolveConflict(
          LocalChange(
            entityId: 'x',
            payload: <String, dynamic>{},
            timestamp: now.add(const Duration(seconds: 1)),
          ),
          LocalChange(
            entityId: 'x',
            payload: <String, dynamic>{},
            timestamp: now,
          ),
        );

        expect(result, equals(ConflictResult.localWins));
      });

      test('returns remoteWins when remote is after local', () {
        final DateTime now = DateTime.now();
        final ConflictResult result = coordinator.resolveConflict(
          LocalChange(
            entityId: 'x',
            payload: <String, dynamic>{},
            timestamp: now,
          ),
          LocalChange(
            entityId: 'x',
            payload: <String, dynamic>{},
            timestamp: now.add(const Duration(seconds: 1)),
          ),
        );

        expect(result, equals(ConflictResult.remoteWins));
      });

      test('returns localWins when timestamps are equal', () {
        final DateTime now = DateTime.now();
        final ConflictResult result = coordinator.resolveConflict(
          LocalChange(
            entityId: 'x',
            payload: <String, dynamic>{},
            timestamp: now,
          ),
          LocalChange(
            entityId: 'x',
            payload: <String, dynamic>{},
            timestamp: now,
          ),
        );

        expect(result, equals(ConflictResult.localWins));
      });
    });
  });

  group('LocalChange', () {
    test('uses provided timestamp', () {
      final DateTime ts = DateTime(2026, 1, 1);
      final LocalChange change = LocalChange(
        entityId: 'id',
        payload: <String, dynamic>{},
        timestamp: ts,
      );

      expect(change.timestamp, equals(ts));
    });

    test('defaults timestamp to now when omitted', () {
      final DateTime before = DateTime.now();
      final LocalChange change = LocalChange(
        entityId: 'id',
        payload: <String, dynamic>{},
      );
      final DateTime after = DateTime.now();

      expect(
        change.timestamp.isAfter(before) ||
            change.timestamp.isAtSameMomentAs(before),
        isTrue,
      );
      expect(
        change.timestamp.isBefore(after) ||
            change.timestamp.isAtSameMomentAs(after),
        isTrue,
      );
    });
  });
}
