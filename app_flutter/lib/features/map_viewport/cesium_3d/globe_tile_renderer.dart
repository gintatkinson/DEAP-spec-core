import 'dart:math' as math;
import 'dart:typed_data';

import 'dart:ui' as ui;

import 'package:meta/meta.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/projected_point.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/tile_fetcher.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';

/// A tile coordinate in the Web Mercator tiling scheme.
///
/// [zoom] is the zoom level (0–12), [x] is the column, and [y] is the row
/// (0 at the top / north).
///
/// Realises: [Feat-10/TileCoord]
class TileCoord {
  /// The zoom level for this tile coordinate.
  final int zoom;

  /// The column index (0 = 180&deg; W, increases eastward).
  final int x;

  /// The row index (0 = 85.05&deg; N, increases southward).
  final int y;

  /// Creates a tile coordinate with the given [zoom], [x], and [y].
  const TileCoord({required this.zoom, required this.x, required this.y});

  /// A string key suitable for use in maps and sets.
  String get key => '$zoom/$x/$y';
}

/// Renders raster map-imagery tiles onto a 3-D globe canvas.
///
/// Tiles are fetched asynchronously via [TileFetcher] and decoded to
/// [ui.Image] instances. Only tiles whose corners project to the front
/// hemisphere are drawn. The active imagery [ImageryProvider] can be
/// changed at any time, which clears the local image cache and triggers
/// fresh fetches.
///
/// Realises: [Feat-10/GlobeTileRenderer]
class GlobeTileRenderer {
  final TileFetcher _fetcher;
  ImageryProvider _activeProvider;
  /// Member documentation.
  final ui.VoidCallback? onTileLoaded;

  /// Member documentation.
  @visibleForTesting
  void Function(List<ui.Offset> positions, List<int> indices)? onDrawVerticesForTesting;

  /// Decoded tile images keyed by "[zoom]/[x]/[y]". Limited to 128 entries.
  final Map<String, ui.Image> _loadedImages = {};

  /// Set of tile keys for which an HTTP fetch is currently in-flight.
  final Set<String> _pendingFetches = {};

  bool _disposed = false;
  int _activeFetchCount = 0;
  static const int _maxConcurrentFetches = 16;
  List<MapEntry<String, ui.Image>>? _cachedSortedEntries;
  int _cachedSortedEntriesLength = -1;

  /// Creates a renderer that will fetch tiles via [fetcher] and initially
  /// use [initialProvider] as the imagery source.
  GlobeTileRenderer({
    required TileFetcher fetcher,
    ImageryProvider initialProvider = ImageryProvider.cartoDark,
    this.onTileLoaded,
  })  : _fetcher = fetcher,
        _activeProvider = initialProvider;

  /// Whether the underlying [TileFetcher] is enabled.
  bool get isEnabled => _fetcher.isEnabled();

  /// Member documentation.
  @visibleForTesting
  int get loadedImagesCount => _loadedImages.length;

  /// Returns true if a higher-zoom tile is loaded whose geographic bounds
  /// fall within [tile]'s area.
  @visibleForTesting
  bool hasHigherZoomOverlayForTesting(TileCoord tile) {
    return _hasHigherZoomOverlay(tile);
  }

  /// Member documentation.
  @visibleForTesting
  void injectTileForTesting(TileCoord coord, ui.Image image) {
    _loadedImages[coord.key] = image;
  }

  /// Switches to [provider] and clears all locally cached images and
  /// pending fetches so that new imagery is loaded.
  void setProvider(ImageryProvider provider) {
    if (_activeProvider == provider) return;
    _activeProvider = provider;
    for (final img in _loadedImages.values) {
      img.dispose();
    }
    _loadedImages.clear();
    _pendingFetches.clear();
    _fetcher.clearCache();
    _cachedSortedEntries = null;
    _cachedSortedEntriesLength = -1;
  }

  /// Disposes all loaded tile images and clears the cache.
  void dispose() {
    _disposed = true;
    for (final img in _loadedImages.values) {
      img.dispose();
    }
    _loadedImages.clear();
    _cachedSortedEntries = null;
    _cachedSortedEntriesLength = -1;
  }

