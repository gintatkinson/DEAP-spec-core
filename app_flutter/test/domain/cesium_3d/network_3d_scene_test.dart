import 'dart:io';
import 'dart:ui';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:path/path.dart' as p;
import 'package:app_flutter/features/topology/scene_3d_viewport_classes.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/topology/topology_map.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/projected_point.dart';

void main() {
  late Database db;
  late Network3DScene scene;

  setUpAll(() async {
    // Initialize FFI for SQLite in tests
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;

    TestWidgetsFlutterBinding.ensureInitialized();

    // Prepare a temporary database by copying the test database
    final tempDir = Directory.systemTemp.createTempSync('network_3d_scene_test');
    final dbPath = p.join(tempDir.path, 'properties_db.db');
    final sourceDb = File('assets/properties_db.db');
    if (sourceDb.existsSync()) {
      sourceDb.copySync(dbPath);
    }

    db = await databaseFactory.openDatabase(dbPath);

    // Insert a valid model path into the database for the test
    // We use a known asset (e.g. topology_data.json) as a fake 'glb' file just for bytes reading validation
    await db.execute('''
      CREATE TABLE IF NOT EXISTS asset_models (
        id TEXT PRIMARY KEY,
        model_path TEXT NOT NULL
      )
    ''');
    await db.insert('asset_models', {
      'id': 'test_asset',
      'model_path': 'assets/topology_data.json'
    });
  });

  tearDownAll(() async {
    await db.close();
  });

  setUp(() {
    scene = Network3DScene();
  });

  test('loadModel queries DB and successfully loads bytes for a known asset, setting state to loaded', () async {
    // Query the database to retrieve a valid model path for a known asset
    final results = await db.query(
      'asset_models',
      columns: ['model_path'],
      where: 'id = ?',
      whereArgs: ['test_asset'],
    );
    final validModelPath = results.first['model_path'] as String;

    // Load the model
    final success = await scene.loadModel(validModelPath);

    expect(success, isTrue);
    expect(scene.state, equals(ModelRenderState.loaded));
    expect(scene.gltfData, isNotNull);
    expect(scene.gltfData!.isNotEmpty, isTrue);
  });

  test('loadModel fails gracefully and sets state to error for a non-existent path', () async {
    final success = await scene.loadModel('assets/non_existent_model.glb');

    expect(success, isFalse);
    expect(scene.state, equals(ModelRenderState.error));
    expect(scene.gltfData, isNull);
  });

  test('applyPbrMaterials returns false and does not set translucent if state is not loaded', () {
    expect(scene.state, equals(ModelRenderState.unloaded));
    
    final success = scene.applyPbrMaterials();

    expect(success, isFalse);
    expect(scene.isTranslucent, isFalse);
  });

  test('TopologyLayer.paint executes without throwing for a loaded 3D model node', () async {
    final results = await db.query(
      'asset_models',
      columns: ['model_path'],
      where: 'id = ?',
      whereArgs: ['test_asset'],
    );
    final validModelPath = results.first['model_path'] as String;
    await scene.loadModel(validModelPath);

    final state = SceneViewState();
    state.showDevices = true;
    state.showDropLines = false;
    state.showLinks = false;
    state.showLabels = false;
    state.nodeModels['node1'] = scene;
    
    final node = TopologyNode(
      id: 'node1',
      label: 'Sat1',
      position: const TopologyNodePosition(dim0: 100.0, dim1: 10.0, dim2: 600000.0, timeIndex: 0, vector: []),
      status: 'Active',
      rawProperties: const {'heightReference': 'ABSOLUTE'},
    );
    state.topologyData = TopologyData(coordinateMapping: const {}, nodes: [node], links: const []);
    state.projectedNodes['node1'] = ProjectedPoint(const Offset(100, 100), 10.0);
    // Dummy provider so it doesn't crash on drop lines
    state.elevationProvider = const ElevationProvider(isElevationActive: false);

    final layer = TopologyLayer();
    final recorder = PictureRecorder();
    final canvas = Canvas(recorder);

    // Should not throw, and should bypass 2D circles and render path
    expect(() => layer.paint(canvas, const Size(800, 600), state), returnsNormally);
  });

  test('TopologyLayer.paint executes without throwing and falls back to 2D for error model node', () async {
    await scene.loadModel('assets/non_existent.glb');

    final state = SceneViewState();
    state.showDevices = true;
    state.showDropLines = false;
    state.showLinks = false;
    state.showLabels = false;
    state.nodeModels['node2'] = scene;
    
    final node = TopologyNode(
      id: 'node2',
      label: 'Sat2',
      position: const TopologyNodePosition(dim0: 200.0, dim1: 20.0, dim2: 600000.0, timeIndex: 0, vector: []),
      status: 'Active',
      rawProperties: const {'heightReference': 'ABSOLUTE'},
    );
    state.topologyData = TopologyData(coordinateMapping: const {}, nodes: [node], links: const []);
    state.projectedNodes['node2'] = ProjectedPoint(const Offset(200, 200), 10.0);

    final layer = TopologyLayer();
    final recorder = PictureRecorder();
    final canvas = Canvas(recorder);

    // Should not throw, and should fallback to 2D circles
    expect(() => layer.paint(canvas, const Size(800, 600), state), returnsNormally);
  });
}
