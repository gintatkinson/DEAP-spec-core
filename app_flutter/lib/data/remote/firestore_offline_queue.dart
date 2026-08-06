import 'dart:async';

/// Realises: [UC-03/FirestoreOperation]
/// Represents a queued offline Firestore write or mutation operation.
///
/// Encapsulates operation type (e.g. create, update, delete), target collection/path,
/// payload data, and timestamp for execution during reconciliation.
class FirestoreOperation {
  /// Unique identifier for this operation.
  final String id;

  /// The operation action, e.g., 'create', 'update', 'delete'.
  final String action;

  /// Target Firestore collection or document path.
  final String path;

  /// Payload data associated with the operation.
  final Map<String, dynamic> data;

  /// Timestamp when the operation was enqueued.
  final DateTime timestamp;

  /// Creates a new [FirestoreOperation].
  FirestoreOperation({
    required this.id,
    required this.action,
    required this.path,
    required this.data,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Converts operation to a serializable map.
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'action': action,
      'path': path,
      'data': data,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  /// Creates a [FirestoreOperation] from a map.
  factory FirestoreOperation.fromMap(Map<String, dynamic> map) {
    return FirestoreOperation(
      id: map['id'] as String? ?? '',
      action: map['action'] as String? ?? 'update',
      path: map['path'] as String? ?? '',
      data: Map<String, dynamic>.from(map['data'] as Map? ?? {}),
      timestamp: map['timestamp'] != null
          ? DateTime.parse(map['timestamp'] as String)
          : DateTime.now(),
    );
  }
}

/// Realises: [UC-03/FirestoreOfflineQueue]
/// Offline queue implementation for batching and reconciling Firestore operations.
///
/// Stores operations performed while offline and flushes/reconciles them with the
/// remote Firestore backend when connectivity is restored.
class FirestoreOfflineQueue {
  final List<FirestoreOperation> _queue = [];

  /// Returns an unmodifiable list of current queued operations.
  List<FirestoreOperation> get pendingOperations => List.unmodifiable(_queue);

  /// Number of operations currently pending in the queue.
  int get queueLength => _queue.length;

  /// Returns `true` if the queue contains no pending operations.
  bool get isEmpty => _queue.isEmpty;

  /// Enqueues a new operation to be processed when online.
  ///
  /// Can accept either a [FirestoreOperation] object or a raw [Map<String, dynamic>].
  void enqueueOperation(dynamic operation) {
    if (operation is FirestoreOperation) {
      _queue.add(operation);
    } else if (operation is Map<String, dynamic>) {
      _queue.add(FirestoreOperation.fromMap(operation));
    } else {
      throw ArgumentError('Operation must be a FirestoreOperation or Map<String, dynamic>');
    }
  }

  /// Reconciles and flushes all enqueued offline operations.
  ///
  /// Accepts an optional custom handler function [executor]. If provided, each
  /// operation is passed to [executor]. If [executor] returns `true` (or succeeds),
  /// the operation is removed from the queue. Returns the number of successfully reconciled operations.
  Future<int> reconcileQueue({
    Future<bool> Function(FirestoreOperation op)? executor,
  }) async {
    if (_queue.isEmpty) return 0;

    int reconciledCount = 0;
    final List<FirestoreOperation> remaining = [];

    for (final op in _queue) {
      bool success = true;
      if (executor != null) {
        try {
          success = await executor(op);
        } catch (_) {
          success = false;
        }
      }
      if (success) {
        reconciledCount++;
      } else {
        remaining.add(op);
      }
    }

    _queue.clear();
    _queue.addAll(remaining);

    return reconciledCount;
  }

  /// Clears all pending operations from the queue.
  void clearQueue() {
    _queue.clear();
  }
}
