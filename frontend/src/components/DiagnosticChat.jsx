import { useState, useRef, useEffect } from 'react';

/**
 * Screen 2: Diagnostic Q&A chat interface.
 * Displays questions from the diagnostic agent and collects patient answers.
 *
 * @param {{
 *   questions: string[],
 *   answers: string[],
 *   currentQuestion: string,
 *   questionCount: number,
 *   onAnswer: (answer: string) => void,
 *   loading: boolean,
 * }} props
 */
export default function DiagnosticChat({
  questions,
  answers,
  currentQuestion,
  questionCount,
  onAnswer,
  loading,
}) {
  const [inputValue, setInputValue] = useState('');
  const chatEndRef = useRef(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [questions, answers, currentQuestion]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !loading) {
      onAnswer(inputValue.trim());
      setInputValue('');
    }
  };

  const answeredCount = answers.length;
  const totalQuestions = 5;
  const progress = (answeredCount / totalQuestions) * 100;

  return (
    <div className="screen-enter">
      <div className="glass-card">
        <h2 className="section-title">🩺 Diagnostic en cours</h2>
        <p className="section-subtitle">
          L'agent de diagnostic pose des questions pour évaluer votre situation clinique.
        </p>

        {/* Progress Bar */}
        <div className="question-counter">
          <span className="question-counter-text">
            {answeredCount}/{totalQuestions}
          </span>
          <div className="question-counter-bar">
            <div
              className="question-counter-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="question-counter-text">
            {answeredCount < totalQuestions ? 'En cours' : '✓ Terminé'}
          </span>
        </div>

        {/* Chat Messages */}
        <div className="chat-container">
          {questions.map((question, index) => (
            <div key={`qa-${index}`}>
              {/* Agent question */}
              <div className="chat-bubble chat-bubble-agent">
                <div className="chat-bubble-label">🩺 Agent Diagnostic</div>
                <div>Question {index + 1}/5 : {question}</div>
              </div>

              {/* Patient answer (if exists) */}
              {answers[index] && (
                <div className="chat-bubble chat-bubble-patient">
                  <div className="chat-bubble-label">🧑 Patient</div>
                  <div>{answers[index]}</div>
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="loading-container" style={{ padding: 'var(--space-4)' }}>
              <div className="spinner" />
              <span className="loading-text">Analyse en cours...</span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input area — only show if we have an unanswered question */}
        {currentQuestion && answeredCount < totalQuestions && !loading && (
          <form onSubmit={handleSubmit} className="chat-input-area">
            <input
              type="text"
              className="form-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Tapez votre réponse..."
              disabled={loading}
              autoFocus
              id="patient-answer-input"
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!inputValue.trim() || loading}
              id="send-answer-btn"
            >
              Envoyer ➤
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
