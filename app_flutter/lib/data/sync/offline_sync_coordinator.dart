/// A single local change queued for synchronisation.
///
/// Realises: [persistence-architecture-blueprint.md/LocalChange]
///
/// Captures the entity identifier, the serialised payload, and the wall-clock
/// timestamp at which the change was recorded.
class LocalChange {
  /// Creates a [LocalChange].
  ///
  /// [entityId] uniquely identifies the domain entity being changed.
  /// [payload] carries the serialised change data.
  /// [timestamp] defaults to [DateTime.now] when omitted.
  LocalChange({
    required this.entityId,
    required this.payload,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Unique identifier of the entity that was changed.
  final String entityId;

  /// Serialised change payload (e.g. JSON map).
  final Map<String, dynamic> payload;

  /// Wall-clock time at which this change was recorded.
  final DateTime timestamp;
}

/// Outcome of a conflict resolution between a local and remote change.
///
/// Realises: [persistence-architecture-blueprint.md/ConflictResult]
enum ConflictResult {
  /// The local change was accepted over the remote.
  localWins,

  /// The remote change was accepted over the local.
  remoteWins,
}

/// Coordinates offline-first data synchronisation.
///
/// Realises: [persistence-architecture-blueprint.md/OfflineSyncCoordinator]
///
/// Queues local mutations while the device is offline, reconciles them with
/// the remote data source when connectivity is available, and resolves
/// conflicts using a last-writer-wins strategy.
///
/// Usage:
/// ```dart
/// final coordinator = OfflineSyncCoordinator();
/// coordinator.queueLocalChange(
///   LocalChange(entityId: 'item-1', payload: {'name': 'updated'}),
/// );
/// final results = coordinator.reconcileWithRemote(remoteChanges);
/// ```
class OfflineSyncCoordinator {
  /// Internal queue of pending local changes awaiting sync.
  final List<LocalChange> _pendingChanges = <LocalChange>[];

  /// Returns an unmodifiable view of the pending local changes.
  List<LocalChange> get pendingChanges =>
      List<LocalChange>.unmodifiable(_pendingChanges);

  /// Queues a local mutation for later synchronisation.
  ///
  /// The [change] is appended to the internal queue.  It will be processed
  /// during the next call to [reconcileWithRemote].
  void queueLocalChange(LocalChange change) {
    _pendingChanges.add(change);
  }

  /// Reconciles queued local changes against [remoteChanges].
  ///
  /// For each entity that has both a local and a remote change, calls
  /// [resolveConflict] to determine the winner.  Returns a map of
  /// entity-ID → winning payload.
  ///
  /// After reconciliation the internal queue is cleared.
  Map<String, Map<String, dynamic>> reconcileWithRemote(
    List<LocalChange> remoteChanges,
  ) {
    final Map<String, Map<String, dynamic>> reconciled =
        <String, Map<String, dynamic>>{};

    // Index remote changes by entity ID (last entry wins if duplicates).
    final Map<String, LocalChange> remoteIndex = <String, LocalChange>{};
    for (final LocalChange remote in remoteChanges) {
      remoteIndex[remote.entityId] = remote;
    }

    // Walk local queue.
    for (final LocalChange local in _pendingChanges) {
      final LocalChange? remote = remoteIndex.remove(local.entityId);
      if (remote == null) {
        // No conflict — local change is new.
        reconciled[local.entityId] = local.payload;
      } else {
        final ConflictResult result = resolveConflict(local, remote);
        reconciled[local.entityId] =
            result == ConflictResult.localWins ? local.payload : remote.payload;
      }
    }

    // Remaining remote-only changes.
    for (final MapEntry<String, LocalChange> entry in remoteIndex.entries) {
      reconciled[entry.key] = entry.value.payload;
    }

    _pendingChanges.clear();
    return reconciled;
  }

  /// Resolves a conflict between a [local] and [remote] change.
  ///
  /// Uses a **last-writer-wins** strategy: the change with the later
  /// [LocalChange.timestamp] prevails.  When timestamps are equal the
  /// local change wins.
  ConflictResult resolveConflict(LocalChange local, LocalChange remote) {
    if (local.timestamp.isAfter(remote.timestamp) ||
        local.timestamp.isAtSameMomentAs(remote.timestamp)) {
      return ConflictResult.localWins;
    }
    return ConflictResult.remoteWins;
  }
}
