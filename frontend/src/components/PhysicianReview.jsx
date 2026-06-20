import { useState } from 'react';

/**
 * Screen 3: Physician review (Human-in-the-Loop).
 * Displays the diagnostic summary and interim care recommendation,
 * then collects the physician's treatment/conduct plan.
 *
 * @param {{
 *   diagnosticSummary: string,
 *   interimCare: string,
 *   redFlags: string[],
 *   onSubmit: (treatment: string) => void,
 *   loading: boolean,
 * }} props
 */
export default function PhysicianReview({
  diagnosticSummary,
  interimCare,
  redFlags,
  onSubmit,
  loading,
}) {
  const [treatment, setTreatment] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (treatment.trim() && !loading) {
      onSubmit(treatment.trim());
    }
  };

  return (
    <div className="screen-enter">
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-6)' }}>
          <h2 className="section-title" style={{ marginBottom: 0 }}>
            👨‍⚕️ Revue du Médecin Traitant
          </h2>
          <span className="status-badge status-badge-waiting">
            ⏸ En attente
          </span>
        </div>
        <p className="section-subtitle">
          Veuillez examiner la synthèse clinique et proposer un traitement ou une conduite à tenir.
        </p>

        {/* Red Flags Alert */}
        {redFlags && redFlags.length > 0 && (
          <div className="red-flag-alert">
            <div className="red-flag-alert-title">
              ⚠️ Drapeaux Rouges Détectés
            </div>
            <ul className="red-flag-alert-list">
              {redFlags.map((flag, index) => (
                <li key={index}>{flag}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Diagnostic Summary */}
        <div className="review-section">
          <div className="review-section-title">
            📋 Synthèse Clinique Préliminaire
          </div>
          <div className="review-content">
            {diagnosticSummary || 'Synthèse non disponible.'}
          </div>
        </div>

        {/* Interim Care */}
        <div className="review-section" style={{ borderColor: 'rgba(16, 185, 129, 0.15)', background: 'rgba(16, 185, 129, 0.04)' }}>
          <div className="review-section-title" style={{ color: 'var(--accent-success)' }}>
            💊 Recommandation Intermédiaire
          </div>
          <div className="review-content">
            {interimCare || 'Recommandation non disponible.'}
          </div>
        </div>

        {/* Physician Input */}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="physician-treatment">
              Traitement / Conduite à Tenir
            </label>
            <textarea
              id="physician-treatment"
              className="form-textarea"
              value={treatment}
              onChange={(e) => setTreatment(e.target.value)}
              placeholder="Ex: Prescrire paracétamol 1g toutes les 6h, repos au lit, contrôle à J+3 si persistance des symptômes. Radiographie thoracique si aggravation..."
              rows={5}
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="btn btn-success btn-lg btn-block"
            disabled={!treatment.trim() || loading}
            id="submit-physician-review-btn"
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
                Validation en cours...
              </>
            ) : (
              <>✅ Valider l'Avis Médical</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
