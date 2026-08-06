import 'dart:ui';
import 'package:flutter_test/flutter_test.dart';

/// Buffered recording implementation of [Canvas] that records drawing commands.
class BufferedRecordingCanvas extends Fake implements Canvas {
  final List<(Paragraph, Offset)> paragraphs = [];
  final List<(Offset, double)> circles = [];
  final List<List<Offset>> points = [];
  final List<Rect> clipRects = [];

  @override
  void drawParagraph(Paragraph paragraph, Offset offset) {
    paragraphs.add((paragraph, offset));
  }

  @override
  void drawCircle(Offset center, double radius, Paint paint) {
    circles.add((center, radius));
  }

  @override
  void drawPoints(PointMode pointMode, List<Offset> pointsList, Paint paint) {
    points.add(List.from(pointsList));
  }

  @override
  void clipRect(Rect rect, {ClipOp clipOp = ClipOp.intersect, bool doAntiAlias = true}) {
    clipRects.add(rect);
  }
  @override
  void drawPath(Path path, Paint paint) {}
  @override
  void drawLine(Offset p1, Offset p2, Paint paint) {}
  @override
  void drawRRect(RRect rrect, Paint paint) {}
  @override
  void save() {}
  @override
  void restore() {}
  @override
  void translate(double dx, double dy) {}
  @override
  void rotate(double radians) {}
  @override
  void scale(double sx, [double? sy]) {}
}
