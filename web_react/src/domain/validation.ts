export interface FieldDescriptor {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  isRequired?: boolean;
  minValue?: number;
  maxValue?: number;
  pattern?: string;
  options?: string[];
  enumOptions?: string[];
}

/**
 * Generic validation function that takes an input map and a list of field descriptors,
 * evaluating constraints (isRequired, minValue/maxValue, pattern regex, options enum).
 */
export function validateFields(input: Record<string, any>, descriptors: FieldDescriptor[]): boolean {
  for (const fd of descriptors) {
    const value = input[fd.key];
    const isRequired = fd.required ?? fd.isRequired ?? false;

    // Check if required. Optional fields that are empty skip constraint validation.
    if (value === undefined || value === null || (typeof value === 'string' && value.trim() === '')) {
      if (isRequired) {
        return false;
      }
      continue;
    }

    const strVal = String(value);
    const type = fd.type;

    if (type === 'int') {
      const parsed = parseInt(strVal, 10);
      if (isNaN(parsed) || parsed.toString() !== strVal) return false;
      if (fd.minValue !== undefined && fd.minValue !== null && parsed < fd.minValue) return false;
      if (fd.maxValue !== undefined && fd.maxValue !== null && parsed > fd.maxValue) return false;
    } else if (type === 'double' || type === 'real') {
      const parsed = parseFloat(strVal);
      if (isNaN(parsed)) return false;
      if (fd.minValue !== undefined && fd.minValue !== null && parsed < fd.minValue) return false;
      if (fd.maxValue !== undefined && fd.maxValue !== null && parsed > fd.maxValue) return false;
    } else if (type === 'string') {
      if (fd.pattern) {
        const regex = new RegExp(fd.pattern);
        if (!regex.test(strVal)) return false;
      }
    } else if (type === 'enum') {
      const options = fd.options ?? fd.enumOptions;
      if (options && !options.includes(strVal)) {
        return false;
      }
    }
  }
  return true;
}
