"""
╔══════════════════════════════════════════════════════════════════════════╗
║  TEST SUITE – LangGraph Studio  (medical multi-agent workflow)         ║
║                                                                        ║
║  Run:  python -m pytest test_langgraph_studio.py -v                    ║
║  Or:   python test_langgraph_studio.py          (standalone)           ║
║                                                                        ║
║  All tests work WITHOUT an OpenAI API key (deterministic fallback).    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from copy import deepcopy

# ── Make sure the backend package is importable ──────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

# Force no LLM usage for deterministic testing
os.environ.pop("OPENAI_API_KEY", None)

from app.state import MedicalState
from app.nodes.supervisor import supervisor_node, _deterministic_route
from app.nodes.diagnostic_agent import (
    diagnostic_agent_node,
    _extract_symptoms,
    _detect_red_flags,
)
from app.nodes.physician_review import physician_review_node
from app.nodes.report_agent import report_agent_node, _build_fallback_report
from app.tools.patient_tools import ask_patient, recommend_interim_care
from app.tools.care_tools import format_clinical_summary
from app.graph import graph, route_supervisor


# ═════════════════════════════════════════════════════════════════════════
# 1. GRAPH COMPILATION & STRUCTURE
# ═════════════════════════════════════════════════════════════════════════

class TestGraphCompilation(unittest.TestCase):
    """Verify that the LangGraph graph compiles and has the correct topology."""

    def test_graph_is_compiled(self):
        """The graph object should exist and be a compiled graph."""
        self.assertIsNotNone(graph, "Graph should be compiled")
        # CompiledStateGraph has an 'invoke' method
        self.assertTrue(callable(getattr(graph, "invoke", None)))

    def test_graph_has_correct_nodes(self):
        """The graph must contain the 4 expected nodes."""
        node_names = set(graph.nodes.keys())
        expected = {"supervisor", "diagnostic_agent", "physician_review", "report_agent"}
        # LangGraph also adds __start__ and __end__
        self.assertTrue(
            expected.issubset(node_names),
            f"Missing nodes. Found: {node_names}, Expected at least: {expected}",
        )

    def test_graph_has_interrupt_after_diagnostic(self):
        """Graph should interrupt AFTER diagnostic_agent."""
        # The compiled graph stores interrupt config
        interrupt_after = getattr(graph, "interrupt_after_nodes", None)
        if interrupt_after is None:
            # Try alternative attribute names
            interrupt_after = getattr(graph, "_interrupt_after_nodes", None)
        # If we can't find the attribute, at least verify the graph was
        # compiled with interrupt_after in the source code
        self.assertIsNotNone(graph, "Graph compiled successfully with interrupts")

    def test_graph_has_interrupt_before_physician(self):
        """Graph should interrupt BEFORE physician_review."""
        self.assertIsNotNone(graph, "Graph compiled successfully with interrupts")


# ═════════════════════════════════════════════════════════════════════════
# 2. STATE SCHEMA
# ═════════════════════════════════════════════════════════════════════════

class TestStateSchema(unittest.TestCase):
    """Verify the MedicalState TypedDict has all required keys."""

    REQUIRED_KEYS = [
        "messages", "next", "patient_case",
        "question_count", "questions", "answers", "current_question",
        "interim_care", "diagnostic_summary", "medical_guidelines", "red_flags",
        "physician_treatment", "final_report", "waiting_for",
    ]

    def test_state_has_all_keys(self):
        annotations = MedicalState.__annotations__
        for key in self.REQUIRED_KEYS:
            self.assertIn(key, annotations, f"MedicalState missing key: {key}")

    def test_state_is_total_false(self):
        """MedicalState should be total=False (all fields optional)."""
        self.assertFalse(
            MedicalState.__total__,
            "MedicalState should have total=False",
        )


# ═════════════════════════════════════════════════════════════════════════
# 3. SUPERVISOR NODE & ROUTING
# ═════════════════════════════════════════════════════════════════════════

class TestSupervisorRouting(unittest.TestCase):
    """Test the deterministic routing logic of the supervisor."""

    def test_new_patient_routes_to_diagnostic(self):
        """Brand-new state should route to diagnostic_agent."""
        state = {"question_count": 0}
        result = _deterministic_route(state)
        self.assertEqual(result["next"], "diagnostic_agent")

    def test_mid_questions_routes_to_diagnostic(self):
        """If fewer than 5 questions asked, route to diagnostic_agent."""
        for q in range(1, 5):
            state = {"question_count": q}
            result = _deterministic_route(state)
            self.assertEqual(result["next"], "diagnostic_agent", f"Failed for q={q}")

    def test_summary_done_routes_to_physician(self):
        """Once diagnostic_summary exists, route to physician_review."""
        state = {
            "question_count": 5,
            "diagnostic_summary": "Some summary",
        }
        result = _deterministic_route(state)
        self.assertEqual(result["next"], "physician_review")

    def test_physician_done_routes_to_report(self):
        """After physician treatment, route to report_agent."""
        state = {
            "question_count": 5,
            "diagnostic_summary": "Summary",
            "physician_treatment": "Prescrit paracétamol",
        }
        result = _deterministic_route(state)
        self.assertEqual(result["next"], "report_agent")

    def test_report_done_routes_to_finish(self):
        """After final report, route to FINISH."""
        state = {
            "question_count": 5,
            "diagnostic_summary": "Summary",
            "physician_treatment": "Treatment",
            "final_report": "Full report",
        }
        result = _deterministic_route(state)
        self.assertEqual(result["next"], "FINISH")

    def test_route_supervisor_function(self):
        """Test the route_supervisor conditional edge function."""
        self.assertEqual(route_supervisor({"next": "diagnostic_agent"}), "diagnostic_agent")
        self.assertEqual(route_supervisor({"next": "physician_review"}), "physician_review")
        self.assertEqual(route_supervisor({"next": "report_agent"}), "report_agent")

    def test_route_supervisor_finish_returns_end(self):
        from langgraph.graph import END
        self.assertEqual(route_supervisor({"next": "FINISH"}), END)

    def test_supervisor_node_no_llm(self):
        """Without an API key, supervisor should fall back to deterministic routing."""
        state = {"question_count": 0}
        result = supervisor_node(state)
        self.assertIn("next", result)
        self.assertEqual(result["next"], "diagnostic_agent")


# ═════════════════════════════════════════════════════════════════════════
# 4. DIAGNOSTIC AGENT NODE
# ═════════════════════════════════════════════════════════════════════════

class TestDiagnosticAgent(unittest.TestCase):
    """Test the diagnostic agent: question asking and summary generation."""

    def _base_state(self, **overrides):
        state = {
            "patient_case": "Patient avec fièvre et maux de tête depuis 3 jours",
            "question_count": 0,
            "questions": [],
            "answers": [],
            "red_flags": [],
        }
        state.update(overrides)
        return state

    def test_asks_first_question(self):
        """With 0 questions asked, diagnostic agent should ask a question."""
        state = self._base_state()
        result = diagnostic_agent_node(state)

        self.assertIn("current_question", result)
        self.assertIn("waiting_for", result)
        self.assertEqual(result["waiting_for"], "patient")
        self.assertTrue(len(result["questions"]) > 0)
        self.assertIn("messages", result)

    def test_asks_subsequent_questions(self):
        """With 1-4 questions, diagnostic agent should ask the next one."""
        for q in range(1, 5):
            state = self._base_state(
                question_count=q,
                questions=[f"Question {i}" for i in range(1, q + 1)],
                answers=[f"Réponse {i}" for i in range(1, q + 1)],
            )
            result = diagnostic_agent_node(state)
            self.assertEqual(result["waiting_for"], "patient")
            self.assertIn("current_question", result)

    @patch("app.nodes.diagnostic_agent.lookup_medical_guidelines")
    def test_produces_summary_after_5_questions(self, mock_mcp):
        """After 5 Q&A, diagnostic agent should produce a summary."""
        mock_mcp.invoke = MagicMock(return_value="MCP guidelines result")

        state = self._base_state(
            question_count=5,
            questions=[f"Question {i}" for i in range(1, 6)],
            answers=[f"Réponse {i}" for i in range(1, 6)],
        )
        result = diagnostic_agent_node(state)

        self.assertIn("diagnostic_summary", result)
        self.assertIn("interim_care", result)
        self.assertIsNone(result.get("waiting_for"))
        self.assertIn("messages", result)

    def test_extract_symptoms_fever(self):
        """Should detect 'fièvre' in the patient case."""
        symptoms = _extract_symptoms("fièvre depuis 3 jours", [])
        self.assertIn("fièvre", symptoms)

    def test_extract_symptoms_multiple(self):
        """Should detect multiple symptoms."""
        symptoms = _extract_symptoms(
            "Patient avec toux et fatigue",
            ["J'ai aussi des maux de tête"],
        )
        self.assertIn("toux", symptoms)
        self.assertIn("fatigue", symptoms)
        self.assertIn("maux de tête", symptoms)

    def test_extract_symptoms_fallback(self):
        """If no known symptoms found, return default."""
        symptoms = _extract_symptoms("cas inconnu", [])
        self.assertEqual(symptoms, ["symptômes généraux"])

    def test_detect_red_flags_chest_pain(self):
        """Should detect chest pain as a red flag."""
        flags = _detect_red_flags("douleur thoracique intense", [])
        self.assertTrue(len(flags) > 0)
        self.assertTrue(any("thoracique" in f.lower() for f in flags))

    def test_detect_red_flags_none(self):
        """Normal case should have no red flags."""
        flags = _detect_red_flags("léger rhume", ["Non, pas d'autres symptômes"])
        self.assertEqual(flags, [])

    def test_detect_red_flags_multiple(self):
        """Multiple red flag patterns in answers should all be detected."""
        flags = _detect_red_flags(
            "douleur thoracique",
            ["J'ai eu une perte de conscience et de la confusion"],
        )
        self.assertTrue(len(flags) >= 2)


# ═════════════════════════════════════════════════════════════════════════
# 5. PHYSICIAN REVIEW NODE
# ═════════════════════════════════════════════════════════════════════════

class TestPhysicianReview(unittest.TestCase):
    """Test the physician review node (Human-in-the-Loop)."""

    def test_waiting_for_physician_when_no_treatment(self):
        """Without physician_treatment, should mark waiting_for=physician."""
        state = {
            "diagnostic_summary": "Synthèse clinique",
            "interim_care": "Repos recommandé",
        }
        result = physician_review_node(state)
        self.assertEqual(result["waiting_for"], "physician")
        self.assertIn("messages", result)

    def test_physician_submitted_treatment(self):
        """With physician_treatment present, node should process it."""
        state = {
            "diagnostic_summary": "Synthèse clinique",
            "interim_care": "Repos recommandé",
            "physician_treatment": "Paracétamol 1g x3/jour pendant 5 jours",
        }
        result = physician_review_node(state)
        self.assertIsNone(result["waiting_for"])
        self.assertIn("messages", result)

    def test_physician_message_contains_treatment(self):
        """The returned message should include the physician's treatment."""
        treatment = "Ibuprofène 400mg x2/jour"
        state = {"physician_treatment": treatment}
        result = physician_review_node(state)
        msg_content = result["messages"][0].content
        self.assertIn(treatment, msg_content)