  /// Converts degrees to radians.
  double _rad(double deg) => deg * math.pi / 180.0;

  // ---------------------------------------------------------------------------
  // Zoom computation
  // ---------------------------------------------------------------------------

  /// Derives a zoom level from the camera [dim_2] (meters) and the
  /// [viewportWidth] (logical pixels).
  ///
  /// Clamped to the range 0–12. Small altitudes (close to the sphere)
  /// produce higher zoom values; high altitudes produce lower values.
  int _zoomForAltitude(double dim_2, double viewportWidth) {
    double v_dim_2 = dim_2;
    if (v_dim_2 <= 0) v_dim_2 = 100;
    final zoom =
        (math.log(120000000.0 / v_dim_2) / math.ln2).round();
    return zoom.clamp(0, 12);
  }

  // ---------------------------------------------------------------------------
  // Tile coordinate math (Web Mercator)
  // ---------------------------------------------------------------------------

  /// Converts dim_0/dim_1 (degrees) to a tile coordinate at the
  /// given [zoom] level.
  TileCoord _latLngToTile(double dim_0, double lng, int zoom) {
    final clampedLat = dim_0.clamp(-85.0511, 85.0511);
    final n = math.pow(2, zoom).toInt();
    final x = ((lng + 180) / 360 * n).floor();
    final latRad = _rad(clampedLat);
    final y =
        ((1 - math.log(math.tan(latRad) + 1 / math.cos(latRad)) / math.pi) /
                2 *
                n)
            .floor();
    return TileCoord(
        zoom: zoom, x: x.clamp(0, n - 1), y: y.clamp(0, n - 1));
  }

  /// Longitude of the *western* edge of tile column [x] at zoom [z].
  double _tile2lon(int x, int z) =>
      x / math.pow(2, z) * 360.0 - 180.0;

  /// Latitude of the *northern* edge of tile row [y] at zoom [z].
  double _tile2lat(double y, int z) {
    final n = math.pi * (1.0 - 2.0 * y / math.pow(2, z));
    return math.atan((math.exp(n) - math.exp(-n)) / 2.0) * 180.0 / math.pi;
  }

  // ---------------------------------------------------------------------------
  // Visible-tile computation
  // ---------------------------------------------------------------------------

  /// Returns the set of tile coordinates that cover the visible hemisphere
  /// from the current [camera] perspective.
  ///
  /// The centre tile is derived from the camera's dim_0/lng. A 4&times;4 grid
  /// (16 tiles) is then generated around it, clamped to valid Web Mercator
  /// bounds.
  List<TileCoord> _visibleTiles(VirtualCamera camera, ui.Size viewportSize, {bool isFlying = false}) {
    final double R = Ellipsoid.wgs84EquatorialRadius;
    final double relativeAlt = camera.dim_2 < R ? camera.dim_2 : camera.dim_2 - R;
    int zoom = _zoomForAltitude(relativeAlt, viewportSize.width);
    if (isFlying && zoom > 4) {
      zoom = 4;
    }
    final center = _latLngToTile(camera.dim_0, camera.dim_1, zoom);
    final List<TileCoord> tiles = [];

    // Horizon angle theta = acos(R / (R + h)) where R = Ellipsoid.wgs84EquatorialRadius
    final double h = relativeAlt < 0.1 ? 0.1 : relativeAlt;
    final double theta = math.acos(R / (R + h));

    // Tier 1: Zoom 2 (global background coverage)
    for (int x = 0; x < 4; x++) {
      for (int y = 0; y < 4; y++) {
        tiles.add(TileCoord(zoom: 2, x: x, y: y));
      }
    }

    // Tier 2: Zoom Z - 2 (Mid-resolution wider background)
    final midZoom = zoom - 2;
    if (midZoom > 2) {
      final midCenter = _latLngToTile(camera.dim_0, camera.dim_1, midZoom);
      final midN = math.pow(2, midZoom).toInt();
      final double midTileWidth = 360.0 / math.pow(2, midZoom);
      final double thetaDeg = theta * 180.0 / math.pi;
      final int midRadius = (thetaDeg / midTileWidth).ceil().clamp(1, 2);
      for (int dx = -midRadius; dx <= midRadius; dx++) {
        for (int dy = -midRadius; dy <= midRadius; dy++) {
          final tx = (midCenter.x + dx).clamp(0, midN - 1);
          final ty = (midCenter.y + dy).clamp(0, midN - 1);
          tiles.add(TileCoord(zoom: midZoom, x: tx, y: ty));
        }
      }
    }

    // Tier 3: Zoom Z (High-resolution close-up)
    if (zoom > 2) {
      final n = math.pow(2, zoom).toInt();
      final double tileWidth = 360.0 / math.pow(2, zoom);
      final double thetaDeg = theta * 180.0 / math.pi;
      final int radius = (thetaDeg / tileWidth).ceil().clamp(1, 2);
      for (int dx = -radius; dx <= radius; dx++) {
        for (int dy = -radius; dy <= radius; dy++) {
          final tx = (center.x + dx).clamp(0, n - 1);
          final ty = (center.y + dy).clamp(0, n - 1);
          tiles.add(TileCoord(zoom: zoom, x: tx, y: ty));
        }
      }
    }

    return tiles;
  }

