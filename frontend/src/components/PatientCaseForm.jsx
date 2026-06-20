import { useState } from 'react';

/**
 * Screen 1: Patient case input form.
 * Collects the initial patient case description and starts the consultation.
 *
 * @param {{ onSubmit: (patientCase: string) => void, loading: boolean }} props
 */
export default function PatientCaseForm({ onSubmit, loading }) {
  const [patientCase, setPatientCase] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (patientCase.trim() && !loading) {
      onSubmit(patientCase.trim());
    }
  };

  return (
    <div className="screen-enter">
      <div className="glass-card">
        <h2 className="section-title">📋 Nouveau Cas Patient</h2>
        <p className="section-subtitle">
          Décrivez les symptômes et le contexte clinique du patient pour démarrer l'orientation.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="patient-case">
              Description du cas
            </label>
            <textarea
              id="patient-case"
              className="form-textarea"
              value={patientCase}
              onChange={(e) => setPatientCase(e.target.value)}
              placeholder="Ex: Patient de 35 ans présentant une toux sèche persistante depuis 5 jours, accompagnée de fièvre modérée (38.2°C) et de fatigue générale..."
              rows={5}
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg btn-block"
            disabled={!patientCase.trim() || loading}
            id="start-consultation-btn"
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                Démarrage en cours...
              </>
            ) : (
              <>🩺 Démarrer la Consultation</>
            )}
          </button>
        </form>

        <div style={{ marginTop: 'var(--space-6)' }}>
          <p className="section-subtitle" style={{ fontSize: '0.75rem', textAlign: 'center' }}>
            💡 Exemples de cas : syndrome respiratoire, douleurs thoraciques, fatigue chronique
          </p>
        </div>
      </div>
    </div>
  );
}