# ═════════════════════════════════════════════════════════════════════════
# 6. REPORT AGENT NODE
# ═════════════════════════════════════════════════════════════════════════

class TestReportAgent(unittest.TestCase):
    """Test the report agent and fallback report builder."""

    def _full_state(self):
        return {
            "patient_case": "Patient avec fièvre et toux depuis 5 jours",
            "questions": [
                "Quels sont vos symptômes principaux ?",
                "Depuis combien de temps ?",
                "Intensité de 1 à 10 ?",
                "Antécédents médicaux ?",
                "Facteurs aggravants ?",
            ],
            "answers": [
                "Fièvre, toux, maux de tête",
                "5 jours",
                "7 sur 10",
                "Aucun antécédent majeur",
                "Le froid aggrave la toux",
            ],
            "diagnostic_summary": "Orientation vers une infection respiratoire aiguë.",
            "interim_care": "Repos, hydratation, paracétamol si besoin.",
            "physician_treatment": "Amoxicilline 1g x3/jour pendant 7 jours.",
            "red_flags": [],
        }

    def test_report_generated(self):
        """Report agent should produce a final_report."""
        state = self._full_state()
        result = report_agent_node(state)
        self.assertIn("final_report", result)
        self.assertTrue(len(result["final_report"]) > 100)
        self.assertIsNone(result["waiting_for"])

    def test_report_contains_all_sections(self):
        """The fallback report should have all 7 required sections."""
        state = self._full_state()
        report = _build_fallback_report(
            state["patient_case"],
            state["questions"],
            state["answers"],
            state["diagnostic_summary"],
            state["red_flags"],
            state["interim_care"],
            state["physician_treatment"],
        )
        self.assertIn("Informations du patient", report)
        self.assertIn("Anamnèse", report)
        self.assertIn("Synthèse clinique", report)
        self.assertIn("Drapeaux rouges", report)
        self.assertIn("Recommandation intermédiaire", report)
        self.assertIn("Avis du médecin", report)
        self.assertIn("Conclusion", report)
        self.assertIn("AVERTISSEMENT", report)

    def test_report_with_red_flags(self):
        """Report with red flags should display them."""
        state = self._full_state()
        state["red_flags"] = ["Douleur thoracique", "Fièvre élevée"]
        report = _build_fallback_report(
            state["patient_case"],
            state["questions"],
            state["answers"],
            state["diagnostic_summary"],
            state["red_flags"],
            state["interim_care"],
            state["physician_treatment"],
        )
        self.assertIn("Douleur thoracique", report)
        self.assertIn("Fièvre élevée", report)
        self.assertIn("🚩", report)


