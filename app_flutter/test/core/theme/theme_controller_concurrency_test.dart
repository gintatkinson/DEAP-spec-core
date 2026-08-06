import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/core/theme/theme_controller.dart';
import 'package:app_flutter/core/theme/theme_service.dart';

/// Ephemeral implementation of [ThemeService] for testing.
class EphemeralThemeService implements ThemeService {
  @override
  Future<ThemeMode> loadThemeMode() async => ThemeMode.system;
  @override
  Future<void> saveThemeMode(ThemeMode mode) async {}
  @override
  Future<int> loadThemeScheme() async => 0;
  @override
  Future<void> saveThemeScheme(int scheme) async {}
  @override
  Future<Axis> loadLayoutSplitAxis() async => Axis.vertical;
  @override
  Future<void> saveLayoutSplitAxis(Axis axis) async {}
  @override
  Future<double> loadPanelOpacity() async => 0.85;
  @override
  Future<void> savePanelOpacity(double opacity) async {}
  @override
  Future<double> loadTextScale() async => 1.0;
  @override
  Future<void> saveTextScale(double scale) async {}
}

void main() {
  group('ThemeController Concurrency', () {
    test('concurrent asynchronous changes short-circuit gracefully after dispose', () async {
      final themeService = EphemeralThemeService();
      final controller = ThemeController(themeService);

      // Concurrently trigger multiple asynchronous updates
      controller.updateThemeMode(ThemeMode.dark);
      controller.updateThemeMode(ThemeMode.light);
      controller.updatePanelOpacity(0.5);
      controller.updateThemeMode(ThemeMode.system);

      // Call dispose immediately before they resolve
      controller.dispose();

      // We just want to assert that no exceptions are thrown by the background tasks
      // and that the state resolves cleanly. 
      await Future.delayed(const Duration(milliseconds: 50));
      expect(true, isTrue); // If we reach here without unhandled exceptions, we're good
    });
  });
}
