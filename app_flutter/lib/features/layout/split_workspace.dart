import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/app_themes.dart';

/// Realises: [Feat-10/SplitWorkspace]
///
/// A resizable split pane that lays out [leading] and [trailing] widgets
/// along [direction] with a draggable divider.
@immutable
class SplitWorkspace extends StatefulWidget {
  /// Member documentation.
  final Widget leading;
  /// Member documentation.
  final Widget trailing;
  /// Member documentation.
  final Axis direction;
  /// Member documentation.
  final double minFirstPaneSize;
  /// Member documentation.
  final double initialRatio;
  /// Thickness of the draggable divider strip in logical pixels.
  ///
  /// When [direction] is [Axis.horizontal] this is the divider's width; when
  /// [direction] is [Axis.vertical] this is its height. The divider
  /// background uses [Theme.dividerColor] and is inset by 1 px borders on
  /// both sides. Defaults to 8.0.
  final double? dividerSize;

  /// Width of the inner drag-grip rectangle in logical pixels.
  ///
  /// The grip is centered inside the divider strip and rendered with the
  /// theme's icon color at 30% opacity. When [direction] is [Axis.horizontal]
  /// this value is used as the grip's width; for [Axis.vertical] it becomes
  /// the grip's height (the orientation is swapped). Defaults to 2.0.
  final double? gripWidth;

  /// Height of the inner drag-grip rectangle in logical pixels.
  ///
  /// The grip is centered inside the divider strip and rendered with the
  /// theme's icon color at 30% opacity. When [direction] is [Axis.horizontal]
  /// this value is used as the grip's height; for [Axis.vertical] it becomes
  /// the grip's width (the orientation is swapped). Defaults to 40.0.
  final double? gripHeight;
  /// Member documentation.
  final Key? splitterKey;
  /// Member documentation.
  final ValueChanged<double>? onDrag;

  /// Member documentation.
  final bool paintLeadingOnTop;

  /// Member documentation.
  const SplitWorkspace({
    super.key,
    required this.leading,
    required this.trailing,
    required this.direction,
    required this.minFirstPaneSize,
    required this.initialRatio,
    this.dividerSize,
    this.gripWidth,
    this.gripHeight,
    this.splitterKey,
    this.onDrag,
    this.paintLeadingOnTop = false,
  });

  @override
  State<SplitWorkspace> createState() => _SplitWorkspaceState();
}

class _SplitWorkspaceState extends State<SplitWorkspace> {
  double _firstPaneSize = 0;
  double? _draggedPaneSize;
  bool _initialized = false;

