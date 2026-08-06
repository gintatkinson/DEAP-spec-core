// ignore_for_file: public_member_api_docs

import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/scheduler.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/cesium_engine.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/globe_tile_renderer.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/projected_point.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/tile_fetcher.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/camera_controller.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';
import 'package:app_flutter/features/topology/scene_3d_viewport_classes.dart';
export 'scene_3d_viewport_classes.dart' hide CoordinateTransformer;
import 'package:app_flutter/features/topology/topology_map.dart';
import 'package:app_flutter/features/tree/view_models/tree_view_model.dart';
import 'package:provider/provider.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:io' show Platform;

/// Realises: [Feat-002/SceneLayer]
abstract class SceneLayer {
  /// Member documentation.
  void paint(Canvas canvas, Size size, SceneViewState state);
}

/// Realises: [Feat-002/BackgroundLayer]
class BackgroundLayer extends SceneLayer {
  static final List<(double, double, double, double)> _stars = () {
    final rand = math.Random(42);
    return List.generate(100, (_) => (
      rand.nextDouble(),             // x fraction
      rand.nextDouble(),             // y fraction
      rand.nextDouble() * 1.5 + 0.5, // radius
      rand.nextDouble() * 0.7 + 0.3, // opacity
    ));
  }();

  final Paint _starPaint = Paint()..style = PaintingStyle.fill;

  @override
  void paint(Canvas canvas, Size size, SceneViewState state) {
    for (final (xf, yf, sz, op) in _stars) {
      _starPaint.color = Color.fromRGBO(255, 255, 255, op);
      canvas.drawCircle(Offset(xf * size.width, yf * size.height), sz, _starPaint);
    }

    if (state.horizonPath == null) return;

    Path getScaledPath(double scaleFactor) {
      final Matrix4 scaleMatrix = Matrix4.identity();
      scaleMatrix.translate(state.projectedCenter.dx, state.projectedCenter.dy);
      scaleMatrix.scale(scaleFactor);
      scaleMatrix.translate(-state.projectedCenter.dx, -state.projectedCenter.dy);
      return state.horizonPath!.transform(scaleMatrix.storage);
    }

    if (state.astronomicalBody == 'Proxima Centauri') {
      final Paint glowPaint = Paint()
        ..shader = RadialGradient(
          colors: [
            const Color(0x99FFD54F),
            const Color(0x00FFD54F),
          ],
          stops: const [0.5, 1.0],
        ).createShader(Rect.fromCircle(center: state.projectedCenter, radius: state.projectedRadius * 1.5));
      canvas.drawPath(getScaledPath(1.5), glowPaint);
    } else if (state.astronomicalBody == 'Earth') {
      final Paint glowPaint = Paint()
        ..shader = RadialGradient(
          colors: [
            const Color(0x6600E5FF),
            const Color(0x0000E5FF),
          ],
          stops: const [0.8, 1.0],
        ).createShader(Rect.fromCircle(center: state.projectedCenter, radius: state.projectedRadius * 1.05));
      canvas.drawPath(getScaledPath(1.05), glowPaint);
    }
  }
}

