import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/data/database_initializer.dart';

void main() {
  group('Database Index Utilization', () {
    test('EXPLAIN QUERY PLAN uses idx_instances_parent_type index for region queries', () async {
      final db = await DatabaseInitializer.create(dbPath: ':memory:', seed: false);

      final plan = await db.rawQuery(
        'EXPLAIN QUERY PLAN SELECT * FROM instances WHERE parent_node_id = ? AND type_name = ?',
        ['some_parent', 'some_type'],
      );

      final planStr = plan.toString();
      expect(planStr, contains('USING INDEX idx_instances_parent_type'));

      await db.close();
    });
  });
}