  @override
  Widget build(BuildContext context) {
    final panelOpacity = context.watch<ThemeController>().panelOpacity;
    final resolvedDividerSize = widget.dividerSize ?? AppThemes.getDimension('component.splitter.divider-size', 8.0);
    final resolvedGripWidth = widget.gripWidth ?? AppThemes.getDimension('component.splitter.grip-width', 2.0);
    final resolvedGripHeight = widget.gripHeight ?? AppThemes.getDimension('component.splitter.grip-height', 40.0);

    return LayoutBuilder(
      builder: (context, constraints) {
        final totalSize = widget.direction == Axis.horizontal
            ? constraints.maxWidth
            : constraints.maxHeight;

        if (!_initialized && totalSize > 0) {
          _firstPaneSize = totalSize * widget.initialRatio;
          _initialized = true;
        }

        final maxPossibleFirstPane = (totalSize - resolvedDividerSize).clamp(0, totalSize).toDouble();
        final safeMinFirstPane = math.min(widget.minFirstPaneSize, maxPossibleFirstPane);

        final clampedFirstPane = _firstPaneSize.clamp(
          safeMinFirstPane,
          math.max(safeMinFirstPane, totalSize - widget.minFirstPaneSize),
        ).toDouble();

        final isHorizontal = widget.direction == Axis.horizontal;
        final splitterPosition = _draggedPaneSize ?? clampedFirstPane;

        final splitter = GestureDetector(
          key: widget.splitterKey,
          onHorizontalDragUpdate: isHorizontal
              ? (details) {
                  setState(() {
                    _draggedPaneSize = ((_draggedPaneSize ?? clampedFirstPane) + details.delta.dx)
                        .clamp(widget.minFirstPaneSize, math.max(widget.minFirstPaneSize, totalSize - widget.minFirstPaneSize)).toDouble();
                  });
                }
              : null,
          onHorizontalDragEnd: isHorizontal
              ? (details) {
                  if (_draggedPaneSize != null) {
                    setState(() {
                      _firstPaneSize = _draggedPaneSize!;
                      _draggedPaneSize = null;
                    });
                    widget.onDrag?.call(_firstPaneSize);
                  }
                }
              : null,
          onHorizontalDragCancel: isHorizontal
              ? () {
                  if (_draggedPaneSize != null) {
                    setState(() {
                      _firstPaneSize = _draggedPaneSize!;
                      _draggedPaneSize = null;
                    });
                    widget.onDrag?.call(_firstPaneSize);
                  }
                }
              : null,
          onVerticalDragUpdate: !isHorizontal
              ? (details) {
                  setState(() {
                    _draggedPaneSize = ((_draggedPaneSize ?? clampedFirstPane) + details.delta.dy)
                        .clamp(widget.minFirstPaneSize, math.max(widget.minFirstPaneSize, totalSize - widget.minFirstPaneSize)).toDouble();
                  });
                }
              : null,
          onVerticalDragEnd: !isHorizontal
              ? (details) {
                  if (_draggedPaneSize != null) {
                    setState(() {
                      _firstPaneSize = _draggedPaneSize!;
                      _draggedPaneSize = null;
                    });
                    widget.onDrag?.call(_firstPaneSize);
                  }
                }
              : null,
          onVerticalDragCancel: !isHorizontal
              ? () {
                  if (_draggedPaneSize != null) {
                    setState(() {
                      _firstPaneSize = _draggedPaneSize!;
                      _draggedPaneSize = null;
                    });
                    widget.onDrag?.call(_firstPaneSize);
                  }
                }
              : null,
          child: MouseRegion(
            cursor: isHorizontal
                ? SystemMouseCursors.resizeLeftRight
                : SystemMouseCursors.resizeUpDown,
            child: Container(
              width: isHorizontal ? resolvedDividerSize : double.infinity,
              height: isHorizontal ? double.infinity : resolvedDividerSize,
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor.withOpacity(panelOpacity),
                border: isHorizontal
                    ? Border(
                        left: BorderSide(
                          color: Theme.of(context).dividerColor,
                          width: 1,
                        ),
                        right: BorderSide(
                          color: Theme.of(context).dividerColor,
                          width: 1,
                        ),
                      )
                    : Border(
                        top: BorderSide(
                          color: Theme.of(context).dividerColor,
                          width: 1,
                        ),
                        bottom: BorderSide(
                          color: Theme.of(context).dividerColor,
                          width: 1,
                        ),
                      ),
              ),
              child: Center(
                child: Container(
                  width: isHorizontal ? resolvedGripWidth : resolvedGripHeight,
                  height: isHorizontal ? resolvedGripHeight : resolvedGripWidth,
                  color: Theme.of(context).iconTheme.color?.withValues(alpha: 0.3) ??
                      Theme.of(context).dividerColor,
                ),
              ),
            ),
          ),
        );

        final leadingPane = isHorizontal
            ? SizedBox(width: clampedFirstPane, child: RepaintBoundary(key: const ValueKey('split_leading'), child: widget.leading))
            : SizedBox(height: clampedFirstPane, child: RepaintBoundary(key: const ValueKey('split_leading'), child: widget.leading));

        final trailingPane = RepaintBoundary(key: const ValueKey('split_trailing'), child: widget.trailing);

        final splitterWidget = Positioned(
          left: isHorizontal ? splitterPosition : 0,
          right: isHorizontal ? null : 0,
          top: isHorizontal ? 0 : splitterPosition,
          bottom: isHorizontal ? 0 : null,
          width: isHorizontal ? resolvedDividerSize : null,
          height: isHorizontal ? null : resolvedDividerSize,
          child: RepaintBoundary(child: splitter),
        );

        final leadingWidget = Positioned(
          left: 0,
          right: isHorizontal ? null : 0,
          top: 0,
          bottom: isHorizontal ? 0 : null,
          width: isHorizontal ? clampedFirstPane : null,
          height: isHorizontal ? null : clampedFirstPane,
          child: leadingPane,
        );

        final double? trailingWidth = isHorizontal
            ? math.max(0.0, totalSize - clampedFirstPane - resolvedDividerSize)
            : null;
        final double? trailingHeight = isHorizontal
            ? null
            : math.max(0.0, totalSize - clampedFirstPane - resolvedDividerSize);

        final trailingWidget = Positioned(
          left: isHorizontal ? clampedFirstPane + resolvedDividerSize : 0,
          right: isHorizontal ? null : 0,
          top: isHorizontal ? 0 : clampedFirstPane + resolvedDividerSize,
          bottom: isHorizontal ? 0 : null,
          width: trailingWidth,
          height: trailingHeight,
          child: trailingPane,
        );

        final List<Widget> children = widget.paintLeadingOnTop
            ? [trailingWidget, splitterWidget, leadingWidget]
            : [leadingWidget, splitterWidget, trailingWidget];

        return Stack(
          children: children,
        );
      },
    );
  }
}