  // ---------------------------------------------------------------------------
  // Asynchronous tile fetching
  // ---------------------------------------------------------------------------

  /// Begins asynchronous fetching of all visible tiles for the given
  /// [camera] and [viewportSize].
  ///
  /// Tiles that are already loaded or whose fetch is already in-flight are
  /// skipped. Up to 16 concurrent fetches may be active at once.
  ///
  /// This method is safe to call on every frame — its work is bounded and
  /// it never blocks the UI thread.
  void beginTileFetch(VirtualCamera camera, ui.Size viewportSize, {bool isFlying = false}) {
    if (!_fetcher.isEnabled()) return;
    _fetchVisibleTiles(camera, viewportSize, isFlying: isFlying); // fire-and-forget
  }

  Future<void> _fetchVisibleTiles(
      VirtualCamera camera, ui.Size viewportSize, {bool isFlying = false}) async {
    final tiles = _visibleTiles(camera, viewportSize, isFlying: isFlying);

    final List<TileCoord> toFetch = [];
    for (final tile in tiles) {
      if (!_loadedImages.containsKey(tile.key) &&
          !_pendingFetches.contains(tile.key)) {
        toFetch.add(tile);
      }
    }

    if (toFetch.isEmpty) return;

    for (final tile in toFetch) {
      if (_activeFetchCount >= _maxConcurrentFetches) {
        break;
      }
      _fetchAndDecode(tile);
    }
  }

  Future<void> _fetchAndDecode(TileCoord tile) async {
    final providerAtStart = _activeProvider;
    _pendingFetches.add(tile.key);
    _activeFetchCount++;
    try {
      final data = await _fetcher.fetchTile(
          providerAtStart, tile.zoom, tile.x, tile.y);
      if (_disposed || _activeProvider != providerAtStart) {
        return;
      }
      if (data != null) {
        final codec = await ui.instantiateImageCodec(data);
        if (_disposed || _activeProvider != providerAtStart) {
          return;
        }
        final frame = await codec.getNextFrame();
        if (_disposed || _activeProvider != providerAtStart) {
          return;
        }
        final image = frame.image;

        final existing = _loadedImages[tile.key];
        if (existing != null) {
          existing.dispose();
        }
        _loadedImages[tile.key] = image;
        _cachedSortedEntries = null;
        _cachedSortedEntriesLength = -1;
        if (_loadedImages.length > 128) {
          final firstKey = _loadedImages.keys.first;
          final evicted = _loadedImages.remove(firstKey);
          evicted?.dispose();
        }
        onTileLoaded?.call();
      }
    } finally {
      _pendingFetches.remove(tile.key);
      _activeFetchCount--;
    }
  }

  // ---------------------------------------------------------------------------
  // Synchronous tile rendering
  // ---------------------------------------------------------------------------