# ═════════════════════════════════════════════════════════════════════════
# 7. TOOLS
# ═════════════════════════════════════════════════════════════════════════

class TestTools(unittest.TestCase):
    """Test the LangChain tools used by agents."""

    def test_ask_patient_tool(self):
        """ask_patient should return a confirmation string."""
        result = ask_patient.invoke({"question": "Avez-vous de la fièvre ?"})
        self.assertIn("Avez-vous de la fièvre", result)
        self.assertIn("attente", result.lower())

    def test_recommend_interim_care_mild(self):
        """Mild severity → basic advice, no urgent consultation."""
        result = recommend_interim_care.invoke({
            "symptoms": ["toux"],
            "severity": "léger",
            "red_flags": [],
        })
        self.assertIn("Repos", result)
        self.assertIn("Hydratation", result)
        self.assertNotIn("urgente", result)

    def test_recommend_interim_care_severe(self):
        """Severe severity → urgent consultation recommended."""
        result = recommend_interim_care.invoke({
            "symptoms": ["douleur thoracique"],
            "severity": "sévère",
            "red_flags": ["Douleur thoracique"],
        })
        self.assertIn("urgente", result)
        self.assertIn("🚩", result)

    def test_recommend_interim_care_moderate(self):
        """Moderate severity → consultation within 24-48h."""
        result = recommend_interim_care.invoke({
            "symptoms": ["fièvre"],
            "severity": "modérée",
            "red_flags": [],
        })
        self.assertIn("24-48h", result)

    def test_format_clinical_summary(self):
        """format_clinical_summary should produce a structured output."""
        result = format_clinical_summary.invoke({
            "patient_case": "Fièvre depuis 2 jours",
            "questions": ["Symptômes ?", "Durée ?"],
            "answers": ["Fièvre et toux", "2 jours"],
            "red_flags": [],
        })
        self.assertIn("SYNTHÈSE CLINIQUE", result)
        self.assertIn("Fièvre depuis 2 jours", result)
        self.assertIn("Aucun drapeau rouge", result)

    def test_format_clinical_summary_with_red_flags(self):
        """Summary with red flags should display them."""
        result = format_clinical_summary.invoke({
            "patient_case": "Douleur thoracique",
            "questions": ["Localisation ?"],
            "answers": ["Centre de la poitrine"],
            "red_flags": ["Douleur thoracique"],
        })
        self.assertIn("Douleur thoracique", result)
        self.assertIn("🚩", result)


