import 'package:app_flutter/domain/type_descriptor.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TypeDescriptor structural equality and copyWith', () {
    test('shouldSupportStructuralEqualityForFieldDescriptor', () {
      const f1 = FieldDescriptor(
        key: 'voltage',
        label: 'Voltage (V)',
        type: 'double',
        required: true,
        minValue: 0.0,
        maxValue: 1000.0,
      );
      const f2 = FieldDescriptor(
        key: 'voltage',
        label: 'Voltage (V)',
        type: 'double',
        required: true,
        minValue: 0.0,
        maxValue: 1000.0,
      );

      expect(f1, equals(f2));
      expect(f1.hashCode, equals(f2.hashCode));

      final f3 = f1.copyWith(label: 'Updated Label');
      expect(f3.label, 'Updated Label');
      expect(f3, isNot(equals(f1)));
    });

    test('shouldSupportStructuralEqualityForTypeRelationDescriptor', () {
      const r1 = TypeRelationDescriptor(
        relationName: 'contains',
        childTypeName: 'ChildUnit',
        childLabel: 'Child Unit',
      );
      const r2 = TypeRelationDescriptor(
        relationName: 'contains',
        childTypeName: 'ChildUnit',
        childLabel: 'Child Unit',
      );

      expect(r1, equals(r2));
      expect(r1.hashCode, equals(r2.hashCode));

      final r3 = r1.copyWith(childLabel: 'New Label');
      expect(r3.childLabel, 'New Label');
      expect(r3, isNot(equals(r1)));
    });

    test('shouldSupportStructuralEqualityForTypeDescriptor', () {
      const t1 = TypeDescriptor(
        typeName: 'Cabinet',
        displayName: 'Equipment Cabinet',
        iconName: 'storage',
        fields: [
          FieldDescriptor(key: 'name', label: 'Name', type: 'string', required: true),
        ],
        childTypes: [
          TypeRelationDescriptor(relationName: 'contains', childTypeName: 'Shelf', childLabel: 'Shelf'),
        ],
        relatedTypes: [],
        parentTypes: [],
      );
      const t2 = TypeDescriptor(
        typeName: 'Cabinet',
        displayName: 'Equipment Cabinet',
        iconName: 'storage',
        fields: [
          FieldDescriptor(key: 'name', label: 'Name', type: 'string', required: true),
        ],
        childTypes: [
          TypeRelationDescriptor(relationName: 'contains', childTypeName: 'Shelf', childLabel: 'Shelf'),
        ],
        relatedTypes: [],
        parentTypes: [],
      );

      expect(t1, equals(t2));
      expect(t1.hashCode, equals(t2.hashCode));

      final t3 = t1.copyWith(displayName: 'Modified Cabinet');
      expect(t3.displayName, 'Modified Cabinet');
      expect(t3, isNot(equals(t1)));
    });
  });
}