/// Realises: [Feat-002/GlobeLayer]
class GlobeLayer extends SceneLayer {
  final Paint _gridPaint = Paint()..style = PaintingStyle.stroke..strokeWidth = 0.8;
  final Paint _bandFillPaint = Paint()..style = PaintingStyle.fill;
  final Paint _bandBorderPaint = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.0;
  final Paint _flarePaint = Paint()..color = const Color(0xFFFFD54F)..style = PaintingStyle.stroke..strokeWidth = 2.0;
  final Paint _flareGlowPaint = Paint()..color = const Color(0x66FF9800)..style = PaintingStyle.stroke..strokeWidth = 6.0..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4.0);
  @override
  void paint(Canvas canvas, Size size, SceneViewState state) {
    if (state.horizonPath == null) return;

    List<Color> oceanColors;
    Color gridColor;
    
    if (state.astronomicalBody == 'Mars') {
      oceanColors = [const Color(0xFFBF360C), const Color(0xFF3E1103)];
      gridColor = const Color(0x22FF5722);
    } else if (state.astronomicalBody == 'Proxima Centauri') {
      oceanColors = [const Color(0xFFFFD54F), const Color(0xFFE65100)];
      gridColor = const Color(0x33FFD54F);
    } else {
      switch (state.activeStyle) {
        case 'Dark Map':
          oceanColors = [const Color(0xFF161B22), const Color(0xFF0D1117)];
          gridColor = const Color(0x1A00E5FF);
          break;
        case 'Street Map':
          oceanColors = [const Color(0xFF29B6F6), const Color(0xFF0288D1)];
          gridColor = const Color(0x33000000);
          break;
        case 'Light Map':
          oceanColors = [const Color(0xFFE0F7FA), const Color(0xFF80DEEA)];
          gridColor = const Color(0x26000000);
          break;
        case 'Satellite Map':
        default:
          oceanColors = [const Color(0xFF0F2B5C), const Color(0xFF040A18)];
          gridColor = const Color(0x2600E5FF);
          break;
      }
    }

    final Paint spherePaint = Paint()
      ..shader = RadialGradient(
        colors: oceanColors,
      ).createShader(Rect.fromCircle(center: state.projectedCenter, radius: state.projectedRadius));
    canvas.drawPath(state.horizonPath!, spherePaint);

    _gridPaint.color = gridColor;
    const double earthRadius = Ellipsoid.wgs84EquatorialRadius;

    const int numMeridians = 12;
    const int meridianSteps = 30;
    final double meridianLngStep = 2 * math.pi / numMeridians;
    final double meridianLatStep = math.pi / meridianSteps;
    for (int i = 0; i < numMeridians; i++) {
      final double lng = i * meridianLngStep;
      for (int j = 0; j < meridianSteps; j++) {
        final double lat1 = -math.pi / 2 + j * meridianLatStep;
        final double lat2 = -math.pi / 2 + (j + 1) * meridianLatStep;
        
        final ProjectedPoint p1 = state.transformer.projectWgs84ToScreen(latRad: lat1, lngRad: lng, heightMeters: 0.0);
        final ProjectedPoint p2 = state.transformer.projectWgs84ToScreen(latRad: lat2, lngRad: lng, heightMeters: 0.0);
        
        if (p1.z >= 0 && p2.z >= 0) {
          canvas.drawLine(p1.offset, p2.offset, _gridPaint);
        }
      }
    }

    const int numParallels = 6;
    const int parallelSteps = 60;
    final double parallelLngStep = 2 * math.pi / parallelSteps;
    final double parallelLatStep = math.pi / (numParallels + 1);
    for (int i = 0; i < numParallels; i++) {
      final double lat = -math.pi / 2 + (i + 1) * parallelLatStep;
      for (int j = 0; j < parallelSteps; j++) {
        final double lng1 = j * parallelLngStep;
        final double lng2 = (j + 1) * parallelLngStep;
        
        final ProjectedPoint p1 = state.transformer.projectWgs84ToScreen(latRad: lat, lngRad: lng1, heightMeters: 0.0);
        final ProjectedPoint p2 = state.transformer.projectWgs84ToScreen(latRad: lat, lngRad: lng2, heightMeters: 0.0);
        
        if (p1.z >= 0 && p2.z >= 0) {
          canvas.drawLine(p1.offset, p2.offset, _gridPaint);
        }
      }
    }

    if (state.astronomicalBody != 'Proxima Centauri') {
      final List<(double, double, Color)> bands = [
        (math.pi / 2, math.pi * 0.4, const Color(0x0800BFFF)),  // Arctic
        (math.pi * 0.4, math.pi * 0.15, const Color(0x082196F3)), // Boreal
        (math.pi * 0.15, -math.pi * 0.15, const Color(0x0800E676)), // Tropical
        (-math.pi * 0.15, -math.pi * 0.4, const Color(0x082196F3)), // Temperate S
        (-math.pi * 0.4, -math.pi / 2, const Color(0x0800BFFF)),  // Antarctic
      ];

      for (final (latMax, latMin, color) in bands) {
        _bandFillPaint.color = color;
        _bandBorderPaint.color = color.withOpacity(0.4);

        const int steps = 60;
        final List<ProjectedPoint> pts = [];
        for (int s = 0; s <= steps; s++) {
          final double lng = s * (2 * math.pi / steps);
          final p = state.transformer.projectWgs84ToScreen(latRad: latMin, lngRad: lng, heightMeters: earthRadius * 0.002);
          if (p.z >= 0.0) pts.add(p);
        }
        for (int s = steps; s >= 0; s--) {
          final double lng = s * (2 * math.pi / steps);
          final p = state.transformer.projectWgs84ToScreen(latRad: latMax, lngRad: lng, heightMeters: earthRadius * 0.002);
          if (p.z >= 0.0) pts.add(p);
        }

        if (pts.length >= 3) {
          final Path path = Path();
          path.moveTo(pts.first.offset.dx, pts.first.offset.dy);
          for (int i = 1; i < pts.length; i++) {
            path.lineTo(pts[i].offset.dx, pts[i].offset.dy);
          }
          path.close();
          canvas.drawPath(path, _bandFillPaint);
          canvas.drawPath(path, _bandBorderPaint);
        }
      }
    } else {
      const int numFlares = 8;
      for (int f = 0; f < numFlares; f++) {
        final double baseAngle = f * (2 * math.pi / numFlares);
        final double pulse = 1.0;
        
        final double angleStart = baseAngle;
        final double angleEnd = baseAngle + 0.25;
        final double angleMid = baseAngle + 0.125;
        
        final Offset ptStart = Offset(
          state.projectedCenter.dx + state.projectedRadius * math.cos(angleStart),
          state.projectedCenter.dy + state.projectedRadius * math.sin(angleStart),
        );
        final Offset ptEnd = Offset(
          state.projectedCenter.dx + state.projectedRadius * math.cos(angleEnd),
          state.projectedCenter.dy + state.projectedRadius * math.sin(angleEnd),
        );
        final Offset ptControl = Offset(
          state.projectedCenter.dx + state.projectedRadius * 1.25 * pulse * math.cos(angleMid),
          state.projectedCenter.dy + state.projectedRadius * 1.25 * pulse * math.sin(angleMid),
        );
        
        final Path flarePath = Path()
          ..moveTo(ptStart.dx, ptStart.dy)
          ..quadraticBezierTo(ptControl.dx, ptControl.dy, ptEnd.dx, ptEnd.dy);
          
        canvas.drawPath(flarePath, _flareGlowPaint);
        canvas.drawPath(flarePath, _flarePaint);
      }
    }

    if (state.tileRenderer != null && state.tileRenderer!.isEnabled) {
      state.tileRenderer!.renderTiles(
        canvas,
        state.camera,
        size,
        state.transformer.screenCenter,
        Ellipsoid.wgs84EquatorialRadius,
        (double latDeg, double lngDeg) {
          final double elev = state.elevationProvider.getElevation(latDeg, lngDeg);
          final double ampElev = elev * state.verticalExaggeration;
          return state.transformer.projectWgs84ToScreen(
            latRad: latDeg * math.pi / 180.0,
            lngRad: lngDeg * math.pi / 180.0,
            heightMeters: ampElev,
          );
        },
        isFlying: state.isFlying,
      );
    }

    final Paint shadingOverlayPaint = Paint()
      ..shader = RadialGradient(
        colors: [const Color(0x00000000), const Color(0x22000000), const Color(0xAA000000)],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromCircle(center: state.projectedCenter, radius: state.projectedRadius));
    canvas.drawPath(state.horizonPath!, shadingOverlayPaint);
  }
}

/// Realises: [Feat-002/TopologyLayer]
class TopologyLayer extends SceneLayer {
  final Paint _linkPaint = Paint()..color = const Color(0xFFFF6D00)..style = PaintingStyle.stroke..strokeWidth = 1.5;
  final Paint _linkGlowPaint = Paint()..color = const Color(0x33FF6D00)..style = PaintingStyle.stroke..strokeWidth = 4.0;
  final Paint _packetPointPaint = Paint()..color = const Color(0xFFFFD54F)..strokeWidth = 5.0..strokeCap = StrokeCap.round..style = PaintingStyle.stroke;
  final Paint _gsPointPaint = Paint()..color = const Color(0xFF00E5FF)..strokeWidth = 6.0..strokeCap = StrokeCap.round..style = PaintingStyle.stroke;
  final Paint _gsGlowPointPaint = Paint()..color = const Color(0x6600E5FF)..strokeWidth = 12.0..strokeCap = StrokeCap.round..style = PaintingStyle.stroke;
  final Paint _satNodePaint = Paint()..color = const Color(0xFFFFB300)..style = PaintingStyle.fill;
  final Paint _satNodeGlowPaint = Paint()..color = const Color(0x66FFB300)..style = PaintingStyle.fill;
  final Paint _innerWhitePaint = Paint()..color = Colors.white..style = PaintingStyle.fill;
  final Paint _dropPaint = Paint()..color = const Color(0x80FFFFFF)..style = PaintingStyle.stroke..strokeWidth = 1.0;

