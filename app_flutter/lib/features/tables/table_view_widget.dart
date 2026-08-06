import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:app_flutter/features/tables/models/column_model.dart';
import 'package:app_flutter/features/tables/view_models/tables_view_model.dart';

/// Renders tabular data from a [TablesViewModel] as a horizontally
/// scrollable, vertically virtualized table.
///
/// Fixes O(n) widget creation from [DataTable] by using [ListView.builder]
/// for O(1) visible-row widget creation. The column header row is fixed at
/// the top; body rows scroll virtually.
///
/// Edge cases:
///   - When [TablesViewModel.loading] is `true`, a centered
///     [CircularProgressIndicator] is displayed instead of the table.
///   - When [TablesViewModel.error] is non-null, the error text is shown in
///     the theme's error color; the table is not rendered.
///   - An empty [headers] list renders an empty [SizedBox] — no crash.
///   - Long content is scrollable horizontally via [SingleChildScrollView];
///     vertical scrolling is handled by [ListView.builder].
///
/// State changes: this widget is read-only; it watches [TablesViewModel] via
/// `context.watch` and rebuilds on every notifyListeners call from the view
/// model.
///
/// Realises: [Feat-10/TableViewWidget]
class TableViewWidget extends StatefulWidget {
  /// Member documentation.
  const TableViewWidget({
    super.key,
    this.headingRowHeight = 32.0,
    this.dataRowMinHeight = 28.0,
    this.dataRowMaxHeight = double.infinity,
    this.horizontalMargin = 12.0,
    this.columnSpacing = 24.0,
  });

  /// Member documentation.
  final double headingRowHeight;
  /// Member documentation.
  final double dataRowMinHeight;
  /// Member documentation.
  final double dataRowMaxHeight;
  /// Member documentation.
  final double horizontalMargin;
  /// Member documentation.
  final double columnSpacing;

  @override
  State<TableViewWidget> createState() => _TableViewWidgetState();
}

class _TableViewWidgetState extends State<TableViewWidget> {
  int? _sortColumnIndex;
  bool _sortAscending = true;

  List<List<String>>? _cachedSourceRows;
  List<ColumnModel>? _cachedHeaders;
  List<List<String>>? _cachedSortedRows;
  int? _cachedSortColumnIndex;
  bool? _cachedSortAscending;

  Map<String, int>? _cachedHeaderIndices;
  List<ColumnModel>? _cachedAllHeadersForIndices;

  List<List<String>> _getSortedRows(
    List<List<String>> rows,
    List<ColumnModel> headers,
    Map<String, int> headerIndices,
  ) {
    if (_sortColumnIndex == null || _sortColumnIndex! >= headers.length) {
      _clearCache();
      return rows;
    }

    if (_rowsEqual(_cachedSourceRows, rows) &&
        _cachedSortColumnIndex == _sortColumnIndex &&
        _cachedSortAscending == _sortAscending &&
        _cachedSortedRows != null) {
      return _cachedSortedRows!;
    }

    _cachedSourceRows = rows;
    _cachedSortColumnIndex = _sortColumnIndex;
    _cachedSortAscending = _sortAscending;

    final sortedRows = List<List<String>>.from(rows);
    final key = headers[_sortColumnIndex!].key;
    final absIdx = headerIndices[key] ?? _sortColumnIndex!;
    sortedRows.sort((a, b) {
      final aVal = absIdx < a.length ? a[absIdx] : '';
      final bVal = absIdx < b.length ? b[absIdx] : '';
      final aNum = double.tryParse(aVal);
      final bNum = double.tryParse(bVal);
      if (aNum != null && bNum != null) {
        return _sortAscending ? aNum.compareTo(bNum) : bNum.compareTo(aNum);
      } else {
        return _sortAscending ? aVal.compareTo(bVal) : bVal.compareTo(aVal);
      }
    });

    _cachedSortedRows = sortedRows;
    return sortedRows;
  }

  Map<String, int> _getHeaderIndices(List<ColumnModel> allHeaders) {
    if (_cachedAllHeadersForIndices != null &&
        _cachedHeaderIndices != null &&
        _cachedAllHeadersForIndices!.length == allHeaders.length) {
      var same = true;
      for (int i = 0; i < allHeaders.length; i++) {
        if (!identical(_cachedAllHeadersForIndices![i], allHeaders[i])) {
          same = false;
          break;
        }
      }
      if (same) return _cachedHeaderIndices!;
    }
    _cachedAllHeadersForIndices = allHeaders;
    _cachedHeaderIndices = {
      for (int idx = 0; idx < allHeaders.length; idx++)
        allHeaders[idx].key: idx
    };
    return _cachedHeaderIndices!;
  }