  /// Draws every loaded tile onto [canvas] using [projectFn] to map
  /// geographic coordinates to screen-space offsets.
  ///
  /// Only tiles whose four corners all lie at least partially on the front
  /// hemisphere (z &ge; 0) are drawn. Each tile is sourced from a 256&times;256
  /// pixel image and projected through [projectFn] into a screen-space
  /// destination rectangle derived from its geographic bounds.
  void renderTiles(
    ui.Canvas canvas,
    VirtualCamera camera,
    ui.Size size,
    ui.Offset center,
    double sphereRadius,
    ProjectedPoint Function(double dim_0, double lng) projectFn, {
    bool isFlying = false,
  }) {
    if (!_fetcher.isEnabled()) return;

    // Kick off fetches for tiles that may be needed soon.
    beginTileFetch(camera, size, isFlying: isFlying);

    final List<MapEntry<String, ui.Image>> sortedEntries;
    if (_cachedSortedEntries != null && _cachedSortedEntriesLength == _loadedImages.length) {
      sortedEntries = _cachedSortedEntries!;
    } else {
      sortedEntries = _loadedImages.entries.toList()
        ..sort((e1, e2) {
          final z1 = int.tryParse(e1.key.split('/')[0]) ?? 0;
          final z2 = int.tryParse(e2.key.split('/')[0]) ?? 0;
          return z1.compareTo(z2);
        });
      _cachedSortedEntries = sortedEntries;
      _cachedSortedEntriesLength = _loadedImages.length;
    }
    for (final entry in sortedEntries) {
      final key = entry.key;
      final parts = key.split('/');
      if (parts.length != 3) continue;
      final z = int.tryParse(parts[0]) ?? -1;
      final x = int.tryParse(parts[1]) ?? -1;
      final y = int.tryParse(parts[2]) ?? -1;
      if (z < 0 || x < 0 || y < 0) continue;

      // LOD masking: skip this tile if a higher-zoom child tile is loaded.
      if (_hasHigherZoomOverlay(TileCoord(zoom: z, x: x, y: y))) continue;

      // Geographic bounds for this tile.
      final double latN = _tile2lat(y.toDouble(), z);
      final double latS = _tile2lat((y + 1).toDouble(), z);
      final double lonW = _tile2lon(x, z);
      final double lonE = _tile2lon(x + 1, z);

      final int subdivisions = subdivisionsForTesting(z);
      final List<ui.Offset> positions = [];
      final List<ui.Offset> textureCoordinates = [];
      final List<double> zs = [];

      for (int r = 0; r <= subdivisions; r++) {
        final double v = r / subdivisions;
        final double latDeg = _tile2lat(y + v, z);
        final double dim_0 = _rad(latDeg);
        final double texY = v * 256.0;

        for (int c = 0; c <= subdivisions; c++) {
          final double u = c / subdivisions;
          final double lonDeg = lonW + (lonE - lonW) * u;
          final double dim_1 = _rad(lonDeg);
          final double texX = u * 256.0;

          double projLat = latDeg;
          if (latDeg >= 85.0511) {
            projLat = 90.0;
          } else if (latDeg <= -85.0511) {
            projLat = -90.0;
          }

          final projected = projectFn(projLat, lonDeg);
          positions.add(projected.offset);
          textureCoordinates.add(ui.Offset(texX, texY));
          zs.add(projected.z);
        }
      }

      final List<int> indices = [];
      for (int r = 0; r < subdivisions; r++) {
        for (int c = 0; c < subdivisions; c++) {
          final int i0 = r * (subdivisions + 1) + c;
          final int i1 = i0 + 1;
          final int i2 = (r + 1) * (subdivisions + 1) + c;
          final int i3 = i2 + 1;

          // Triangle 1: (i0, i1, i2)
          final bool anyBehind1 = zs[i0] <= -100.0 || zs[i1] <= -100.0 || zs[i2] <= -100.0;
          final bool allCulled1 = zs[i0] < -0.5 && zs[i1] < -0.5 && zs[i2] < -0.5;
          if (anyBehind1 || allCulled1) {
            // Discard
          } else {
            indices.add(i0);
            indices.add(i1);
            indices.add(i2);
          }

          // Triangle 2: (i1, i3, i2)
          final bool anyBehind2 = zs[i1] <= -100.0 || zs[i3] <= -100.0 || zs[i2] <= -100.0;
          final bool allCulled2 = zs[i1] < -0.5 && zs[i3] < -0.5 && zs[i2] < -0.5;
          if (anyBehind2 || allCulled2) {
            // Discard
          } else {
            indices.add(i1);
            indices.add(i3);
            indices.add(i2);
          }
        }
      }

      if (indices.isEmpty) {
        if (onDrawVerticesForTesting != null) {
          onDrawVerticesForTesting!(positions, indices);
        }
        continue;
      }

      if (onDrawVerticesForTesting != null) {
        onDrawVerticesForTesting!(positions, indices);
      }

      final vertices = ui.Vertices(
        ui.VertexMode.triangles,
        positions,
        textureCoordinates: textureCoordinates,
        indices: indices,
      );

      final paint = ui.Paint()
        ..shader = ui.ImageShader(
          entry.value,
          ui.TileMode.clamp,
          ui.TileMode.clamp,
          Float64List.fromList([
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
          ]),
        );

      canvas.drawVertices(vertices, ui.BlendMode.srcOver, paint);
    }
  }