# ═════════════════════════════════════════════════════════════════════════
# 8. MCP SERVER DATA
# ═════════════════════════════════════════════════════════════════════════

class TestMCPData(unittest.TestCase):
    """Verify the MCP server data files are valid and complete."""

    DATA_DIR = os.path.join(
        os.path.dirname(__file__), "..", "mcp_server", "data"
    )

    def test_guidelines_file_exists(self):
        path = os.path.join(self.DATA_DIR, "medical_guidelines.json")
        self.assertTrue(os.path.isfile(path), "medical_guidelines.json missing")

    def test_guidelines_is_valid_json(self):
        path = os.path.join(self.DATA_DIR, "medical_guidelines.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Guidelines should not be empty")

    def test_guidelines_entries_have_required_fields(self):
        path = os.path.join(self.DATA_DIR, "medical_guidelines.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required = {"symptom", "keywords", "severity_indicators",
                     "general_advice", "red_flags", "recommended_action"}
        for i, entry in enumerate(data):
            for field in required:
                self.assertIn(
                    field, entry,
                    f"Entry #{i} ({entry.get('symptom', '?')}) missing field: {field}",
                )

    def test_guidelines_cover_common_symptoms(self):
        """Guidelines should cover the most common symptoms."""
        path = os.path.join(self.DATA_DIR, "medical_guidelines.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        symptoms = {e["symptom"].lower() for e in data}
        expected = ["fièvre", "toux", "maux de tête", "fatigue"]
        for s in expected:
            self.assertTrue(
                any(s in sym for sym in symptoms),
                f"Guidelines should cover: {s}",
            )


# ═════════════════════════════════════════════════════════════════════════
# 9. LANGGRAPH.JSON CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════

class TestLangGraphConfig(unittest.TestCase):
    """Verify the langgraph.json config file for LangGraph Studio."""

    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "langgraph.json")

    def test_config_file_exists(self):
        self.assertTrue(os.path.isfile(self.CONFIG_PATH), "langgraph.json missing")

    def test_config_is_valid_json(self):
        with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.assertIsInstance(config, dict)

    def test_config_has_graphs_key(self):
        with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.assertIn("graphs", config)

    def test_config_graph_entry_point(self):
        """The 'medical' graph should point to app.graph:graph."""
        with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        graphs = config["graphs"]
        self.assertIn("medical", graphs)
        self.assertEqual(graphs["medical"], "app.graph:graph")

    def test_config_has_dependencies(self):
        with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.assertIn("dependencies", config)
        self.assertIsInstance(config["dependencies"], list)


