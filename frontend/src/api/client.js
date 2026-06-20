/**
 * API Client — wraps all FastAPI endpoints for the medical consultation system.
 */

import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000, // 60s — LLM calls can be slow
});

/**
 * Create a new consultation session.
 * @returns {{ thread_id: string, message: string }}
 */
export async function startSession() {
  const { data } = await api.post('/sessions/start');
  return data;
}

/**
 * Start a consultation with a patient case.
 * @param {string} threadId
 * @param {string} patientCase
 * @returns {ConsultationState}
 */
export async function startConsultation(threadId, patientCase) {
  const { data } = await api.post('/consultation/start', {
    thread_id: threadId,
    patient_case: patientCase,
  });
  return data;
}

/**
 * Resume a consultation after an interrupt (patient answer or physician review).
 * @param {string} threadId
 * @param {string} input
 * @param {'patient' | 'physician'} inputType
 * @returns {ConsultationState}
 */
export async function resumeConsultation(threadId, input, inputType = 'patient') {
  const { data } = await api.post('/consultation/resume', {
    thread_id: threadId,
    input,
    input_type: inputType,
  });
  return data;
}

/**
 * Get the current state of a consultation.
 * @param {string} threadId
 * @returns {ConsultationState}
 */
export async function getConsultation(threadId) {
  const { data } = await api.get(`/consultation/${threadId}`);
  return data;
}

/**
 * Get the final report.
 * @param {string} threadId
 * @returns {{ thread_id: string, final_report: string, disclaimer: string }}
 */
export async function getReport(threadId) {
  const { data } = await api.get(`/consultation/${threadId}/report`);
  return data;
}

export default api;