  @override
  void paint(Canvas canvas, Size size, SceneViewState state) {
    if (!state.showDevices) return;

    if (state.groundGlowPoints.isNotEmpty) {
      canvas.drawPoints(PointMode.points, state.groundGlowPoints, _gsGlowPointPaint);
    }
    if (state.groundPoints.isNotEmpty) {
      canvas.drawPoints(PointMode.points, state.groundPoints, _gsPointPaint);
    }

    if (state.showLinks) {
      if (state.linkGlowPoints.isNotEmpty) {
        canvas.drawPoints(PointMode.lines, state.linkGlowPoints, _linkGlowPaint);
      }
      if (state.linkPoints.isNotEmpty) {
        canvas.drawPoints(PointMode.lines, state.linkPoints, _linkPaint);
      }
      if (state.packetPoints.isNotEmpty) {
        canvas.drawPoints(PointMode.points, state.packetPoints, _packetPointPaint);
      }
    }

    for (final node in state.topologyData?.nodes ?? <TopologyNode>[]) {
      final proj = state.projectedNodes[node.id];
      if (proj == null || proj.z < 0) continue;

      final String heightRef = (node.rawProperties['heightReference'] ?? node.rawProperties['height_reference'] ?? '').toString().toUpperCase();
      final double alt = node.position.dim2;
      String type = (heightRef == 'RELATIVE_TO_GROUND' || heightRef == 'CLAMP_TO_GROUND') ? 'ground' : (heightRef == 'ABSOLUTE' ? 'space' : (alt < 50000.0 ? 'ground' : 'space'));

      final model = state.nodeModels[node.id];
      final bool hasLoadedModel = model != null && model.state == ModelRenderState.loaded && model.gltfData != null;

      if (hasLoadedModel) {
        final Path path = Path();
        final double s = 6.0;
        path.moveTo(proj.offset.dx, proj.offset.dy - s);
        path.lineTo(proj.offset.dx + s, proj.offset.dy);
        path.lineTo(proj.offset.dx, proj.offset.dy + s);
        path.lineTo(proj.offset.dx - s, proj.offset.dy);
        path.close();
        
        canvas.drawPath(path, _satNodePaint);
        canvas.drawPath(
          path,
          Paint()
            ..color = Colors.white
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.0,
        );
      } else if (type == 'space') {
        canvas.drawCircle(proj.offset, 7.0, _satNodeGlowPaint);
        canvas.drawCircle(proj.offset, 4.0, _satNodePaint);
        canvas.drawCircle(proj.offset, 1.8, _innerWhitePaint);
      }
        
      if (type == 'space' && state.showDropLines) {
         final double latRad = node.position.dim1 * math.pi / 180.0;
         final double lngRad = node.position.dim0 * math.pi / 180.0;
         final double elev = state.elevationProvider.getElevation(node.position.dim1, node.position.dim0);
         final double surfaceHeight = Ellipsoid.wgs84EquatorialRadius + elev * state.verticalExaggeration;
         final surfaceProj = state.transformer.projectWgs84ToScreen(latRad: latRad, lngRad: lngRad, heightMeters: surfaceHeight);
         const int dashes = 10;
         for (int d = 0; d < dashes; d++) {
           final Offset pStart = Offset.lerp(proj.offset, surfaceProj.offset, d / dashes)!;
           final Offset pEnd = Offset.lerp(proj.offset, surfaceProj.offset, (d + 0.5) / dashes)!;
           canvas.drawLine(pStart, pEnd, _dropPaint);
         }
      }
    }
  }
}

/// Realises: [Feat-002/HUDLayer]
class HUDLayer extends SceneLayer {
  final Paint _reticleDotPaint = Paint()..color = const Color(0xFF00E5FF)..style = PaintingStyle.fill;
  final Paint _reticlePaint = Paint()..color = const Color(0xCC00E5FF)..style = PaintingStyle.stroke..strokeWidth = 1.0;
  final Paint _labelBgPaint = Paint()..color = const Color(0xE6000000)..style = PaintingStyle.fill;
  final Paint _labelBorderPaint = Paint()..style = PaintingStyle.stroke..strokeWidth = 1.0;

  @override
  void paint(Canvas canvas, Size size, SceneViewState state) {
    final center = state.transformer.screenCenter;
    canvas.drawCircle(center, 3.0, _reticleDotPaint);
    canvas.drawCircle(center, 10.0, _reticlePaint);

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.drawLine(const Offset(0, -18), const Offset(0, -10), _reticlePaint);
    canvas.drawLine(const Offset(0, 10), const Offset(0, 18), _reticlePaint);
    canvas.drawLine(const Offset(-18, 0), const Offset(-10, 0), _reticlePaint);
    canvas.drawLine(const Offset(10, 0), const Offset(18, 0), _reticlePaint);
    canvas.restore();

    if (state.showLabels && state.showDevices) {
      for (final node in state.topologyData?.nodes ?? <TopologyNode>[]) {
        final proj = state.projectedNodes[node.id];
        if (proj == null || proj.z < 0) continue;

        final double alt = node.position.dim2;
        final String type = (alt < 50000.0) ? 'ground' : 'space';
        final String labelText = node.label.isNotEmpty ? node.label : node.id;
        final Color textColor = type == 'space' ? const Color(0xFFFFB300) : const Color(0xFF00E5FF);
        
        final key = TextPainterKey(labelText, textColor);
        final textPainter = state.textPainterCache[key];
        if (textPainter != null) {
          final Offset? finalPos = state.finalLabelPositions[node.id];
          if (finalPos != null) {
            final Rect outerRect = Rect.fromLTWH(finalPos.dx - 6, finalPos.dy - 3, textPainter.width + 12, textPainter.height + 6);
            final RRect capsuleRRect = RRect.fromRectAndRadius(outerRect, const Radius.circular(8));
            _labelBorderPaint.color = textColor.withOpacity(0.4);
            canvas.drawRRect(capsuleRRect, _labelBgPaint);
            canvas.drawRRect(capsuleRRect, _labelBorderPaint);
            textPainter.paint(canvas, finalPos);
          }
        }
      }
    }
  }
}

/// Realises: [Feat-002/Scene3DViewportPainter]
class Scene3DViewportPainter extends CustomPainter {
  (double, double, double) getEcefCoordinatesForTesting(double lat, double lng, double height) {
    final double px = height * math.cos(lat) * math.cos(lng);
    final double py = height * math.cos(lat) * math.sin(lng);
    final double pz = height * math.sin(lat);
    return (px, py, pz);
  }

