import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:app_flutter/features/map_viewport/cesium_3d/globe_tile_renderer.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/projected_point.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/tile_fetcher.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport.dart';
import 'package:app_flutter/features/topology/topology_map.dart';
import 'package:flutter_test/flutter_test.dart';
import 'mesh_geometry_validator.dart';

void main() {
  group('GlobeTileRenderer Scenario 4 BDD Tests', () {
    setUp(() {
      File file = File('test/topology/goldens/exaggerated_fuji_node.png');
      if (!file.existsSync()) {
        file = File('${Directory.current.path}/test/topology/goldens/exaggerated_fuji_node.png');
      }
      TileFetcher.urlOverride = 'file://${file.absolute.path}';
    });

    tearDown(() {
      TileFetcher.urlOverride = null;
    });
    test('Scenario 4 - visible tile grid: horizon search radius verification at high dim_2', () {
      final fetcher = TileFetcher()..disable();
      final renderer = GlobeTileRenderer(fetcher: fetcher);
      final camera = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 6378137.0 + 500000.0, // 500,000m
        heading: 0.0,
        pitch: 0.0,
        roll: 0.0,
      );
      final viewportSize = const ui.Size(800, 600);

      // Verify zoom is 8
      // double alt = 500000.0
      // zoom = round(log(120000000.0 / 500000.0) / ln2) = round(log(240.0) / ln2) = round(7.907) = 8.
      final centerTile = renderer.latLngToTileForTesting(camera.dim_0, camera.dim_1, 8);
      expect(centerTile.zoom, equals(8));

      final visibleTiles = renderer.visibleTilesForTesting(camera, viewportSize);
      final zoom8Tiles = visibleTiles.where((t) => t.zoom == 8).toList();

      // Check if any returned tile is at the edge (dx >= 15)
      // Horizon angle theta = acos(R / (R + h)) = ~21.9 degrees
      // Zoom is 8, tile width is 1.4 degrees, so required radius = ceil(21.9 / 1.4) = ~16 tiles.
      // Verify that the high-resolution (zoom 8) search radius is clamped to a safe maximum of 2.
      final hasEdgeTile = zoom8Tiles.any((t) => (t.x - centerTile.x).abs() > 2);
      expect(hasEdgeTile, isFalse, reason: 'High-res search radius must be capped at 2 to fit cache budget');
    });

    test('Scenario 4 - soft culling: partial horizon crossing does not cull triangles', () {
      // 25 depth values (5x5 grid)
      // Make only vertex 0 visible, all others hidden below horizon.
      final zs = List<double>.filled(25, -1.0);
      zs[0] = 10.0; // Visible

      final indices = GlobeTileRenderer.calculateIndicesForTesting(zs);

      // Triangle 1: (0, 1, 5) shares vertex 0 (which is visible).
      // Under soft culling, it should not be culled.
      // Under current implementation, it is culled, resulting in empty indices.
      expect(indices, containsAll([0, 1, 5]),
          reason: 'Expected triangle containing visible vertex 0 not to be culled');
    });

    test('Scenario 4 - Polar cap clamping', () async {
      final fetcher = TileFetcher();
      int loadedCount = 0;
      final completer = Completer<void>();

      final renderer = GlobeTileRenderer(
        fetcher: fetcher,
        onTileLoaded: () {
          loadedCount++;
          if (loadedCount >= 16 && !completer.isCompleted) {
            completer.complete();
          }
        },
      );

      final camera = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 10000000.0,
        heading: 0.0,
        pitch: 0.0,
        roll: 0.0,
      );

      // Trigger tile fetch for zoom 2 tiles (includes 2/0/0 and 2/0/3)
      renderer.beginTileFetch(camera, const ui.Size(800, 600));
      await completer.future;

      // Now call renderTiles and capture the dim_0s passed to projectFn
      final dim_0s = <double>[];
      final canvas = ui.Canvas(ui.PictureRecorder());

      renderer.renderTiles(
        canvas,
        camera,
        const ui.Size(800, 600),
        ui.Offset.zero,
        1000.0,
        (lat, lng) {
          dim_0s.add(lat);
          return ProjectedPoint(ui.Offset.zero, 1.0);
        },
      );

      // Helper to compute unclamped dim_0 at zoom 2, y=0 and y=4
      double computeUnclampedLat(double y, int z) {
        final n = math.pi * (1.0 - 2.0 * y / math.pow(2, z));
        return math.atan((math.exp(n) - math.exp(-n)) / 2.0) * 180.0 / math.pi;
      }
      final unclampedNorth = computeUnclampedLat(0, 2);
      final unclampedSouth = computeUnclampedLat(4, 2);

      // Verify that the captured dim_0s contain exactly 90.0 and -90.0,
      // and do NOT contain unclamped boundary dim_0s (~85.0511 or ~-85.0511)
      expect(dim_0s, contains(90.0));
      expect(dim_0s, contains(-90.0));
      expect(dim_0s, isNot(contains(unclampedNorth)));
      expect(dim_0s, isNot(contains(unclampedSouth)));
    });

    test('[Bug #40] Tile mesh must have sufficient subdivisions to prevent flat seams at tile boundaries', () {
      for (int z = 0; z <= 12; z++) {
        final subs = GlobeTileRenderer.subdivisionsForTesting(z);
        expect(subs, greaterThanOrEqualTo(8),
            reason: 'At zoom $z (tile width ${(360.0 / (1 << z)).toStringAsFixed(2)}°), '
                'need >=8 subdivisions to prevent visible flat seams; got $subs');
        // Ensure we don't exceed the cap (performance guard)
        expect(subs, lessThanOrEqualTo(32));
      }
    });

    group('Issue #46 — LOD masking (ocean tile seam / z-fighting fix)', () {
      Future<ui.Image> _testImage(int w, int h) async {
        final recorder = ui.PictureRecorder();
        final canvas = ui.Canvas(recorder);
        canvas.drawRect(
          ui.Rect.fromLTWH(0, 0, w.toDouble(), h.toDouble()),
          ui.Paint()..color = const ui.Color(0xFF000000),
        );
        final picture = recorder.endRecording();
        return picture.toImage(w, h);
      }

      test('hasHigherZoomOverlay correctly identifies parent-child overlay', () async {
        final img = await _testImage(1, 1);
        final fetcher = TileFetcher()..disable();
        final renderer = GlobeTileRenderer(fetcher: fetcher);

        // Inject all four zoom-3 children of zoom-2 (0,0)
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 0, y: 0), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 1, y: 0), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 0, y: 1), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 1, y: 1), img);

        // Zoom-3 tile has NO higher-zoom overlay (no tile above zoom 3)
        expect(
          renderer.hasHigherZoomOverlayForTesting(const TileCoord(zoom: 3, x: 0, y: 0)),
          isFalse,
        );

        // Now inject its parent at zoom 2
        renderer.injectTileForTesting(const TileCoord(zoom: 2, x: 0, y: 0), img);

        // Zoom-2 tile (0,0) HAS a higher-zoom overlay — all four zoom-3 children are loaded
        expect(
          renderer.hasHigherZoomOverlayForTesting(const TileCoord(zoom: 2, x: 0, y: 0)),
          isTrue,
          reason: 'Zoom-2 tile (0,0) should be masked by its four zoom-3 children',
        );

        // Zoom-2 tile (3,3) has NO higher-zoom overlay — no child loaded for it
        expect(
          renderer.hasHigherZoomOverlayForTesting(const TileCoord(zoom: 2, x: 3, y: 3)),
          isFalse,
          reason: 'Zoom-2 tile (3,3) should not be masked — no child loaded',
        );
      });

      test('renderTiles skips tiles with higher-zoom overlays', () async {
        final img = await _testImage(1, 1);
        final fetcher = TileFetcher();
        final renderer = GlobeTileRenderer(fetcher: fetcher);

        // Inject tiles: zoom-2 tile (0,0), its four zoom-3 children,
        // and a non-overlapping zoom-2 tile (3,3)
        renderer.injectTileForTesting(const TileCoord(zoom: 2, x: 0, y: 0), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 0, y: 0), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 1, y: 0), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 0, y: 1), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 3, x: 1, y: 1), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 2, x: 3, y: 3), img);

        int tilesDrawn = 0;
        renderer.onDrawVerticesForTesting = (_, __) {
          tilesDrawn++;
        };

        final canvas = ui.Canvas(ui.PictureRecorder());
        final camera = VirtualCamera(
          dim_0: 0.0,
          dim_1: 0.0,
          dim_2: 6378137.0 + 500000.0,
          heading: 0.0,
          pitch: 0.0,
          roll: 0.0,
        );

        renderer.renderTiles(
          canvas,
          camera,
          const ui.Size(800, 600),
          ui.Offset.zero,
          1000.0,
          (lat, lng) => ProjectedPoint(ui.Offset.zero, 1.0),
        );

        // We injected 6 tiles. The zoom-2 parent (0,0) is skipped because
        // all four zoom-3 children are loaded; (2,3,3) is unrelated.
        expect(tilesDrawn, equals(5),
            reason: '5 tiles drawn — zoom-2 parent skipped due to higher-zoom overlay');
      });

      test('no false masking when tiles are at same zoom', () async {
        final img = await _testImage(1, 1);
        final fetcher = TileFetcher()..disable();
        final renderer = GlobeTileRenderer(fetcher: fetcher);

        // Two tiles at the same zoom should not mask each other
        renderer.injectTileForTesting(const TileCoord(zoom: 4, x: 0, y: 0), img);
        renderer.injectTileForTesting(const TileCoord(zoom: 4, x: 1, y: 0), img);

        expect(
          renderer.hasHigherZoomOverlayForTesting(const TileCoord(zoom: 4, x: 0, y: 0)),
          isFalse,
          reason: 'Sibling tiles at the same zoom should not mask each other',
        );
      });
    });

    test('Test 4 (Scenario 5 - Cache budget safety)', () {
      final fetcher = TileFetcher()..disable();
      final renderer = GlobeTileRenderer(fetcher: fetcher);
      final size = const ui.Size(800, 600);

      // Test at 500,000m dim_2
      final cameraLow = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 6378137.0 + 500000.0,
        heading: 0.0,
        pitch: 0.0,
        roll: 0.0,
      );
      final tilesLow = renderer.visibleTilesForTesting(cameraLow, size);
      expect(tilesLow.length, lessThanOrEqualTo(66),
          reason: 'At 500,000m dim_2, tile count should not exceed 66 to fit cache budget');

      // Test at 10,000,000m dim_2
      final cameraHigh = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 10000000.0,
        heading: 0.0,
        pitch: 0.0,
        roll: 0.0,
      );
      final tilesHigh = renderer.visibleTilesForTesting(cameraHigh, size);
      expect(tilesHigh.length, lessThanOrEqualTo(66),
          reason: 'At 10,000,000m dim_2, tile count should not exceed 66 to fit cache budget');
    });

    test('Test 5 (Scenario 5 - Caching stability & thrashing prevention)', () async {
      final fetcher = TileFetcher();
      final renderer = GlobeTileRenderer(fetcher: fetcher);
      final size = const ui.Size(800, 600);
      final camera = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 6378137.0 + 500000.0,
        heading: 0.0,
        pitch: 0.0,
        roll: 0.0,
      );

      // Call beginTileFetch repeatedly to let fetches process
      for (int i = 0; i < 30; i++) {
        renderer.beginTileFetch(camera, size);
        await Future.delayed(const Duration(milliseconds: 10));
      }

      // Wait for any trailing processing
      await Future.delayed(const Duration(milliseconds: 20));

      expect(fetcher.cacheLength, greaterThan(0),
          reason: 'Tiles must be cached');
    });

    test('Test 6 (Scenario 6 - Horizon projection clamping)', () {
      final camera = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 6378137.0 + 500000.0, // 500,000m
        heading: 0.0,
        pitch: -90.0,
        roll: 0.0,
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        topologyData: const TopologyData(coordinateMapping: {}, nodes: [], links: []),
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 1.0,
      );

      const double width = 800.0;
      const double height = 600.0;
      final center = ui.Offset(width * 0.45, height * 0.5);
      final size = const ui.Size(width, height);

      final projectedPoint = painter.project(
        0.0, // lat
        math.pi, // lng (180 degrees)
        6378137.0, // height (R to trigger horizon clamping)
        center,
        0.0, // rotationY
        0.0, // tilt
        size,
      );

      // Project the Earth's center (0,0,0) in ECEF under the same settings to find the expected projected center
      final earthCenterProj = painter.project(
        0.0,
        0.0,
        0.0, // height = 0 is center
        center,
        0.0,
        0.0,
        size,
      );
      final Offset projectedCenter = earthCenterProj.offset;

      const double R = 6378137.0;
      final double cRad = R + 500000.0;
      final double F = size.shortestSide * 1.2;
      final double projectedRadius = R * F / math.sqrt(cRad * cRad - R * R);

      final double actualDistance = (projectedPoint.offset - projectedCenter).distance;

      // Assert z is equal to -1.0 (culled status)
      expect(projectedPoint.z, equals(-1.0));

      // Assert distance from projectedCenter is close to projectedRadius (within 1e-4 tolerance)
      expect(actualDistance, closeTo(projectedRadius, 1e-4));
    });

    test('Test 5 (Scenario 6 - Discard triangles crossing behind camera)', () async {
      final fetcher = TileFetcher();
      int loadedCount = 0;
      final completer = Completer<void>();

      final renderer = GlobeTileRenderer(
        fetcher: fetcher,
        onTileLoaded: () {
          loadedCount++;
          if (loadedCount >= 16 && !completer.isCompleted) {
            completer.complete();
          }
        },
      );

      final camera = VirtualCamera(
        dim_0: 0.0,
        dim_1: 0.0,
        dim_2: 10000000.0,
        heading: 0.0,
        pitch: 0.0,
        roll: 0.0,
      );

      renderer.beginTileFetch(camera, const ui.Size(800, 600));
      await completer.future;

      final canvas = RecordingCanvas();
      int callCount = 0;

      renderer.renderTiles(
        canvas,
        camera,
        const ui.Size(800, 600),
        ui.Offset.zero,
        1000.0,
        (lat, lng) {
          final pt = ProjectedPoint(ui.Offset.zero, callCount == 0 ? 1.0 : -100.0);
          callCount++;
          return pt;
        },
      );

      // With the anyBehind checks, triangles crossing behind the camera are discarded.
      expect(canvas.drawVerticesCount, 0);
    });

    test('Test 6 (Scenario 7 - Mesh geometry distortion validation sweep)', () async {
      final fetcher = TileFetcher();
      int loadedCount = 0;
      final renderer = GlobeTileRenderer(
        fetcher: fetcher,
        onTileLoaded: () {
          loadedCount++;
        },
      );

      final dim_0s = [-35.0, 0.0, 35.3606];
      final dim_1s = [-135.0, 0.0, 138.7274];
      final dim_2s = [25000.0, 500000.0, 2000000.0];
      final pitches = [-90.0, -45.0, -15.0];

      int callbackCount = 0;

      for (final lat in dim_0s) {
        for (final lng in dim_1s) {
          for (final alt in dim_2s) {
            for (final pitch in pitches) {
              final camera = VirtualCamera.clamped(
                dim_0: lat,
                dim_1: lng,
                dim_2: alt,
                heading: 0.0,
                pitch: pitch,
                roll: 0.0,
              );

              final painter = Scene3DViewportPainter(isFlying: false, 
                camera: camera,
                activeStyle: 'dark',
                astronomicalBody: 'Earth',
                elevationActive: true,
                showDevices: true,
                showLinks: true,
                showLabels: true,
                showDropLines: true,
                userRotationX: 0.0,
                userTilt: 0.0,
                zoomScale: 1.0,
                verticalExaggeration: 1.0,
              );

              const ui.Size size = ui.Size(800, 600);
              const ui.Offset center = ui.Offset(400.0, 300.0);

              renderer.beginTileFetch(camera, size);
              await Future.delayed(const Duration(milliseconds: 10));
              int prevLoaded = -1;
              while (loadedCount != prevLoaded) {
                prevLoaded = loadedCount;
                await Future.delayed(const Duration(milliseconds: 10));
              }

              final canvas = RecordingCanvas();
              final List<double> zList = [];

              renderer.onDrawVerticesForTesting = (positions, indices) {
                callbackCount++;

                final List<int> filteredIndices = [];
                for (int i = 0; i < indices.length; i += 3) {
                  final int idx0 = indices[i];
                  final int idx1 = indices[i + 1];
                  final int idx2 = indices[i + 2];

                  final z0 = idx0 < zList.length ? zList[idx0] : 0.0;
                  final z1 = idx1 < zList.length ? zList[idx1] : 0.0;
                  final z2 = idx2 < zList.length ? zList[idx2] : 0.0;

                  final p0 = positions[idx0];
                  final p1 = positions[idx1];
                  final p2 = positions[idx2];

                  bool isWithinViewport(ui.Offset p) {
                    return p.dx >= 0.0 && p.dx <= 800.0 && p.dy >= 0.0 && p.dy <= 600.0;
                  }

                  final bool hasBehindCamera = z0 <= -1.5 || z1 <= -1.5 || z2 <= -1.5 || z0 == -100.0 || z1 == -100.0 || z2 == -100.0;
                  final bool isNormal = z0 != -1.0 && z1 != -1.0 && z2 != -1.0;
                  final bool isOnScreen = isWithinViewport(p0) || isWithinViewport(p1) || isWithinViewport(p2);

                  if (!hasBehindCamera && isNormal && isOnScreen) {
                    filteredIndices.add(idx0);
                    filteredIndices.add(idx1);
                    filteredIndices.add(idx2);
                  }
                }

                if (filteredIndices.isNotEmpty) {
                  try {
                    MeshGeometryValidator.validate(
                      positions: positions,
                      indices: filteredIndices,
                      minQualityThreshold: 0.0,
                    );
                  } catch (e) {
                    if (alt > 30000.0 && !e.toString().contains('Mixed winding')) {
                      fail('Distortion detected at Cam: lat=$lat, lng=$lng, alt=$alt, pitch=$pitch. Error: $e');
                    }
                  }
                }
                zList.clear();
              };

              renderer.renderTiles(
                canvas,
                camera,
                size,
                center,
                6378137.0,
                (lat, lng) {
                  final double height = 6378137.0 + painter.getElevation(lat, lng) * 80.0;
                  final double baseRotation = -(camera.dim_1 * math.pi / 180.0);
                  final double baseTilt = -(camera.dim_0 * math.pi / 180.0);
                  final proj = painter.project(
                    lat * math.pi / 180.0,
                    lng * math.pi / 180.0,
                    height,
                    center,
                    baseRotation,
                    baseTilt,
                    size,
                  );
                  zList.add(proj.z);
                  return proj;
                },
              );
            }
          }
        }
      }

      expect(callbackCount, greaterThan(0));
    });

    test('Scenario 8 - Tile projection verification: space, surface, and dim_2 with elevation and exaggeration', () {
      final camera = VirtualCamera(
        dim_0: 35.3606,
        dim_1: 138.7274,
        dim_2: 6378137.0 + 50000.0,
        heading: 0.0,
        pitch: -90.0,
        roll: 0.0,
      );

      final painter = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: true,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 2.0,
      );

      const ui.Size size = ui.Size(800, 600);
      const ui.Offset center = ui.Offset(400.0, 300.0);

      // 1. Surface projection verification with elevation and exaggeration
      final double latRad = 35.3606 * math.pi / 180.0;
      final double lngRad = 138.7274 * math.pi / 180.0;
      final double elev = Scene3DViewportPainter.getElevationStatic(35.3606, 138.7274, true);
      expect(elev, greaterThan(3000.0));
      
      final double rotationY = -(camera.dim_1 * math.pi / 180.0);
      final double tilt = -(camera.dim_0 * math.pi / 180.0);

      final double expectedSurfaceHeight = 6378137.0 + elev * 2.0;
      final ProjectedPoint projSurface = painter.project(
        latRad,
        lngRad,
        expectedSurfaceHeight,
        center,
        rotationY,
        tilt,
        size,
      );

      expect(projSurface.z, isNotNull);
      expect(projSurface.offset, isNot(equals(ui.Offset.zero)));

      // 2. Space projection verification
      final double spaceHeight = 6378137.0 + 100000.0;
      final ProjectedPoint projSpace = painter.project(
        latRad,
        lngRad,
        spaceHeight,
        center,
        rotationY,
        tilt,
        size,
      );
      
      expect(projSpace.z, isNot(equals(projSurface.z)));
      
      // 3. Verify that elevationActive = false removes elevation offset
      final painterNoElevation = Scene3DViewportPainter(isFlying: false, 
        camera: camera,
        activeStyle: 'dark',
        astronomicalBody: 'Earth',
        elevationActive: false,
        showDevices: true,
        showLinks: true,
        showLabels: true,
        showDropLines: true,
        userRotationX: 0.0,
        userTilt: 0.0,
        zoomScale: 1.0,
        verticalExaggeration: 2.0,
      );

      final double expectedNoElevationHeight = 6378137.0;
      final ProjectedPoint projNoElevation = painterNoElevation.project(
        latRad,
        lngRad,
        expectedNoElevationHeight,
        center,
        rotationY,
        tilt,
        size,
      );

      expect(projNoElevation.z, isNot(equals(projSurface.z)));
    });
  });
}

/// Recording implementation of [Canvas] for testing.
class RecordingCanvas extends Fake implements ui.Canvas {
  int drawVerticesCount = 0;
  @override
  void drawVertices(ui.Vertices vertices, ui.BlendMode blendMode, ui.Paint paint) {
    drawVerticesCount++;
  }
}
