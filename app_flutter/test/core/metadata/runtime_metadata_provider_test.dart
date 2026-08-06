import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/core/metadata/runtime_metadata_provider.dart';

void main() {
  group('RuntimeMetadataProvider', () {
    late RuntimeMetadataProvider provider;

    setUp(() {
      provider = RuntimeMetadataProvider();
    });

    test('getMetadata returns null for unregistered key', () {
      expect(provider.getMetadata('missing'), isNull);
    });

    test('registerMetadata stores a string value', () {
      provider.registerMetadata('version', '1.0.0');

      expect(provider.getMetadata('version'), equals('1.0.0'));
    });

    test('registerMetadata stores an int value', () {
      provider.registerMetadata('count', 42);

      expect(provider.getMetadata('count'), equals(42));
    });

    test('registerMetadata stores a bool value', () {
      provider.registerMetadata('enabled', true);

      expect(provider.getMetadata('enabled'), isTrue);
    });

    test('registerMetadata stores a map value', () {
      final Map<String, int> m = <String, int>{'a': 1};
      provider.registerMetadata('config', m);

      expect(provider.getMetadata('config'), equals(m));
    });

    test('registerMetadata overwrites existing value', () {
      provider.registerMetadata('key', 'old');
      provider.registerMetadata('key', 'new');

      expect(provider.getMetadata('key'), equals('new'));
    });

    test('containsKey returns true for registered key', () {
      provider.registerMetadata('key', 'val');

      expect(provider.containsKey('key'), isTrue);
    });

    test('containsKey returns false for unregistered key', () {
      expect(provider.containsKey('nope'), isFalse);
    });

    test('removeMetadata returns previous value and removes entry', () {
      provider.registerMetadata('key', 'val');

      expect(provider.removeMetadata('key'), equals('val'));
      expect(provider.containsKey('key'), isFalse);
    });

    test('removeMetadata returns null for missing key', () {
      expect(provider.removeMetadata('missing'), isNull);
    });

    test('length reflects number of entries', () {
      expect(provider.length, equals(0));

      provider.registerMetadata('a', 1);
      expect(provider.length, equals(1));

      provider.registerMetadata('b', 2);
      expect(provider.length, equals(2));
    });

    test('keys returns registered key names', () {
      provider.registerMetadata('alpha', 1);
      provider.registerMetadata('beta', 2);

      expect(provider.keys, containsAll(<String>['alpha', 'beta']));
    });
  });
}