  (double, double, double) getSnappedEcefCoordinatesForTesting(
    double lat,
    double lng,
    double height,
    double cameraAltitude,
  ) {
    final double R = Ellipsoid.wgs84EquatorialRadius;
    final double radLng = 0.0;
    final double radLat = 0.0;

    double px = height * math.cos(lat) * math.cos(lng);
    double py = height * math.cos(lat) * math.sin(lng);
    double pz = height * math.sin(lat);

    final double cRad = cameraAltitude;
    final double cx = cRad * math.cos(radLat) * math.cos(radLng);
    final double cy = cRad * math.cos(radLat) * math.sin(radLng);
    final double cz = cRad * math.sin(radLat);

    final double d2 = cRad * cRad;
    final double r2 = R * R;

    // cull check
    bool isCulled = false;
    {
      final double cullHeight = math.max(height, R);
      final double pxCull = cullHeight * math.cos(lat) * math.cos(lng);
      final double pyCull = cullHeight * math.cos(lat) * math.sin(lng);
      final double pzCull = cullHeight * math.sin(lat);

      final double rx = pxCull - cx;
      final double ry = pyCull - cy;
      final double rz = pzCull - cz;
      final double dCP2 = rx * rx + ry * ry + rz * rz;
      final double dotPC = pxCull * cx + pyCull * cy + pzCull * cz;

      if (dotPC < r2) {
        final double tMin = (d2 - dotPC) / dCP2;
        if (tMin >= 0.0 && tMin <= 1.0) {
          final double minDistanceSq = d2 - (d2 - dotPC) * (d2 - dotPC) / dCP2;
          if (minDistanceSq < r2) {
            isCulled = true;
          }
        }
      }
    }
    if (height < R && cRad > R) {
      isCulled = true;
    }

    if (isCulled) {
      final double h2 = height * height;
      if (d2 > h2) {
        final double r2_over_d2 = h2 / d2;
        final double parX = r2_over_d2 * cx;
        final double parY = r2_over_d2 * cy;
        final double parZ = r2_over_d2 * cz;

        final double dotPC = px * cx + py * cy + pz * cz;
        final double dot_over_d2 = dotPC / d2;
        final double perpX = px - dot_over_d2 * cx;
        final double perpY = py - dot_over_d2 * cy;
        final double perpZ = pz - dot_over_d2 * cz;

        final double perpLen = math.sqrt(perpX * perpX + perpY * perpY + perpZ * perpZ);
        if (perpLen > 0.0) {
          final double rHorizon = height * math.sqrt(1.0 - h2 / d2);
          final double scale = rHorizon / perpLen;
          px = parX + perpX * scale;
          py = parY + perpY * scale;
          pz = parZ + perpZ * scale;
        }
      }
    }
    return (px, py, pz);
  }

  /// Member documentation.
  final List<SceneLayer> layers;
  /// Member documentation.
  final SceneViewState state;
  /// Member documentation.
  final double userRotationX;
  /// Member documentation.
  final double userTilt;
  /// Member documentation.
  final double zoomScale;

  Scene3DViewportPainter({
    List<SceneLayer>? layers,
    SceneViewState? state,
    bool? isFlying,
    VirtualCamera? camera,
    TopologyData? topologyData,
    String? activeStyle,
    String? astronomicalBody,
    bool? elevationActive,
    bool? showDevices,
    bool? showLinks,
    bool? showLabels,
    bool? showDropLines,
    double? verticalExaggeration,
    GlobeTileRenderer? tileRenderer,
    this.userRotationX = 0.0,
    this.userTilt = 0.0,
    this.zoomScale = 1.0,
  }) : layers = layers ?? [BackgroundLayer(), GlobeLayer(), TopologyLayer(), HUDLayer()],
       state = state ?? SceneViewState(),
       super(repaint: state ?? SceneViewState()) {
    final passedState = state;
    if (passedState == null) {
      if (camera != null) this.state.camera = camera;
      if (topologyData != null) this.state.topologyData = topologyData;
      this.state.activeStyle = activeStyle ?? '';
      this.state.astronomicalBody = astronomicalBody ?? 'Earth';
      this.state.elevationActive = elevationActive ?? true;
      this.state.showDevices = showDevices ?? true;
      this.state.showLinks = showLinks ?? true;
      this.state.showLabels = showLabels ?? true;
      this.state.showDropLines = showDropLines ?? true;
      this.state.verticalExaggeration = verticalExaggeration ?? 1.0;
      this.state.elevationProvider = ElevationProvider(
        isElevationActive: this.state.elevationActive,
        verticalExaggeration: this.state.verticalExaggeration,
      );
      this.state.tileRenderer = tileRenderer;
      this.state.isFlying = isFlying ?? false;
    } else {
      if (camera != null) this.state.camera = camera;
      if (topologyData != null) this.state.topologyData = topologyData;
      if (activeStyle != null) this.state.activeStyle = activeStyle;
      if (astronomicalBody != null) this.state.astronomicalBody = astronomicalBody;
      if (elevationActive != null) this.state.elevationActive = elevationActive;
      if (showDevices != null) this.state.showDevices = showDevices;
      if (showLinks != null) this.state.showLinks = showLinks;
      if (showLabels != null) this.state.showLabels = showLabels;
      if (showDropLines != null) this.state.showDropLines = showDropLines;
      if (verticalExaggeration != null) this.state.verticalExaggeration = verticalExaggeration;
      this.state.elevationProvider = ElevationProvider(
        isElevationActive: this.state.elevationActive,
        verticalExaggeration: this.state.verticalExaggeration,
      );
      if (tileRenderer != null) this.state.tileRenderer = tileRenderer;
      if (isFlying != null) this.state.isFlying = isFlying;
    }
  }

  /// Member documentation.
  static double getElevationStatic(double latDeg, double lngDeg, bool isElevationActive) {
    return ElevationProvider(isElevationActive: isElevationActive).getElevation(latDeg, lngDeg);
  }

  /// Member documentation.
  double getElevation(double latDeg, double lngDeg) {
    try {
      return state.elevationProvider.getElevation(latDeg, lngDeg);
    } catch (_) {
      return ElevationProvider(isElevationActive: true).getElevation(latDeg, lngDeg);
    }
  }

