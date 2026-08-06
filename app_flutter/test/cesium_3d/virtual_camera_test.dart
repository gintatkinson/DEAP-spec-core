import 'package:flutter_test/flutter_test.dart';
import 'package:app_flutter/features/map_viewport/cesium_3d/virtual_camera.dart';

void main() {
  group('VirtualCamera', () {
    test('isSpatiallyEquivalentTo handles exact matches', () {
      const camera = VirtualCamera.raw(dim_0: 10, dim_1: 20, dim_2: 30, heading: 40, pitch: 50, roll: 60);
      expect(camera.isSpatiallyEquivalentTo(camera), isTrue);
    });

    test('isSpatiallyEquivalentTo handles drift within epsilon', () {
      const camera1 = VirtualCamera.raw(dim_0: 10, dim_1: 20, dim_2: 30, heading: 40, pitch: 50, roll: 60);
      const camera2 = VirtualCamera.raw(dim_0: 10.00000001, dim_1: 20.00000001, dim_2: 30.0001, heading: 40.0001, pitch: 50.0001, roll: 60.0001);
      expect(camera1.isSpatiallyEquivalentTo(camera2), isTrue);
    });

    test('isSpatiallyEquivalentTo fails on drift beyond epsilon', () {
      const camera1 = VirtualCamera.raw(dim_0: 10, dim_1: 20, dim_2: 30, heading: 40, pitch: 50, roll: 60);
      const camera2 = VirtualCamera.raw(dim_0: 10.1, dim_1: 20.0, dim_2: 30.0, heading: 40.0, pitch: 50.0, roll: 60.0);
      expect(camera1.isSpatiallyEquivalentTo(camera2), isFalse);
    });
  });
}
