import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:app_flutter/data/seeds/domain_seed_strategy.dart';

/// Realises: [Feat-000/DomainSeedStrategy]
/// Mock batch tracker that records batch size metrics.
class TrackingBatch implements Batch {
  final Batch _delegate;
  int currentOperations = 0;
  int peakBatchSize = 0;
  int totalOperationsSubmitted = 0;
  int commitCount = 0;

  TrackingBatch(this._delegate);

  void _recordOp() {
    currentOperations++;
    totalOperationsSubmitted++;
    if (currentOperations > peakBatchSize) {
      peakBatchSize = currentOperations;
    }
  }

  @override
  int get length => _delegate.length;

  @override
  Future<List<Object?>> apply({bool? noResult, bool? continueOnError}) {
    return _delegate.apply(noResult: noResult, continueOnError: continueOnError);
  }

  @override
  void insert(String table, Map<String, Object?> values,
      {String? nullColumnHack, ConflictAlgorithm? conflictAlgorithm}) {
    _recordOp();
    _delegate.insert(table, values,
        nullColumnHack: nullColumnHack, conflictAlgorithm: conflictAlgorithm);
  }

  @override
  void update(String table, Map<String, Object?> values,
      {String? where, List<Object?>? whereArgs, ConflictAlgorithm? conflictAlgorithm}) {
    _recordOp();
    _delegate.update(table, values,
        where: where, whereArgs: whereArgs, conflictAlgorithm: conflictAlgorithm);
  }

  @override
  void delete(String table, {String? where, List<Object?>? whereArgs}) {
    _recordOp();
    _delegate.delete(table, where: where, whereArgs: whereArgs);
  }

  @override
  void execute(String sql, [List<Object?>? arguments]) {
    _recordOp();
    _delegate.execute(sql, arguments);
  }

  @override
  void rawInsert(String sql, [List<Object?>? arguments]) {
    _recordOp();
    _delegate.rawInsert(sql, arguments);
  }

  @override
  void rawUpdate(String sql, [List<Object?>? arguments]) {
    _recordOp();
    _delegate.rawUpdate(sql, arguments);
  }

  @override
  void rawDelete(String sql, [List<Object?>? arguments]) {
    _recordOp();
    _delegate.rawDelete(sql, arguments);
  }

  @override
  void query(String table,
      {bool? distinct,
      List<String>? columns,
      String? where,
      List<Object?>? whereArgs,
      String? groupBy,
      String? having,
      String? orderBy,
      int? limit,
      int? offset}) {
    _recordOp();
    _delegate.query(table,
        distinct: distinct,
        columns: columns,
        where: where,
        whereArgs: whereArgs,
        groupBy: groupBy,
        having: having,
        orderBy: orderBy,
        limit: limit,
        offset: offset);
  }

  @override
  void rawQuery(String sql, [List<Object?>? arguments]) {
    _recordOp();
    _delegate.rawQuery(sql, arguments);
  }

  @override
  Future<List<Object?>> commit({
    bool? exclusive,
    bool? noResult,
    bool? continueOnError,
  }) async {
    commitCount++;
    final res = await _delegate.commit(
      exclusive: exclusive,
      noResult: noResult,
      continueOnError: continueOnError,
    );
    currentOperations = 0;
    return res;
  }
}

/// Realises: [Feat-000/DomainSeedStrategy]
/// Mock database tracker that records batches and commit metrics.
class TrackingDatabase implements Database {
  final Database _realDb;
  final List<TrackingBatch> createdBatches = [];

  TrackingDatabase(this._realDb);

  int get totalCommitCount => createdBatches.fold(0, (sum, b) => sum + b.commitCount);
  int get totalOperationsSubmitted => createdBatches.fold(0, (sum, b) => sum + b.totalOperationsSubmitted);
  int get peakBatchSize => createdBatches.fold(0, (max, b) => b.peakBatchSize > max ? b.peakBatchSize : max);

  @override
  Future<T> transaction<T>(Future<T> Function(Transaction txn) action, {bool? exclusive}) {
    return _realDb.transaction(action, exclusive: exclusive);
  }

  @override
  Batch batch() {
    final b = TrackingBatch(_realDb.batch());
    createdBatches.add(b);
    return b;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    return reflect(invocation);
  }

  dynamic reflect(Invocation invocation) {
    if (invocation.memberName == #execute) {
      return _realDb.execute(
        invocation.positionalArguments[0] as String,
        invocation.positionalArguments.length > 1
            ? invocation.positionalArguments[1] as List<Object?>?
            : null,
      );
    }
    if (invocation.memberName == #rawQuery) {
      return _realDb.rawQuery(
        invocation.positionalArguments[0] as String,
        invocation.positionalArguments.length > 1
            ? invocation.positionalArguments[1] as List<Object?>?
            : null,
      );
    }
    if (invocation.memberName == #close) {
      return _realDb.close();
    }
    throw UnimplementedError('Unhandled method on TrackingDatabase: ${invocation.memberName}');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  group('DomainSeedStrategy Reproduction Benchmark (#351)', () {
    test('measures batch operation accumulation and commit behavior', () async {
      final realDb = await openDatabase(inMemoryDatabasePath, version: 1, onCreate: (db, version) async {
        await db.execute('CREATE TABLE type_definitions (type_name TEXT PRIMARY KEY, display_name TEXT, icon_name TEXT);');
        await db.execute('CREATE TABLE type_attributes (type_name TEXT, attr_key TEXT, label TEXT, attr_type TEXT, section_label TEXT, section_order INTEGER, is_required INTEGER);');
        await db.execute('CREATE TABLE type_relations (parent_type_name TEXT, relation_name TEXT, child_type_name TEXT, child_label TEXT);');
        await db.execute('CREATE TABLE properties (node_id TEXT PRIMARY KEY, parent_node_id TEXT, data_json TEXT);');
        await db.execute('CREATE TABLE instances (id TEXT PRIMARY KEY, parent_node_id TEXT, type_name TEXT, data_json TEXT);');
      });

      final trackingDb = TrackingDatabase(realDb);
      final strategy = DomainSeedStrategy();

      final stopwatch = Stopwatch()..start();
      await strategy.seed(trackingDb);
      stopwatch.stop();

      print('=== REPRODUCTION SYMPTOM REPORT (#351) ===');
      print('Total seed execution time: ${stopwatch.elapsedMilliseconds} ms');
      print('Total batch commit calls: ${trackingDb.totalCommitCount}');
      print('Total operations submitted: ${trackingDb.totalOperationsSubmitted}');
      print('Peak batch operation accumulation: ${trackingDb.peakBatchSize}');

      // Assertions verifying issue #351 fix:
      // 1. Batch chunking executed multiple commits
      // 2. Peak batch operation accumulation <= 1,000 operations
      expect(trackingDb.totalCommitCount, greaterThan(1), reason: 'Statements committed in chunks');
      expect(trackingDb.peakBatchSize, lessThanOrEqualTo(1000), reason: 'Batch queue size kept <= 1,000 operations');

      await realDb.close();
    });
  });
}
