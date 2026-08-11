import React, { useState, useEffect } from 'react';
import { validateFields } from '../domain/validation';
import logicalLayout from '../../../.pipeline/logical-ui/logical-layout.json';

export interface PropertyGridProps {
  activeView: string;
  onSave?: (data: any) => void;
}

const defaultShowcase: Record<string, any> = {};

const fallbackAttributes: any[] = [];

export const PropertyGrid: React.FC<PropertyGridProps> = ({ activeView, onSave }) => {
  const attributes = (logicalLayout as any).attributes || fallbackAttributes;

  const getInitialData = () => {
    const data: Record<string, any> = {};
    attributes.forEach((attr: any) => {
      if (defaultShowcase[attr.key] !== undefined) {
        data[attr.key] = defaultShowcase[attr.key];
      } else if (attr.defaultValue !== undefined) {
        data[attr.key] = attr.defaultValue;
      } else if (attr.type === 'boolean') {
        data[attr.key] = false;
      } else if (attr.type === 'int' || attr.type === 'double' || attr.type === 'real') {
        data[attr.key] = 0;
      } else if (attr.type === 'enum') {
        const opts = attr.options || attr.enumOptions || [];
        data[attr.key] = opts.length > 0 ? opts[0] : '';
      } else {
        data[attr.key] = '';
      }
    });
    return data;
  };

  // Parent state simulated for showcase
  const [committedData, setCommittedData] = useState<Record<string, any>>(() => getInitialData());

  // Local buffered state to prevent re-renders on keystroke
  const [bufferedData, setBufferedData] = useState<Record<string, any>>(() => ({ ...committedData }));
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Synchronize buffer when activeView changes or parent state is updated
  useEffect(() => {
    setBufferedData({ ...committedData });
    setErrors({});
  }, [activeView, committedData]);

  const handleInputChange = (field: string, value: any) => {
    setBufferedData((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleBlur = (field: string) => {
    const value = bufferedData[field];
    const newErrors = { ...errors };
    let isValid = true;

    // Find the attribute definition to perform validation
    const attr = attributes.find((a: any) => a.key === field);
    if (attr) {
      // Validate using our generic validation function
      const singleInput = { [field]: value };
      const singleDescriptor = [attr];
      const isFieldValid = validateFields(singleInput, singleDescriptor);

      if (!isFieldValid) {
        // Construct detailed error message based on constraints
        if ((attr.required || attr.isRequired) && (value === undefined || value === null || (typeof value === 'string' && value.trim() === ''))) {
          newErrors[field] = `${attr.label} is required`;
        } else if (attr.type === 'int' && (typeof value !== 'number' || isNaN(value))) {
          newErrors[field] = 'Must be a valid integer';
        } else if ((attr.type === 'double' || attr.type === 'real') && (typeof value !== 'number' || isNaN(value))) {
          newErrors[field] = 'Must be a valid number';
        } else if (attr.minValue !== undefined && value < attr.minValue) {
          newErrors[field] = `Value cannot be less than ${attr.minValue}`;
        } else if (attr.maxValue !== undefined && value > attr.maxValue) {
          newErrors[field] = `Value cannot be greater than ${attr.maxValue}`;
        } else if (attr.pattern && typeof value === 'string' && !new RegExp(attr.pattern).test(value)) {
          if (field === 'countryCode') {
            newErrors[field] = 'Must match ISO 2-letter uppercase pattern (e.g. US, FI)';
          } else {
            newErrors[field] = 'Invalid format';
          }
        } else if (attr.type === 'enum') {
          const opts = attr.options || attr.enumOptions || [];
          newErrors[field] = `Must be one of: ${opts.join(', ')}`;
        } else {
          newErrors[field] = 'Invalid value';
        }
        isValid = false;
      } else {
        delete newErrors[field];
      }
    }

    setErrors(newErrors);

    // Commit only if valid
    if (isValid) {
      setCommittedData((prev) => {
        const next = { ...prev, [field]: value };
        if (onSave) {
          onSave(next);
        }
        return next;
      });
    }
  };

  // Group attributes by sectionGroup
  const groups: Record<string, typeof attributes> = {};
  attributes.forEach((attr: any) => {
    const groupName = attr.sectionGroup || 'General';
    if (!groups[groupName]) {
      groups[groupName] = [];
    }
    groups[groupName].push(attr);
  });

  const isGeodeticGroup = (groupName: string) => {
    const nameLower = groupName.toLowerCase();
    return nameLower.includes('geodetic') || nameLower.includes('location') || nameLower.includes('ingestion');
  };

  const isHighlighted = (groupName: string) => {
    const nameLower = groupName.toLowerCase();
    if (activeView === 'Location' || activeView === 'Ingestion') {
      return nameLower.includes('geodetic');
    }
    if (activeView === 'Chassis' || activeView === 'root') {
      return nameLower.includes('structural');
    }
    return false;
  };

  return (
    <div className="property-grid-container">
      <div className="system-sections-wrapper">
        {Object.keys(groups).map((groupName) => {
          const groupAttrs = groups[groupName];
          const highlighted = isHighlighted(groupName);
          return (
            <div key={groupName} className={`system-section ${highlighted ? 'highlighted' : 'dimmed'}`}>
              <div className="section-header-row">
                <h4>{groupName}</h4>
                {highlighted && <span className="highlight-tag">Active Reference</span>}
              </div>
              <div className="form-grid">
                {groupAttrs.map((attr: any) => {
                  const hasError = !!errors[attr.key];
                  return (
                    <div key={attr.key} className="form-group">
                      <label>{attr.label}</label>
                      {attr.type === 'boolean' ? (
                        <input
                          type="checkbox"
                          checked={!!bufferedData[attr.key]}
                          onChange={(e) => handleInputChange(attr.key, e.target.checked)}
                          onBlur={() => handleBlur(attr.key)}
                        />
                      ) : attr.type === 'enum' ? (
                        <select
                          value={bufferedData[attr.key] || ''}
                          className={hasError ? 'input-error' : ''}
                          onChange={(e) => handleInputChange(attr.key, e.target.value)}
                          onBlur={() => handleBlur(attr.key)}
                        >
                          <option value="">-- Select Option --</option>
                          {(attr.options || attr.enumOptions || []).map((opt: string) => (
                            <option key={opt} value={opt}>{opt}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={attr.type === 'int' || attr.type === 'double' || attr.type === 'real' ? 'number' : 'text'}
                          step={attr.type === 'double' || attr.type === 'real' ? 'any' : '1'}
                          className={hasError ? 'input-error' : ''}
                          value={bufferedData[attr.key] ?? ''}
                          onChange={(e) => {
                            const val = attr.type === 'double' || attr.type === 'real'
                              ? parseFloat(e.target.value)
                              : attr.type === 'int'
                              ? parseInt(e.target.value, 10)
                              : e.target.value;
                            handleInputChange(attr.key, typeof val === 'number' && isNaN(val) ? '' : val);
                          }}
                          onBlur={() => handleBlur(attr.key)}
                        />
                      )}
                      {hasError && <span className="error-text">{errors[attr.key]}</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Committed State Display */}
      <div className="committed-state-panel">
        <h5>Committed Pipeline Scope Data (onBlur verified)</h5>
        <pre>{JSON.stringify(committedData, null, 2)}</pre>
      </div>
    </div>
  );
};