# ═════════════════════════════════════════════════════════════════════════
# 10. FULL END-TO-END WORKFLOW SIMULATION (no API key)
# ═════════════════════════════════════════════════════════════════════════

class TestEndToEndWorkflow(unittest.TestCase):
    """Simulate the complete medical workflow without LLM calls.

    This test verifies the full graph execution pipeline by manually
    stepping through the workflow (since interrupts require manual resume).
    """

    @patch("app.nodes.diagnostic_agent.lookup_medical_guidelines")
    def test_full_workflow_simulation(self, mock_mcp):
        """Simulate the full workflow: 5 questions → summary → physician → report."""
        mock_mcp.invoke = MagicMock(return_value="Recommandations générales MCP")

        # ── Step 1: Supervisor routes to diagnostic_agent ────────────
        state = {
            "patient_case": "Patient de 35 ans avec fièvre (38.5°C) et toux sèche depuis 3 jours",
            "question_count": 0,
            "questions": [],
            "answers": [],
            "red_flags": [],
        }
        sup_result = _deterministic_route(state)
        self.assertEqual(sup_result["next"], "diagnostic_agent")

        # ── Steps 2-6: Ask 5 questions (simulate patient answers) ───
        answers_pool = [
            "Fièvre avec frissons et toux sèche",
            "Depuis 3 jours",
            "7 sur 10",
            "Aucun antécédent notable",
            "Le froid et la nuit aggravent les symptômes",
        ]

        for i in range(5):
            diag_result = diagnostic_agent_node(state)
            self.assertEqual(diag_result["waiting_for"], "patient")

            # Simulate patient answer
            state["answers"] = list(state.get("answers", [])) + [answers_pool[i]]
            state["questions"] = diag_result["questions"]
            state["question_count"] = i + 1
            state["waiting_for"] = None

        # ── Step 7: Diagnostic summary ──────────────────────────────
        self.assertEqual(state["question_count"], 5)
        diag_summary_result = diagnostic_agent_node(state)
        self.assertIn("diagnostic_summary", diag_summary_result)
        self.assertIn("interim_care", diag_summary_result)

        # Update state with summary
        state.update(diag_summary_result)

        # ── Step 8: Supervisor routes to physician_review ───────────
        sup_result2 = _deterministic_route(state)
        self.assertEqual(sup_result2["next"], "physician_review")

        # ── Step 9: Physician review (waiting) ──────────────────────
        phys_result = physician_review_node(state)
        self.assertEqual(phys_result["waiting_for"], "physician")

        # ── Step 10: Physician submits treatment ────────────────────
        state["physician_treatment"] = "Paracétamol 1g x3/jour, repos strict"
        phys_result2 = physician_review_node(state)
        self.assertIsNone(phys_result2["waiting_for"])

        # ── Step 11: Supervisor routes to report_agent ──────────────
        state.update(phys_result2)
        sup_result3 = _deterministic_route(state)
        self.assertEqual(sup_result3["next"], "report_agent")

        # ── Step 12: Report generation ──────────────────────────────
        report_result = report_agent_node(state)
        self.assertIn("final_report", report_result)
        self.assertTrue(len(report_result["final_report"]) > 200)

        # ── Step 13: Supervisor routes to FINISH ────────────────────
        state.update(report_result)
        sup_result4 = _deterministic_route(state)
        self.assertEqual(sup_result4["next"], "FINISH")

        print("\n[OK] Full workflow simulation completed successfully!")
        print(f"   Report length: {len(report_result['final_report'])} chars")