  /// Member documentation.
  ProjectedPoint project(double latRad, double lngRad, double heightMeters, Offset center, double rotationAngle, double tilt, Size size, {bool clampToHorizon = true}) {
    VirtualCamera cam;
    try {
      cam = state.camera;
    } catch (_) {
      cam = VirtualCamera.raw(dim_0: -tilt * 180 / math.pi, dim_1: -rotationAngle * 180 / math.pi, dim_2: 500000, heading: 0, pitch: -90, roll: 0);
    }
    return CoordinateTransformer(
      camera: cam, 
      viewportSize: size, 
      screenCenter: center, 
      rotationAngle: rotationAngle, 
      tilt: tilt
    ).projectWgs84ToScreen(
      latRad: latRad, 
      lngRad: lngRad, 
      heightMeters: heightMeters - Ellipsoid.wgs84EquatorialRadius, 
      clampToHorizon: clampToHorizon
    );
  }

  /// Calculates the tile Level-of-Detail (LOD) index for a given altitude in meters.
  int calculateTileLOD(double altitudeMeters) {
    double alt = altitudeMeters;
    if (alt <= 0) alt = 100.0;
    final lod = (math.log(120000000.0 / alt) / math.ln2).round();
    return lod.clamp(0, 18);
  }

  @override
  void paint(Canvas canvas, Size size) {
    canvas.clipRect(Offset.zero & size);
    for (final layer in layers) {
      layer.paint(canvas, size, state);
    }
  }

  @override
  bool shouldRepaint(covariant Scene3DViewportPainter oldDelegate) => true; 
}

/// Realises: [Feat-002/CameraStatsPanel]
@immutable
class CameraStatsPanel extends StatelessWidget {
  /// Member documentation.
  final CameraController cameraController;
  /// Member documentation.
  final VoidCallback onClose;
  /// Member documentation.
  final int frameDropCount;
  
  const CameraStatsPanel({super.key, required this.cameraController, required this.onClose, this.frameDropCount = 0});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 16,
      left: 16,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: ListenableBuilder(
          listenable: cameraController,
          builder: (context, _) {
            final cam = cameraController.current;
            return Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.6),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0x33FFFFFF), width: 1.0),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('CAMERA STATS', style: TextStyle(color: Color(0xFF00E5FF), fontWeight: FontWeight.bold, fontFamily: 'monospace', fontSize: 12)),
                      InkWell(key: const Key('collapse_camera_stats_button'), onTap: onClose, child: const Icon(Icons.close, size: 14, color: Color(0xAAFFFFFF))),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('Latitude: ${cam.dim_0.toStringAsFixed(6)}', style: const TextStyle(color: Color(0xFFE0E0E0), fontFamily: 'monospace', fontSize: 11)),
                  Text('Longitude: ${cam.dim_1.toStringAsFixed(6)}', style: const TextStyle(color: Color(0xFFE0E0E0), fontFamily: 'monospace', fontSize: 11)),
                  Text('Altitude: ${(cam.dim_2 - Ellipsoid.wgs84EquatorialRadius).toStringAsFixed(2)} meters', style: const TextStyle(color: Color(0xFFE0E0E0), fontFamily: 'monospace', fontSize: 11)),
                  Text('Pitch/Yaw/Roll: ${cam.pitch} / ${cam.heading} / ${cam.roll}', style: const TextStyle(color: Color(0xFFE0E0E0), fontFamily: 'monospace', fontSize: 11)),
                  Text('Frame Drops: $frameDropCount', style: const TextStyle(color: Color(0xFFE0E0E0), fontFamily: 'monospace', fontSize: 11)),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Realises: [Feat-002/MapConfigPanel]
@immutable
class MapConfigPanel extends StatelessWidget {
  /// Member documentation.
  final String activeStyle;
  /// Member documentation.
  final String astronomicalBody;
  /// Member documentation.
  final String activeDatum;
  /// Member documentation.
  final bool elevationActive;
  /// Member documentation.
  final bool showDevices;
  /// Member documentation.
  final bool showLinks;
  /// Member documentation.
  final bool showLabels;
  /// Member documentation.
  final bool showDropLines;
  /// Member documentation.
  final ValueChanged<String> onStyleChanged;
  /// Member documentation.
  final ValueChanged<String> onBodyChanged;
  /// Member documentation.
  final ValueChanged<String>? onDatumChanged;
  /// Member documentation.
  final ValueChanged<bool> onElevationToggled;
  /// Member documentation.
  final ValueChanged<bool> onDevicesToggled;
  /// Member documentation.
  final ValueChanged<bool> onLinksToggled;
  /// Member documentation.
  final ValueChanged<bool> onLabelsToggled;
  /// Member documentation.
  final ValueChanged<bool> onDropLinesToggled;
  /// Member documentation.
  final VoidCallback onClose;
  /// Member documentation.
  final VoidCallback onResetCamera;

  const MapConfigPanel({
    super.key,
    required this.activeStyle,
    required this.astronomicalBody,
    this.activeDatum = 'WGS84',
    required this.elevationActive,
    required this.showDevices,
    required this.showLinks,
    required this.showLabels,
    required this.showDropLines,
    required this.onStyleChanged,
    required this.onBodyChanged,
    this.onDatumChanged,
    required this.onElevationToggled,
    required this.onDevicesToggled,
    required this.onLinksToggled,
    required this.onLabelsToggled,
    required this.onDropLinesToggled,
    required this.onClose,
    required this.onResetCamera,
  });

