import 'package:app_flutter/features/tables/models/column_model.dart';
import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ColumnModel', () {
    group('constructor', () {
      test('sets all required fields', () {
        const column = ColumnModel(
          key: 'testKey',
          label: 'Test Label',
          type: 'string',
        );
        expect(column.key, 'testKey');
        expect(column.label, 'Test Label');
        expect(column.type, 'string');
      });

      test('sets width when provided', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
          width: 120.0,
        );
        expect(column.width, 120.0);
      });

      test('sets sortable', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
          sortable: false,
        );
        expect(column.sortable, isFalse);
      });

      test('sets frozen', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
          frozen: true,
        );
        expect(column.frozen, isTrue);
      });

      test('sets visible', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
          visible: false,
        );
        expect(column.visible, isFalse);
      });
    });

    group('defaults', () {
      test('width defaults to null', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
        );
        expect(column.width, isNull);
      });

      test('sortable defaults to true', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
        );
        expect(column.sortable, isTrue);
      });

      test('frozen defaults to false', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
        );
        expect(column.frozen, isFalse);
      });

      test('visible defaults to true', () {
        const column = ColumnModel(
          key: 'k',
          label: 'l',
          type: 't',
        );
        expect(column.visible, isTrue);
      });
    });

    group('fromFieldDescriptor', () {
      test('maps key, label, type from FieldDescriptor', () {
        final fd = FieldDescriptor(
          key: 'voltage',
          label: 'Voltage (V)',
          type: 'double',
        );
        final column = ColumnModel.fromFieldDescriptor(fd);
        expect(column.key, 'voltage');
        expect(column.label, 'Voltage (V)');
        expect(column.type, 'double');
      });

      test('uses defaults for fields not in FieldDescriptor', () {
        final fd = FieldDescriptor(
          key: 'current',
          label: 'Current (A)',
          type: 'double',
        );
        final column = ColumnModel.fromFieldDescriptor(fd);
        expect(column.width, isNull);
        expect(column.sortable, isTrue);
        expect(column.frozen, isFalse);
        expect(column.visible, isTrue);
      });

      test('dynamically derives label from key when label starts with Field fallback pattern', () {
        final fd = FieldDescriptor(
          key: 'max_voltage',
          label: 'Field 1',
          type: 'double',
        );
        final column = ColumnModel.fromFieldDescriptor(fd);
        expect(column.label, 'Max Voltage');
      });

      test('dynamically derives label from key when label is empty', () {
        final fd = FieldDescriptor(
          key: 'device_id',
          label: '',
          type: 'string',
        );
        final column = ColumnModel.fromFieldDescriptor(fd);
        expect(column.label, 'Device Id');
      });

      test('preserves explicit custom label when label does not match fallback pattern', () {
        final fd = FieldDescriptor(
          key: 'max_voltage',
          label: 'Maximum System Voltage',
          type: 'double',
        );
        final column = ColumnModel.fromFieldDescriptor(fd);
        expect(column.label, 'Maximum System Voltage');
      });
    });

    group('edge cases', () {
      test('empty key', () {
        const column = ColumnModel(
          key: '',
          label: 'label',
          type: 'string',
        );
        expect(column.key, '');
      });

      test('empty label', () {
        const column = ColumnModel(
          key: 'k',
          label: '',
          type: 'string',
        );
        expect(column.label, '');
      });
    });
  });
}
