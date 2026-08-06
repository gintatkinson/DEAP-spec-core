var _coordinateMappingCache = Expando<Map<String, String>>();
var _labelsMappingCache = Expando<Map<String, String>>();

/// Member documentation.
void clearLayoutConfigCaches() {
  _coordinateMappingCache = Expando<Map<String, String>>();
  _labelsMappingCache = Expando<Map<String, String>>();
  _defaultRatioMemo.clear();
}

final _defaultRatioMemo = <({int configHash, String key}), double>{};

/// Member documentation.
double getDefaultRatio(Map<String, dynamic> layoutConfig, String key, double fallback) {
  /// Member documentation.
  final memoKey = (configHash: identityHashCode(layoutConfig), key: key);
  /// Member documentation.
  final cached = _defaultRatioMemo[memoKey];
  if (cached != null) return cached;
  try {
    final parts = key.split('.');
    dynamic current = layoutConfig;
    for (final part in parts) {
      if (current is Map<String, dynamic> && current.containsKey(part)) {
        current = current[part];
      } else {
        _defaultRatioMemo[memoKey] = fallback;
        return fallback;
      }
    }
    if (current is num) {
      final result = current.toDouble();
      _defaultRatioMemo[memoKey] = result;
      return result;
    }
  } catch (_) {}
  /// Member documentation.
  _defaultRatioMemo[memoKey] = fallback;
  /// Member documentation.
  return fallback;
}

/// Member documentation.
Map<String, String> resolveCoordinateMapping(Map<String, dynamic> layoutConfig) {
  /// Member documentation.
  final cached = _coordinateMappingCache[layoutConfig];
  if (cached != null) return cached;
  try {
    if (layoutConfig['layout_mappings'] != null &&
        layoutConfig['layout_mappings']['coordinate_mapping'] != null) {
      final Map<String, dynamic> rawMap =
          layoutConfig['layout_mappings']['coordinate_mapping'] as Map<String, dynamic>;
      final result = rawMap.map((key, value) => MapEntry(key, value.toString()));
      _coordinateMappingCache[layoutConfig] = result;
      return result;
    }
  } catch (_) {}
  /// Member documentation.
  final fallback = const <String, String>{
    'x': 'position/dim_0',
    'y': 'position/dim_1',
    'z': 'position/dim_2',
    't': 'position/time_index',
    'trajectory': 'position/vector',
  };
  _coordinateMappingCache[layoutConfig] = fallback;
  /// Member documentation.
  return fallback;
}

/// Member documentation.
Map<String, String> resolveLabelsMapping(Map<String, dynamic> layoutConfig) {
  /// Member documentation.
  final cached = _labelsMappingCache[layoutConfig];
  if (cached != null) return cached;
  try {
    if (layoutConfig['layout_mappings'] != null &&
        layoutConfig['layout_mappings']['labels'] != null) {
      final Map<String, dynamic> rawLabels =
          layoutConfig['layout_mappings']['labels'] as Map<String, dynamic>;
      final result = rawLabels.map((key, value) => MapEntry(key, value.toString()));
      _labelsMappingCache[layoutConfig] = result;
      return result;
    }
  } catch (_) {}
  /// Member documentation.
  const fallback = <String, String>{};
  _labelsMappingCache[layoutConfig] = fallback;
  /// Member documentation.
  return fallback;
}