  Widget _buildStyleButton(String style) {
    final bool isActive = activeStyle == style;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => onStyleChanged(style),
        child: Container(
          margin: const EdgeInsets.all(4),
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
          decoration: BoxDecoration(
            color: isActive ? const Color(0x2200E5FF) : const Color(0x0AFFFFFF),
            border: Border.all(color: isActive ? const Color(0xFF00E5FF) : const Color(0x33FFFFFF), width: 1.0),
            borderRadius: BorderRadius.circular(6),
          ),
          alignment: Alignment.center,
          child: Text(style.toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: isActive ? const Color(0xFF00E5FF) : const Color(0xFFB0BEC5), fontSize: 9, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
        ),
      ),
    );
  }

  Widget _buildBodyButton(String body) {
    final bool isActive = astronomicalBody == body;
    return Expanded(
      child: GestureDetector(
        onTap: () => onBodyChanged(body),
        child: Container(
          margin: const EdgeInsets.all(4),
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
          decoration: BoxDecoration(
            color: isActive ? const Color(0x2200E5FF) : const Color(0x0AFFFFFF),
            border: Border.all(color: isActive ? const Color(0xFF00E5FF) : const Color(0x33FFFFFF), width: 1.0),
            borderRadius: BorderRadius.circular(6),
          ),
          alignment: Alignment.center,
          child: Text(body.toUpperCase(), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: isActive ? const Color(0xFF00E5FF) : const Color(0xFFB0BEC5), fontSize: 9, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
        ),
      ),
    );
  }

  Widget _buildDatumButton(String datum) {
    final bool isActive = activeDatum.toUpperCase() == datum.toUpperCase();
    return Expanded(
      child: GestureDetector(
        onTap: () => onDatumChanged?.call(datum),
        child: Container(
          margin: const EdgeInsets.all(4),
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
          decoration: BoxDecoration(
            color: isActive ? const Color(0x2200E5FF) : const Color(0x0AFFFFFF),
            border: Border.all(color: isActive ? const Color(0xFF00E5FF) : const Color(0x33FFFFFF), width: 1.0),
            borderRadius: BorderRadius.circular(6),
          ),
          alignment: Alignment.center,
          child: Text(
            datum.toUpperCase(),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: isActive ? const Color(0xFF00E5FF) : const Color(0xFFB0BEC5),
              fontSize: 9,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildVisibilityToggle(String label, bool value, ValueChanged<bool> onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(child: Text(label, overflow: TextOverflow.ellipsis, maxLines: 1, style: const TextStyle(color: Color(0xFFCFD8DC), fontSize: 11, fontFamily: 'monospace'))),
          const SizedBox(width: 8),
          Switch(value: value, onChanged: onChanged, activeColor: const Color(0xFF00E5FF), activeTrackColor: const Color(0x6600E5FF), inactiveThumbColor: const Color(0xFF78909C), inactiveTrackColor: const Color(0x33FFFFFF), materialTapTargetSize: MaterialTapTargetSize.shrinkWrap),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 16,
      right: 16,
      bottom: 16,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: 320,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.black.withOpacity(0.6), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0x3300E5FF), width: 1.0)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.settings, color: Color(0xFF00E5FF), size: 16),
                  const SizedBox(width: 8),
                  const Expanded(child: Text('MAP CONFIGURATION', style: TextStyle(color: Color(0xFF00E5FF), fontSize: 12, fontWeight: FontWeight.bold))),
                  InkWell(key: const Key('collapse_map_config_button'), onTap: onClose, child: const Padding(padding: EdgeInsets.all(4.0), child: Icon(Icons.close, size: 14, color: Color(0xAAFFFFFF)))),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(color: Color(0x2200E5FF), height: 1),
              const SizedBox(height: 12),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('ASTRONOMICAL BODY', style: TextStyle(color: Color(0xFFB0BEC5), fontWeight: FontWeight.bold, fontSize: 10)),
                      Row(children: [_buildBodyButton('Earth'), _buildBodyButton('Mars')]),
                      Row(children: [_buildBodyButton('Proxima Centauri')]),
                      const SizedBox(height: 16),
                      const Text('COORDINATE DATUM', style: TextStyle(color: Color(0xFFB0BEC5), fontWeight: FontWeight.bold, fontSize: 10)),
                      Row(children: [_buildDatumButton('WGS84'), _buildDatumButton('NAD83'), _buildDatumButton('WebMercator')]),
                      const SizedBox(height: 16),
                      const Text('BASE LAYER STYLE', style: TextStyle(color: Color(0xFFB0BEC5), fontWeight: FontWeight.bold, fontSize: 10)),
                      Row(children: [_buildStyleButton('Dark Map'), _buildStyleButton('Street Map')]),
                      Row(children: [_buildStyleButton('Satellite Map'), _buildStyleButton('Light Map')]),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('3D SURFACE ELEVATION', style: TextStyle(color: Color(0xFFCFD8DC), fontWeight: FontWeight.bold, fontSize: 10)),
                          Switch(value: elevationActive, onChanged: onElevationToggled, activeColor: const Color(0xFF00E5FF), activeTrackColor: const Color(0x6600E5FF), inactiveThumbColor: const Color(0xFF78909C), inactiveTrackColor: const Color(0x33FFFFFF)),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Text('VISIBILITY TOGGLES', style: TextStyle(color: Color(0xFFB0BEC5), fontWeight: FontWeight.bold, fontSize: 10)),
                      _buildVisibilityToggle('Devices / Nodes', showDevices, onDevicesToggled),
                      _buildVisibilityToggle('Topology Links', showLinks, onLinksToggled),
                      _buildVisibilityToggle('Address Labels', showLabels, onLabelsToggled),
                      _buildVisibilityToggle('Vertical Drop Lines', showDropLines, onDropLinesToggled),
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton(
                          onPressed: onResetCamera,
                          style: OutlinedButton.styleFrom(side: const BorderSide(color: Color(0xFF00E5FF), width: 1.0), backgroundColor: const Color(0x0D00E5FF), padding: const EdgeInsets.symmetric(vertical: 12)),
                          child: const Text('RESET CAMERA PERSPECTIVE', style: TextStyle(color: Color(0xFF00E5FF), fontSize: 10, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Realises: [Feat-002/Scene3DViewport]
class Scene3DViewport extends StatefulWidget {
  /// Member documentation.
  final VirtualCamera camera;
  final TopologyData? topologyData;
  final ValueChanged<VirtualCamera>? onCameraChanged;
  /// Member documentation.
  final double verticalExaggeration;

  const Scene3DViewport({
    super.key,
    required this.camera,
    this.topologyData,
    this.onCameraChanged,
    this.verticalExaggeration = 1.0,
  });

  /// Member documentation.
  bool initializeScene() => true;
  /// Member documentation.
  bool render(Canvas canvas) => true;

  @override
  State<Scene3DViewport> createState() => Scene3DViewportState();
}

/// Realises: [Feat-002/Scene3DViewportState]
class Scene3DViewportState extends State<Scene3DViewport> with SingleTickerProviderStateMixin {
  late CameraController _cameraController;
  TreeViewModel? _treeViewModel;

  @visibleForTesting CameraController get cameraController => _cameraController;
  @visibleForTesting FocusNode get globeFocusNode => _globeFocusNode;
  @visibleForTesting GlobeTileRenderer? get tileRenderer => _tileRenderer;

  /// Member documentation.
  Offset getProjectedPosition(
    double latitude,
    double longitude, {
    double altitude = 0.0,
    String nodeType = '',
  }) {
    final Size? size = context.size;
    if (size == null) return Offset.zero;

    final rawCamera = _cameraController.current;
    final camera = rawCamera.dim_2 < Ellipsoid.wgs84EquatorialRadius 
      ? VirtualCamera.raw(
          dim_0: rawCamera.dim_0,
          dim_1: rawCamera.dim_1,
          dim_2: Ellipsoid.wgs84EquatorialRadius + rawCamera.dim_2,
          heading: rawCamera.heading,
          pitch: rawCamera.pitch,
          roll: rawCamera.roll,
        ) 
      : rawCamera;

    final transformer = CoordinateTransformer(
      camera: camera,
      viewportSize: size,
      screenCenter: Offset(size.width * 0.45, size.height * 0.5),
      rotationAngle: -(camera.dim_1 * math.pi / 180.0),
      tilt: -(camera.dim_0 * math.pi / 180.0),
    );

    final String heightRef = nodeType.toUpperCase();
    final String type;
    if (heightRef == 'RELATIVE_TO_GROUND' || heightRef == 'CLAMP_TO_GROUND') {
      type = 'ground';
    } else if (heightRef == 'ABSOLUTE') {
      type = 'space';
    } else {
      type = (altitude < 50000.0) ? 'ground' : 'space';
    }

    final double finalHeight;
    if (type == 'space') {
      finalHeight = altitude;
    } else {
      if (_elevationActive) {
        final double terrainElev = Scene3DViewportPainter.getElevationStatic(latitude, longitude, _elevationActive);
        final double relativeAlt;
        if (heightRef == 'CLAMP_TO_GROUND') {
          relativeAlt = 0.0;
        } else if (heightRef == 'RELATIVE_TO_GROUND') {
          relativeAlt = altitude;
        } else {
          relativeAlt = altitude - terrainElev;
        }
        finalHeight = terrainElev * widget.verticalExaggeration + relativeAlt;
      } else {
        finalHeight = altitude;
      }
    }

    final proj = transformer.projectWgs84ToScreen(
      latRad: latitude * math.pi / 180.0,
      lngRad: longitude * math.pi / 180.0,
      heightMeters: finalHeight,
    );
    return proj.offset;
  }

  final FocusNode _globeFocusNode = FocusNode();
  final SceneViewState _viewState = SceneViewState();

  bool _shiftHeld = false;
  bool _ctrlHeld = false;
  bool _rightButtonDown = false;
  bool _isUpdatingWidget = false;

  String _activeStyle = 'Satellite Map';
  String _astronomicalBody = 'Earth';
  bool _elevationActive = true;
  bool _showDevices = true;
  bool _showLinks = true;
  bool _showLabels = true;
  bool _showDropLines = true;
  bool _showCameraStats = true;
  bool _showMapConfig = true;

  GlobeTileRenderer? _tileRenderer;
  Ticker? _flyTicker;
  int _tileCacheVersion = 0;

  ImageryProvider _providerForStyle(String style) {
    switch (style) {
      case 'Dark Map': return ImageryProvider.cartoDark;
      case 'Street Map': return ImageryProvider.openStreetMap;
      case 'Light Map': return ImageryProvider.cartoLight;
      case 'Satellite Map': default: return ImageryProvider.arcGisSatellite;
    }
  }

  @override
  void initState() {
    super.initState();
    _flyTicker = createTicker((_) {
      if (_cameraController.tick()) _flyTicker?.stop();
    });

    _cameraController = CameraController(widget.camera.toAbsoluteWgs84());
    _cameraController.elevationProvider = (lat, lng) {
      return ElevationProvider(isElevationActive: _elevationActive).getElevation(lat, lng) * widget.verticalExaggeration;
    };
    _cameraController.addListener(_onCameraChangedInside);

    _tileRenderer = GlobeTileRenderer(
      fetcher: TileFetcher(),
      initialProvider: _providerForStyle(_activeStyle),
      onTileLoaded: () {
        if (mounted) setState(() => _tileCacheVersion++);
      },
    );

    _globeFocusNode.addListener(() { if (mounted) setState(() {}); });
    _treeViewModel = context.read<TreeViewModel?>();
    _treeViewModel?.addListener(_onTreeViewModelChangeInsideViewport);
  }

  void _onCameraChangedInside() {
    if (mounted && !_isUpdatingWidget) {
      widget.onCameraChanged?.call(_cameraController.current);
    }
  }

  @override
  void didUpdateWidget(covariant Scene3DViewport oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!oldWidget.camera.isSpatiallyEquivalentTo(widget.camera)) {
      if (_cameraController.isFlying) return;
      _isUpdatingWidget = true;
      _cameraController.updateCamera(widget.camera.toAbsoluteWgs84());
      _isUpdatingWidget = false;
    }
  }

  @override
  void dispose() {
    _treeViewModel?.removeListener(_onTreeViewModelChangeInsideViewport);
    _flyTicker?.dispose();
    _globeFocusNode.dispose();
    _cameraController.removeListener(_onCameraChangedInside);
    _cameraController.dispose();
    _tileRenderer?.dispose();
    _viewState.dispose();
    super.dispose();
  }

  void _onTreeViewModelChangeInsideViewport() {
    final treeViewModel = _treeViewModel;
    if (treeViewModel != null && treeViewModel.flightTarget != null) {
      final targetNodeId = treeViewModel.flightTarget!;
      treeViewModel.clearFlightTarget();
      final targetCam = _calculateCameraForNode(targetNodeId);
      if (targetCam != null) {
        _cameraController.flyTo(targetCam.toAbsoluteWgs84());
        _flyTicker?.stop();
        _flyTicker?.start();
      }
    }
  }

  VirtualCamera? _calculateCameraForNode(String nodeId) {
    if (widget.topologyData == null) return null;
    TopologyNode? activeNode;
    for (final node in widget.topologyData!.nodes) {
      if (node.id == nodeId) {
        activeNode = node;
        break;
      }
    }
    if (activeNode == null) return null;
    final double latVal = activeNode.resolveCoordinate('y', widget.topologyData!.coordinateMapping);
    final double lngVal = activeNode.resolveCoordinate('x', widget.topologyData!.coordinateMapping);
    if (latVal == 0.0 && lngVal == 0.0) {
      return VirtualCamera.raw(dim_0: 35.6074, dim_1: 140.1063, dim_2: 500.0, heading: 0.0, pitch: -89.9, roll: 0.0);
    }
    return VirtualCamera.raw(dim_0: latVal, dim_1: lngVal, dim_2: 500.0, heading: 0.0, pitch: -89.9, roll: 0.0);
  }

  KeyEventResult _handleKeyEvent(FocusNode node, KeyEvent event) {
    final key = event.logicalKey;
    if (key == LogicalKeyboardKey.escape) {
      _globeFocusNode.unfocus();
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.shiftLeft || key == LogicalKeyboardKey.shiftRight) {
      _shiftHeld = event is KeyDownEvent;
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.controlLeft || key == LogicalKeyboardKey.controlRight || key == LogicalKeyboardKey.metaLeft || key == LogicalKeyboardKey.metaRight) {
      _ctrlHeld = event is KeyDownEvent;
      return KeyEventResult.handled;
    }
    if (event is! KeyDownEvent && event is! KeyRepeatEvent) return KeyEventResult.ignored;

    if (key == LogicalKeyboardKey.arrowLeft) {
      setState(() { _shiftHeld ? _cameraController.keyboardRotateHeading(-CameraController.keyboardStep) : _cameraController.keyboardRotate(-CameraController.keyboardStep); });
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.arrowRight) {
      setState(() { _shiftHeld ? _cameraController.keyboardRotateHeading(CameraController.keyboardStep) : _cameraController.keyboardRotate(CameraController.keyboardStep); });
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.arrowUp) {
      setState(() { _cameraController.keyboardTilt(CameraController.keyboardStep); });
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.arrowDown) {
      setState(() { _cameraController.keyboardTilt(-CameraController.keyboardStep); });
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      focusNode: _globeFocusNode,
      autofocus: true,
      onKeyEvent: _handleKeyEvent,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapDown: (_) => _globeFocusNode.requestFocus(),
        onDoubleTapDown: (details) {
          print("DOUBLE TAP TRIGGERED"); final current = _cameraController.current;
          final surfaceAlt = current.dim_2 - Ellipsoid.wgs84EquatorialRadius;
          final targetAlt = (surfaceAlt * 0.5).clamp(
            CameraController.minAltitude,
            CameraController.maxAltitude,
          );
          _cameraController.flyTo(VirtualCamera.raw(
            dim_0: current.dim_0,
            dim_1: current.dim_1,
            dim_2: targetAlt + Ellipsoid.wgs84EquatorialRadius,
            heading: current.heading,
            pitch: current.pitch,
            roll: current.roll,
          ));
          _flyTicker?.stop();
          _flyTicker?.start();
        },
        onScaleStart: (_) => _globeFocusNode.requestFocus(),
        onScaleUpdate: (details) {
          if (details.scale != 1.0) _cameraController.zoomInteractive((details.scale - 1.0).sign * 20.0);
        },
        child: Stack(
          key: const Key('scene_3d_viewport_container'),
          children: [
            Positioned.fill(
              child: Listener(
                onPointerDown: (event) {
                  _globeFocusNode.requestFocus();
                  if (event.buttons & kSecondaryMouseButton != 0) _rightButtonDown = true;
                },
                onPointerUp: (_) => _rightButtonDown = false,
                onPointerCancel: (_) => _rightButtonDown = false,
                onPointerMove: (event) {
                  final delta = event.localDelta;
                  if (delta.distance <= 0.01) return;
                  if (event.buttons & kSecondaryMouseButton != 0 || _shiftHeld) {
                    _cameraController.tilt(delta);
                  } else if (_ctrlHeld) {
                    _cameraController.rotateHeading(delta);
                  } else if (event.buttons & kPrimaryMouseButton != 0) {
                    _cameraController.pan(delta, context.size?.shortestSide ?? 800.0);
                  }
                },
                onPointerSignal: (event) {
                  if (event is PointerScrollEvent) _cameraController.zoomInteractive(event.scrollDelta.dy);
                },
                child: RepaintBoundary(
                  key: const Key('scene_3d_viewport_boundary'),
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final size = constraints.biggest;
                      return ListenableBuilder(
                        listenable: Listenable.merge([_cameraController, _viewState]),
                        builder: (context, _) {
                          _viewState.recalculate(
                            _cameraController.current,
                            size,
                            widget.topologyData,
                            _activeStyle,
                            _astronomicalBody,
                            _elevationActive,
                            _showDevices,
                            _showLinks,
                            _showLabels,
                            _showDropLines,
                            widget.verticalExaggeration,
                            0.0,
                            0.0,
                            _tileRenderer,
                            _cameraController.isFlying,
                          );
                          return CustomPaint(
                            size: size,
                            painter: Scene3DViewportPainter(
                              layers: [BackgroundLayer(), GlobeLayer(), TopologyLayer(), HUDLayer()],
                              state: _viewState,
                            ),
                          );
                        },
                      );
                    }
                  ),
                ),
              ),
            ),
            if (_showCameraStats) CameraStatsPanel(
              cameraController: _cameraController,
              onClose: () => setState(() => _showCameraStats = false),
            ),
            if (!_showCameraStats) Positioned(top: 16, left: 16, child: ClipOval(child: Container(width: 40, height: 40, decoration: BoxDecoration(color: Colors.black.withOpacity(0.6), shape: BoxShape.circle, border: Border.all(color: const Color(0x33FFFFFF), width: 1.0)), child: IconButton(key: const Key('expand_camera_stats_button'), icon: const Icon(Icons.analytics_outlined, size: 18, color: Color(0xFF00E5FF)), padding: EdgeInsets.zero, onPressed: () => setState(() => _showCameraStats = true))))),
            if (_showMapConfig) MapConfigPanel(
              activeStyle: _activeStyle,
              astronomicalBody: _astronomicalBody,
              elevationActive: _elevationActive,
              showDevices: _showDevices,
              showLinks: _showLinks,
              showLabels: _showLabels,
              showDropLines: _showDropLines,
              onStyleChanged: (val) => setState(() { _activeStyle = val; _tileRenderer?.setProvider(_providerForStyle(val)); }),
              onBodyChanged: (val) => setState(() => _astronomicalBody = val),
              onElevationToggled: (val) => setState(() => _elevationActive = val),
              onDevicesToggled: (val) => setState(() => _showDevices = val),
              onLinksToggled: (val) => setState(() => _showLinks = val),
              onLabelsToggled: (val) => setState(() => _showLabels = val),
              onDropLinesToggled: (val) => setState(() => _showDropLines = val),
              onClose: () => setState(() => _showMapConfig = false),
              onResetCamera: () => setState(() {
                _astronomicalBody = 'Earth';
                _activeStyle = 'Satellite Map';
                _elevationActive = true;
                _showDevices = true;
                _showLinks = true;
                _showLabels = true;
                _showDropLines = true;
                _tileRenderer?.setProvider(ImageryProvider.arcGisSatellite);
              }),
            ),
            if (!_showMapConfig) Positioned(top: 16, right: 16, child: ClipOval(child: Container(width: 40, height: 40, decoration: BoxDecoration(color: Colors.black.withOpacity(0.6), shape: BoxShape.circle, border: Border.all(color: const Color(0x3300E5FF), width: 1.0)), child: IconButton(key: const Key('expand_map_config_button'), icon: const Icon(Icons.settings, size: 18, color: Color(0xFF00E5FF)), padding: EdgeInsets.zero, onPressed: () => setState(() => _showMapConfig = true))))),
          ],
        ),
      ),
    );
  }
}