  bool _rowsEqual(List<List<String>>? a, List<List<String>>? b) {
    if (identical(a, b)) return true;
    if (a == null || b == null) return false;
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i].length != b[i].length) return false;
      for (int j = 0; j < a[i].length; j++) {
        if (a[i][j] != b[i][j]) return false;
      }
    }
    return true;
  }

  void _clearCache() {
    _cachedSourceRows = null;
    _cachedHeaders = null;
    _cachedSortedRows = null;
    _cachedSortColumnIndex = null;
    _cachedSortAscending = null;
    _cachedHeaderIndices = null;
    _cachedAllHeadersForIndices = null;
  }

  @override
  void dispose() {
    _clearCache();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final viewModel = context.watch<TablesViewModel>();

    if (viewModel.loading) {
      _clearCache();
      return const Center(child: CircularProgressIndicator());
    }

    if (viewModel.error != null) {
      _clearCache();
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Text(
            viewModel.error!,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.error,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    final headers = viewModel.visibleColumnModels;
    final allHeaders = viewModel.headers;
    final headerIndices = _getHeaderIndices(allHeaders);

    final rows = _getSortedRows(viewModel.rows, headers, headerIndices);
    final testId = '${viewModel.tabId}-table';
    final numericTextStyle = Theme.of(context).textTheme.bodySmall?.copyWith(
      fontFamily: 'monospace',
    );

    if (headers.isEmpty) {
      return const SizedBox.shrink();
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final colCount = headers.length;
        final spacingWidth = colCount > 1
            ? (colCount - 1) * widget.columnSpacing
            : 0.0;
        final colWidth = math.max(120.0, (constraints.maxWidth - 2 * widget.horizontalMargin - spacingWidth) / colCount);
        final tableWidth = math.max(constraints.maxWidth, colCount * colWidth + spacingWidth + 2 * widget.horizontalMargin);

        void onSort(int columnIndex) {
          _clearCache();
          setState(() {
            if (_sortColumnIndex == columnIndex) {
              _sortAscending = !_sortAscending;
            } else {
              _sortColumnIndex = columnIndex;
              _sortAscending = true;
            }
          });
        }

        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: SizedBox(
            key: Key(testId),
            width: tableWidth,
            height: constraints.maxHeight,
            child: Stack(
              children: [
                RepaintBoundary(
                  child: ListView.builder(
                    key: Key('$testId-body'),
                    itemCount: rows.length,
                    padding: EdgeInsets.only(top: widget.headingRowHeight),
                    itemBuilder: (context, index) {
                      final row = rows[index];
                      return _DataRow(
                        cells: row,
                        columnModels: headers,
                        headerIndices: headerIndices,
                        colWidth: colWidth,
                        dataRowMinHeight: widget.dataRowMinHeight,
                        dataRowMaxHeight: widget.dataRowMaxHeight,
                        horizontalMargin: widget.horizontalMargin,
                        columnSpacing: widget.columnSpacing,
                        index: index,
                        numericTextStyle: numericTextStyle,
                      );
                    },
                  ),
                ),
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: _HeaderRow(
                    headers: headers,
                    colWidth: colWidth,
                    headingRowHeight: widget.headingRowHeight,
                    horizontalMargin: widget.horizontalMargin,
                    columnSpacing: widget.columnSpacing,
                    testId: testId,
                    sortColumnIndex: _sortColumnIndex,
                    sortAscending: _sortAscending,
                    onSort: onSort,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _HeaderRow extends StatelessWidget {
  /// Member documentation.
  final List<ColumnModel> headers;
  /// Member documentation.
  final double colWidth;
  /// Member documentation.
  final double headingRowHeight;
  /// Member documentation.
  final double horizontalMargin;
  /// Member documentation.
  final double columnSpacing;
  /// Member documentation.
  final String testId;
  /// Member documentation.
  final int? sortColumnIndex;
  /// Member documentation.
  final bool sortAscending;
  /// Member documentation.
  final void Function(int columnIndex) onSort;

  const _HeaderRow({
    required this.headers,
    required this.colWidth,
    required this.headingRowHeight,
    required this.horizontalMargin,
    required this.columnSpacing,
    required this.testId,
    required this.sortColumnIndex,
    required this.sortAscending,
    required this.onSort,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      key: Key('$testId-header'),
      height: headingRowHeight,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (int i = 0; i < headers.length; i++)
            _HeaderCell(
              label: headers[i].label,
              columnWidth: headers[i].width,
              colWidth: colWidth,
              horizontalMargin: horizontalMargin,
              columnSpacing: columnSpacing,
              isFirst: i == 0,
              isLast: i == headers.length - 1,
              sortable: headers[i].sortable,
              isActiveSort: sortColumnIndex == i,
              sortAscending: sortAscending,
              onTap: headers[i].sortable ? () => onSort(i) : null,
              isNumeric: headers[i].type == 'int' || headers[i].type == 'double',
            ),
        ],
      ),
    );
  }
}

class _HeaderCell extends StatelessWidget {
  /// Member documentation.
  final String label;
  /// Member documentation.
  final double? columnWidth;
  /// Member documentation.
  final double colWidth;
  /// Member documentation.
  final double horizontalMargin;
  /// Member documentation.
  final double columnSpacing;
  /// Member documentation.
  final bool isFirst;
  /// Member documentation.
  final bool isLast;
  /// Member documentation.
  final bool sortable;
  /// Member documentation.
  final bool isActiveSort;
  /// Member documentation.
  final bool sortAscending;
  /// Member documentation.
  final VoidCallback? onTap;
  /// Member documentation.
  final bool isNumeric;

  const _HeaderCell({
    required this.label,
    this.columnWidth,
    required this.colWidth,
    required this.horizontalMargin,
    required this.columnSpacing,
    required this.isFirst,
    required this.isLast,
    required this.sortable,
    required this.isActiveSort,
    required this.sortAscending,
    required this.onTap,
    required this.isNumeric,
  });

  @override
  Widget build(BuildContext context) {
    final displayLabel = isActiveSort
        ? '$label ${sortAscending ? '↑' : '↓'}'
        : label;

    return SizedBox(
      width: columnWidth ?? colWidth,
      child: Padding(
        padding: EdgeInsets.only(
          left: isFirst ? horizontalMargin : columnSpacing / 2,
          right: isLast ? horizontalMargin : columnSpacing / 2,
        ),
        child: Align(
          alignment: isNumeric ? Alignment.centerRight : Alignment.centerLeft,
          child: sortable
              ? GestureDetector(
                  onTap: onTap,
                  child: Text(displayLabel, style: Theme.of(context).textTheme.labelSmall),
                )
              : Text(label, style: Theme.of(context).textTheme.labelSmall),
        ),
      ),
    );
  }
}

class _DataRow extends StatelessWidget {
  /// Member documentation.
  final List<String> cells;
  /// Member documentation.
  final List<ColumnModel> columnModels;
  /// Member documentation.
  final Map<String, int> headerIndices;
  /// Member documentation.
  final double colWidth;
  /// Member documentation.
  final double dataRowMinHeight;
  /// Member documentation.
  final double dataRowMaxHeight;
  /// Member documentation.
  final double horizontalMargin;
  /// Member documentation.
  final double columnSpacing;
  /// Member documentation.
  final int index;
  /// Member documentation.
  final TextStyle? numericTextStyle;

  static final Color _stripeColor = Colors.black.withOpacity(0.03);

  const _DataRow({
    required this.cells,
    required this.columnModels,
    required this.headerIndices,
    required this.colWidth,
    required this.dataRowMinHeight,
    required this.dataRowMaxHeight,
    required this.horizontalMargin,
    required this.columnSpacing,
    required this.index,
    required this.numericTextStyle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(
        minHeight: dataRowMinHeight,
      ),
      color: index.isEven ? null : _stripeColor,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(columnModels.length, (i) {
          final cellIdx = headerIndices[columnModels[i].key];
          final cellValue = cellIdx != null && cellIdx < cells.length ? cells[cellIdx] : '';
          return _DataCell(
            value: cellValue,
            columnModel: columnModels[i],
            colWidth: colWidth,
            horizontalMargin: horizontalMargin,
            columnSpacing: columnSpacing,
            isFirst: i == 0,
            isLast: i == columnModels.length - 1,
            numericTextStyle: numericTextStyle,
          );
        }),
      ),
    );
  }
}

class _DataCell extends StatelessWidget {
  /// Member documentation.
  final String value;
  /// Member documentation.
  final ColumnModel columnModel;
  /// Member documentation.
  final double colWidth;
  /// Member documentation.
  final double horizontalMargin;
  /// Member documentation.
  final double columnSpacing;
  /// Member documentation.
  final bool isFirst;
  /// Member documentation.
  final bool isLast;
  /// Member documentation.
  final TextStyle? numericTextStyle;

  const _DataCell({
    required this.value,
    required this.columnModel,
    required this.colWidth,
    required this.horizontalMargin,
    required this.columnSpacing,
    required this.isFirst,
    required this.isLast,
    required this.numericTextStyle,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isNumeric = columnModel.type == 'int' || columnModel.type == 'double';

    Widget cellContent;
    switch (columnModel.type) {
      case 'int':
      case 'double':
        cellContent = Text(
          value,
          style: numericTextStyle ?? theme.textTheme.bodySmall,
          textAlign: TextAlign.right,
        );
        break;
      case 'enum':
        cellContent = Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
            color: theme.colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(value, style: theme.textTheme.bodySmall),
        );
        break;
      case 'date':
        cellContent = Text(
          _formatDate(value),
          style: theme.textTheme.bodySmall,
        );
        break;
      default:
        cellContent = Text(value, style: theme.textTheme.bodySmall);
    }

    return SizedBox(
      width: columnModel.width ?? colWidth,
      child: Padding(
        padding: EdgeInsets.only(
          left: isFirst ? horizontalMargin : columnSpacing / 2,
          right: isLast ? horizontalMargin : columnSpacing / 2,
        ),
        child: Align(
          alignment: isNumeric ? Alignment.centerRight : Alignment.centerLeft,
          child: cellContent,
        ),
      ),
    );
  }

  String _formatDate(String value) {
    if (value.isEmpty) return value;
    try {
      final dt = DateTime.parse(value);
      final y = dt.year.toString();
      final m = dt.month.toString().padLeft(2, '0');
      final d = dt.day.toString().padLeft(2, '0');
      return '$y-$m-$d';
    } catch (_) {
      return value;
    }
  }
}
