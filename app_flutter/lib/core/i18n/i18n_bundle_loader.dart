import 'dart:convert';
import 'package:flutter/services.dart';

/// Multi-language internationalisation bundle loader.
///
/// Realises: [string-externalization-plan.md/I18nBundleLoader]
///
/// Loads locale-specific JSON string bundles from the application's asset
/// directory and exposes them through a simple key-value lookup.
///
/// Usage:
/// ```dart
/// final loader = I18nBundleLoader();
/// await loader.loadBundle('en');
/// final greeting = loader.getString('hello'); // "Hello"
/// ```
///
/// Bundles are expected at `assets/i18n/<locale>.json`, where each file is a
/// flat JSON object mapping string keys to translated values.
///
/// The loader keeps only one locale in memory at a time.  Calling
/// [loadBundle] with a different locale replaces the previous strings.
class I18nBundleLoader {
  /// Internal string map for the currently loaded locale.
  Map<String, String> _strings = <String, String>{};

  /// The locale tag that is currently loaded, or `null` if no bundle has
  /// been loaded yet.
  String? _currentLocale;

  /// The locale tag that is currently loaded.
  ///
  /// Returns `null` when no bundle has been loaded yet.
  String? get currentLocale => _currentLocale;

  /// Loads the string bundle for [locale] from application assets.
  ///
  /// Reads `assets/i18n/<locale>.json` via [rootBundle], parses it as a
  /// flat JSON object, and caches the resulting key-value map.  Any
  /// previously loaded strings are replaced.
  ///
  /// Throws a [FlutterError] if the asset cannot be found, or a
  /// [FormatException] if the JSON is malformed.
  Future<void> loadBundle(String locale) async {
    final String jsonString =
        await rootBundle.loadString('assets/i18n/$locale.json');
    _strings = Map<String, String>.from(
      jsonDecode(jsonString) as Map<String, dynamic>,
    );
    _currentLocale = locale;
  }

  /// Loads a bundle from a raw JSON string — intended for testing.
  ///
  /// Replaces any previously cached strings and sets [currentLocale] to
  /// [locale].  Does **not** touch [rootBundle] or the filesystem.
  void loadBundleFromJson(String json, {required String locale}) {
    _strings = Map<String, String>.from(
      jsonDecode(json) as Map<String, dynamic>,
    );
    _currentLocale = locale;
  }

  /// Returns the translated string for [key].
  ///
  /// If [key] is not found in the currently loaded bundle, [fallback] is
  /// returned when provided; otherwise [key] itself is returned so that
  /// missing translations degrade gracefully instead of crashing.
  String getString(String key, {String? fallback}) =>
      _strings[key] ?? fallback ?? key;

  /// Returns `true` when a bundle is loaded and a value exists for [key].
  bool containsKey(String key) => _strings.containsKey(key);

  /// Returns the number of string entries in the currently loaded bundle.
  int get length => _strings.length;
}
