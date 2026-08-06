/// Provides runtime key-value metadata storage and retrieval.
///
/// Realises: [runtime-metadata-blueprint.md/RuntimeMetadataProvider]
///
/// A lightweight in-memory metadata registry that allows application
/// subsystems to publish and consume runtime configuration, feature flags,
/// and diagnostic context without tight coupling.
///
/// Usage:
/// ```dart
/// final provider = RuntimeMetadataProvider();
/// provider.registerMetadata('build.version', '1.0.0');
/// final version = provider.getMetadata('build.version'); // '1.0.0'
/// ```
class RuntimeMetadataProvider {
  /// Internal metadata store.
  final Map<String, dynamic> _store = <String, dynamic>{};

  /// Returns the metadata value associated with [key], or `null` if [key]
  /// has not been registered.
  ///
  /// The returned type is `dynamic` because metadata values are
  /// intentionally heterogeneous (strings, numbers, booleans, maps, etc.).
  dynamic getMetadata(String key) => _store[key];

  /// Registers (or overwrites) metadata under [key] with [value].
  ///
  /// Any previous value for [key] is silently replaced.
  void registerMetadata(String key, dynamic value) {
    _store[key] = value;
  }

  /// Returns `true` when a value has been registered for [key].
  bool containsKey(String key) => _store.containsKey(key);

  /// Removes the metadata entry for [key] and returns its previous value.
  ///
  /// Returns `null` if [key] was not registered.
  dynamic removeMetadata(String key) => _store.remove(key);

  /// Returns the number of registered metadata entries.
  int get length => _store.length;

  /// Returns all registered keys as an unmodifiable iterable.
  Iterable<String> get keys => _store.keys;
}
