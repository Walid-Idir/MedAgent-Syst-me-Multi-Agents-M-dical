import React from 'react';

const STEPS = [
  { label: 'Cas Patient', icon: '📋' },
  { label: 'Diagnostic', icon: '🩺' },
  { label: 'Médecin', icon: '👨‍⚕️' },
  { label: 'Rapport', icon: '📄' },
];

/**
 * Visual progress indicator across the 4 consultation steps.
 * @param {{ currentStep: number }} props — 0-indexed current step
 */
export default function StepIndicator({ currentStep }) {
  return (
    <div className="step-indicator">
      {STEPS.map((step, index) => (
        <React.Fragment key={index}>
          {index > 0 && (
            <div
              className={`step-connector ${index <= currentStep ? 'completed' : ''}`}
            />
          )}
          <div className="step-item" style={{ flexDirection: 'column', alignItems: 'center' }}>
            <div
              className={`step-circle ${
                index === currentStep
                  ? 'active'
                  : index < currentStep
                  ? 'completed'
                  : ''
              }`}
            >
              {index < currentStep ? '✓' : step.icon}
            </div>
            <span
              className={`step-label ${
                index === currentStep
                  ? 'active'
                  : index < currentStep
                  ? 'completed'
                  : ''
              }`}
            >
              {step.label}
            </span>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}
