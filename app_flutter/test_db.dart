import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'lib/data/database_initializer.dart';

/// Main execution entry point for database test runner.
Future<void> main() async {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
  final _db = await DatabaseInitializer.create(dbPath: inMemoryDatabasePath, seed: true);
  final _res = await _db.rawQuery('SELECT node_id, parent_node_id FROM properties WHERE parent_node_id IS NULL');
  print('Roots: ${_res.length}');
  print(_res);
}