  /// Returns true only when all four direct child tiles at zoom [tile.zoom]+1
  /// are loaded in [_loadedImages], ensuring full geographic coverage before
  /// the parent tile can be skipped.
  bool _hasHigherZoomOverlay(TileCoord tile) {
    final int childZoom = tile.zoom + 1;
    final int childX0 = tile.x * 2;
    final int childY0 = tile.y * 2;
    final List<String> requiredChildren = [
      '$childZoom/$childX0/$childY0',
      '$childZoom/${childX0 + 1}/$childY0',
      '$childZoom/$childX0/${childY0 + 1}',
      '$childZoom/${childX0 + 1}/${childY0 + 1}',
    ];
    for (final childKey in requiredChildren) {
      if (!_loadedImages.containsKey(childKey)) return false;
    }
    return true;
  }

  double _min4(double a, double b, double c, double d) {
    double m = a;
    if (b < m) m = b;
    if (c < m) m = c;
    if (d < m) m = d;
    return m;
  }

  double _max4(double a, double b, double c, double d) {
    double m = a;
    if (b > m) m = b;
    if (c > m) m = c;
    if (d > m) m = d;
    return m;
  }

  /// Member documentation.
  @visibleForTesting
  List<TileCoord> visibleTilesForTesting(VirtualCamera camera, ui.Size viewportSize) {
    return _visibleTiles(camera, viewportSize);
  }

  /// Member documentation.
  @visibleForTesting
  TileCoord latLngToTileForTesting(double dim_0, double lng, int zoom) {
    return _latLngToTile(dim_0, lng, zoom);
  }

  /// Member documentation.
  @visibleForTesting
  static int subdivisionsForTesting(int zoom) {
    final double tileWidthDeg = 360.0 / math.pow(2, zoom);
    return (tileWidthDeg / 3.0).ceil().clamp(8, 32);
  }

  /// Member documentation.
  @visibleForTesting
  static List<int> calculateIndicesForTesting(List<double> zs) {
    const int subdivisions = 4;
    final List<int> indices = [];
    for (int r = 0; r < subdivisions; r++) {
      for (int c = 0; c < subdivisions; c++) {
        final int i0 = r * (subdivisions + 1) + c;
        final int i1 = i0 + 1;
        final int i2 = (r + 1) * (subdivisions + 1) + c;
        final int i3 = i2 + 1;

        // Triangle 1: (i0, i1, i2)
        final bool anyBehind1 = zs[i0] <= -100.0 || zs[i1] <= -100.0 || zs[i2] <= -100.0;
        final bool allCulled1 = zs[i0] < -0.5 && zs[i1] < -0.5 && zs[i2] < -0.5;
        if (anyBehind1 || allCulled1) {
          // Discard
        } else {
          indices.add(i0);
          indices.add(i1);
          indices.add(i2);
        }

        // Triangle 2: (i1, i3, i2)
        final bool anyBehind2 = zs[i1] <= -100.0 || zs[i3] <= -100.0 || zs[i2] <= -100.0;
        final bool allCulled2 = zs[i1] < -0.5 && zs[i3] < -0.5 && zs[i2] < -0.5;
        if (anyBehind2 || allCulled2) {
          // Discard
        } else {
          indices.add(i1);
          indices.add(i3);
          indices.add(i2);
        }
      }
    }
    return indices;
  }
}