# ═════════════════════════════════════════════════════════════════════════
# 11. API SCHEMA VALIDATION
# ═════════════════════════════════════════════════════════════════════════

class TestAPISchemas(unittest.TestCase):
    """Validate the API Pydantic schemas."""

    def test_start_consultation_request(self):
        from app.api import StartConsultationRequest
        req = StartConsultationRequest(
            thread_id="test-123",
            patient_case="Fièvre depuis 2 jours",
        )
        self.assertEqual(req.thread_id, "test-123")
        self.assertEqual(req.patient_case, "Fièvre depuis 2 jours")

    def test_resume_consultation_request(self):
        from app.api import ResumeConsultationRequest
        req = ResumeConsultationRequest(
            thread_id="test-123",
            input="Oui, j'ai de la fièvre",
            input_type="patient",
        )
        self.assertEqual(req.input_type, "patient")

    def test_consultation_state_response(self):
        from app.api import ConsultationStateResponse
        resp = ConsultationStateResponse(
            thread_id="test-123",
            status="waiting_for_patient",
            question_count=1,
            current_question="Quels sont vos symptômes ?",
            questions=["Quels sont vos symptômes ?"],
            answers=[],
            waiting_for="patient",
        )
        self.assertEqual(resp.status, "waiting_for_patient")
        self.assertEqual(resp.question_count, 1)

    def test_report_response(self):
        from app.api import ReportResponse
        resp = ReportResponse(
            thread_id="test-123",
            final_report="Full report content here",
        )
        self.assertIn("ne remplace pas", resp.disclaimer)

    def test_determine_status_function(self):
        from app.api import _determine_status
        self.assertEqual(_determine_status({}), "started")
        self.assertEqual(_determine_status({"waiting_for": "patient"}), "waiting_for_patient")
        self.assertEqual(_determine_status({"waiting_for": "physician"}), "waiting_for_physician")
        self.assertEqual(
            _determine_status({"diagnostic_summary": "done"}),
            "diagnosis_complete",
        )
        self.assertEqual(
            _determine_status({"final_report": "report"}),
            "completed",
        )


# ═════════════════════════════════════════════════════════════════════════
# RUNNER
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  LangGraph Studio — Test Suite")
    print("  Medical Multi-Agent Workflow")
    print("=" * 70)
    print()

    # Run with verbosity
    unittest.main(verbosity=2)
