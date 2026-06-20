import { useState, useCallback } from 'react';
import StepIndicator from './components/StepIndicator';
import PatientCaseForm from './components/PatientCaseForm';
import DiagnosticChat from './components/DiagnosticChat';
import PhysicianReview from './components/PhysicianReview';
import FinalReport from './components/FinalReport';
import {
  startSession,
  startConsultation,
  resumeConsultation,
} from './api/client';

/**
 * Main application component.
 * Manages the 4-step consultation flow:
 *   0 → Patient case input
 *   1 → Diagnostic Q&A (5 questions)
 *   2 → Physician review (Human-in-the-Loop)
 *   3 → Final report
 */
export default function App() {
  // --- State ---
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Session
  const [threadId, setThreadId] = useState(null);

  // Diagnostic data
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [questionCount, setQuestionCount] = useState(0);

  // Clinical outputs
  const [diagnosticSummary, setDiagnosticSummary] = useState('');
  const [interimCare, setInterimCare] = useState('');
  const [redFlags, setRedFlags] = useState([]);
  const [finalReport, setFinalReport] = useState('');

  // --- Update state from API response ---
  const updateFromResponse = useCallback((data) => {
    setQuestions(data.questions || []);
    setAnswers(data.answers || []);
    setCurrentQuestion(data.current_question || '');
    setQuestionCount(data.question_count || 0);
    setDiagnosticSummary(data.diagnostic_summary || '');
    setInterimCare(data.interim_care || '');
    setRedFlags(data.red_flags || []);
    setFinalReport(data.final_report || '');

    // Determine which screen to show
    if (data.final_report) {
      setCurrentStep(3);
    } else if (data.waiting_for === 'physician' || data.diagnostic_summary) {
      setCurrentStep(2);
    } else if (data.waiting_for === 'patient' || (data.questions && data.questions.length > 0)) {
      setCurrentStep(1);
    }
  }, []);

  // --- Handlers ---

  /**
   * Step 0 → Start consultation with patient case.
   */
  const handleStartConsultation = useCallback(async (patientCase) => {
    setLoading(true);
    setError(null);

    try {
      // Create session
      const session = await startSession();
      const tid = session.thread_id;
      setThreadId(tid);

      // Start consultation
      const result = await startConsultation(tid, patientCase);
      updateFromResponse(result);
    } catch (err) {
      console.error('Error starting consultation:', err);
      setError(
        err.response?.data?.detail ||
        'Erreur lors du démarrage de la consultation. Vérifiez que le backend est en cours d\'exécution.'
      );
    } finally {
      setLoading(false);
    }
  }, [updateFromResponse]);

  /**
   * Step 1 → Submit patient answer to a diagnostic question.
   */
  const handlePatientAnswer = useCallback(async (answer) => {
    if (!threadId) return;

    setLoading(true);
    setError(null);

    try {
      const result = await resumeConsultation(threadId, answer, 'patient');
      updateFromResponse(result);
    } catch (err) {
      console.error('Error submitting answer:', err);
      setError(
        err.response?.data?.detail ||
        'Erreur lors de l\'envoi de la réponse.'
      );
    } finally {
      setLoading(false);
    }
  }, [threadId, updateFromResponse]);

  /**
   * Step 2 → Submit physician treatment plan.
   */
  const handlePhysicianSubmit = useCallback(async (treatment) => {
    if (!threadId) return;

    setLoading(true);
    setError(null);

    try {
      const result = await resumeConsultation(threadId, treatment, 'physician');
      updateFromResponse(result);
    } catch (err) {
      console.error('Error submitting physician review:', err);
      setError(
        err.response?.data?.detail ||
        'Erreur lors de la validation de l\'avis médical.'
      );
    } finally {
      setLoading(false);
    }
  }, [threadId, updateFromResponse]);

  /**
   * Reset for a new consultation.
   */
  const handleNewConsultation = useCallback(() => {
    setCurrentStep(0);
    setThreadId(null);
    setQuestions([]);
    setAnswers([]);
    setCurrentQuestion('');
    setQuestionCount(0);
    setDiagnosticSummary('');
    setInterimCare('');
    setRedFlags([]);
    setFinalReport('');
    setError(null);
  }, []);

  // --- Render ---
  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="app-logo">
          <div className="app-logo-icon">⚕️</div>
          <h1 className="app-title">MedAgent</h1>
        </div>
        <p className="app-subtitle">
          Système multi-agents d'orientation clinique préliminaire
        </p>
      </header>

      {/* Step Indicator */}
      <StepIndicator currentStep={currentStep} />

      {/* Error Display */}
      {error && (
        <div className="red-flag-alert" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="red-flag-alert-title">❌ Erreur</div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            {error}
          </p>
          <button
            className="btn btn-secondary"
            onClick={() => setError(null)}
            style={{ marginTop: 'var(--space-3)' }}
          >
            Fermer
          </button>
        </div>
      )}

      {/* Screens */}
      {currentStep === 0 && (
        <PatientCaseForm
          onSubmit={handleStartConsultation}
          loading={loading}
        />
      )}

      {currentStep === 1 && (
        <DiagnosticChat
          questions={questions}
          answers={answers}
          currentQuestion={currentQuestion}
          questionCount={questionCount}
          onAnswer={handlePatientAnswer}
          loading={loading}
        />
      )}

      {currentStep === 2 && (
        <PhysicianReview
          diagnosticSummary={diagnosticSummary}
          interimCare={interimCare}
          redFlags={redFlags}
          onSubmit={handlePhysicianSubmit}
          loading={loading}
        />
      )}

      {currentStep === 3 && (
        <FinalReport
          report={finalReport}
          onNewConsultation={handleNewConsultation}
        />
      )}

      {/* Footer */}
      <footer className="app-footer">
        <p>
          ⚕️ Ce système ne remplace pas une consultation médicale.
          Projet académique — Walid Idir
        </p>
      </footer>
    </div>
  );
}
