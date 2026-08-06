import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/core/i18n/i18n_bundle_loader.dart';

void main() {
  group('I18nBundleLoader', () {
    late I18nBundleLoader loader;

    setUp(() {
      loader = I18nBundleLoader();
    });

    test('initial state has null currentLocale', () {
      expect(loader.currentLocale, isNull);
    });

    test('initial state has zero length', () {
      expect(loader.length, equals(0));
    });

    test('loadBundleFromJson loads strings and sets locale', () {
      loader.loadBundleFromJson(
        '{"hello": "Hello", "goodbye": "Goodbye"}',
        locale: 'en',
      );

      expect(loader.currentLocale, equals('en'));
      expect(loader.length, equals(2));
    });

    test('getString returns value for existing key', () {
      loader.loadBundleFromJson(
        '{"greeting": "Hola"}',
        locale: 'es',
      );

      expect(loader.getString('greeting'), equals('Hola'));
    });

    test('getString returns key itself when key is missing', () {
      loader.loadBundleFromJson('{}', locale: 'en');

      expect(loader.getString('missing_key'), equals('missing_key'));
    });

    test('getString returns fallback when provided and key is missing', () {
      loader.loadBundleFromJson('{}', locale: 'en');

      expect(
        loader.getString('missing_key', fallback: 'default'),
        equals('default'),
      );
    });

    test('getString prefers bundle value over fallback', () {
      loader.loadBundleFromJson(
        '{"key": "value"}',
        locale: 'en',
      );

      expect(
        loader.getString('key', fallback: 'default'),
        equals('value'),
      );
    });

    test('containsKey returns true for existing key', () {
      loader.loadBundleFromJson(
        '{"exists": "yes"}',
        locale: 'en',
      );

      expect(loader.containsKey('exists'), isTrue);
    });

    test('containsKey returns false for missing key', () {
      loader.loadBundleFromJson('{}', locale: 'en');

      expect(loader.containsKey('nope'), isFalse);
    });

    test('loadBundleFromJson replaces previous bundle', () {
      loader.loadBundleFromJson(
        '{"a": "1"}',
        locale: 'en',
      );
      expect(loader.getString('a'), equals('1'));

      loader.loadBundleFromJson(
        '{"b": "2"}',
        locale: 'fr',
      );

      expect(loader.currentLocale, equals('fr'));
      expect(loader.containsKey('a'), isFalse);
      expect(loader.getString('b'), equals('2'));
    });

    test('loadBundleFromJson throws on invalid JSON', () {
      expect(
        () => loader.loadBundleFromJson('not json', locale: 'en'),
        throwsA(isA<FormatException>()),
      );
    });
  });
}
