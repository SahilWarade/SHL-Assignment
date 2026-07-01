import os
from typing import Any, Dict, List, Optional
import google.generativeai as genai
from agent.models import AgentAction, AgentResponse, Message, ConversationState
from agent import tools
from agent.prompts.system_prompt import SYSTEM_PROMPT
from agent.prompts.clarification_prompt import CLARIFICATION_PROMPT
from agent.prompts.recommendation_prompt import RECOMMENDATION_PROMPT
from agent.prompts.comparison_prompt import COMPARISON_PROMPT
from agent.prompts.refusal_prompt import REFUSAL_PROMPT
from agent.prompts.planner_prompt import PLANNER_PROMPT
from agent.utils import logger


class AgentPlanner:
    """
    Formulates prompt payloads, triggers tools, and generates replies
    based on intent classification and conversational states.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self._setup_gemini()

    def _setup_gemini(self):
        """Initializes Gemini configure settings."""
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def detect_comparison_targets(self, query: str) -> List[str]:
        """Extracts target assessment slugs that the user wants to compare."""
        q = query.lower()
        targets = []
        
        if "opq" in q or "personality" in q:
            targets.append("opq")
        if "verify" in q or "cognitive" in q:
            if "numerical" in q:
                targets.append("verify-numerical-reasoning")
            elif "verbal" in q:
                targets.append("verify-verbal-reasoning")
            elif "deductive" in q:
                targets.append("verify-deductive-reasoning")
            else:
                targets.append("verify-g")
        if "sjt" in q or "situational" in q:
            targets.append("situational-judgement-tests")
        if "motivation" in q or "mq" in q:
            targets.append("shl-motivational-questionnaire")
        if "coding" in q or "technical" in q:
            targets.append("shl-coding-skills-assessment-and-simulations")

        return list(set(targets))[:2]

    def run_live_gemini(self, system_instruction: str, prompt_content: str) -> str:
        """Sends compiled instructions to the Gemini API."""
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt_content)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}", exc_info=True)
            return "[Error: LLM execution failed. Please verify API configurations.]"

    def run_consultant_simulator(
        self, 
        state: ConversationState, 
        retrieved_data: List[Dict[str, Any]], 
        comparison_data: Dict[str, Any]
    ) -> str:
        """
        Local rules-based consultant simulator for offline test runs.
        Ensures high-fidelity responses matching official catalog parameters.
        """
        action = state.intent
        constraints = state.collected_information

        if action == AgentAction.REFUSE:
            return (
                "As an SHL Talent Assessment Consultant, I can only help you search, compare, "
                "and select official SHL assessments from our catalog. I cannot provide general "
                "interview questions, programming code, or legal opinions. Please let me know which "
                "SHL assessments you would like to explore!"
            )

        elif action == AgentAction.CLARIFY:
            if not constraints.get("job_role"):
                return (
                    "Welcome! I am here to help you select the optimal SHL assessments for your team. "
                    "To start, could you please specify the target job role (e.g. Java Backend Developer, "
                    "Sales Manager, or Customer Support Agent) you are hiring for?"
                )
            elif not constraints.get("experience_level") and not constraints.get("assessment_type"):
                return (
                    f"Thanks for the context on the {constraints['job_role']} role. To narrow this down: "
                    "what experience level are you looking at (e.g. entry-level, senior)? Also, are you "
                    "interested in measuring cognitive reasoning, technical skills, or behavioral style?"
                )
            elif not constraints.get("experience_level"):
                return f"Got it. What experience level is this {constraints['job_role']} role (e.g., graduate, manager, senior professional)?"
            else:
                return f"Could you clarify if you prefer a cognitive reasoning test, technical programming skills tests, or situational judgement simulations for this role?"

        elif action == AgentAction.COMPARE:
            item1_res = comparison_data.get("assessment1", {})
            item2_res = comparison_data.get("assessment2", {})
            
            if not item1_res.get("found") or not item2_res.get("found"):
                return (
                    "I searched the catalog, but I could not find all of the specific assessments you requested "
                    "to compare. Please verify the names (e.g., OPQ, SHL Verify, or SJT) and try again!"
                )
                
            data1 = item1_res["data"]
            data2 = item2_res["data"]
            
            return (
                f"### Side-by-Side Comparison: {data1['name']} vs {data2['name']}\n\n"
                f"Here is how these two SHL solutions compare based on official catalog metadata:\n\n"
                f"*   **Category**:\n"
                f"    - *{data1['name']}*: {data1.get('category', 'Not specified')}\n"
                f"    - *{data2['name']}*: {data2.get('category', 'Not specified')}\n"
                f"*   **Assessment Type**:\n"
                f"    - *{data1['name']}*: {data1.get('assessment_type', 'Not specified')}\n"
                f"    - *{data2['name']}*: {data2.get('assessment_type', 'Not specified')}\n"
                f"*   **Typical Duration**:\n"
                f"    - *{data1['name']}*: {data1.get('duration', 'Not specified')}\n"
                f"    - *{data2['name']}*: {data2.get('duration', 'Not specified')}\n"
                f"*   **Skills Measured**:\n"
                f"    - *{data1['name']}*: {', '.join(data1.get('skills', []))}\n"
                f"    - *{data2['name']}*: {', '.join(data2.get('skills', []))}\n"
                f"*   **Adaptive Format**:\n"
                f"    - *{data1['name']}*: {'Yes' if data1.get('adaptive') else 'No'}\n"
                f"    - *{data2['name']}*: {'Yes' if data2.get('adaptive') else 'No'}\n\n"
                f"If you need to explore or run either test, you can access details at their respective catalog links:\n"
                f"- [{data1['name']}]({data1['url']})\n"
                f"- [{data2['name']}]({data2['url']})"
            )

        else:  # RECOMMEND or REFINE
            if not retrieved_data:
                return (
                    "I performed a semantic search of the SHL catalog but did not find any specific matches. "
                    "Could you please expand or modify your job description or assessment criteria?"
                )
                
            reply_lines = [
                f"Based on your requirements (Job Role: {constraints.get('job_role')}, Level: {constraints.get('experience_level')}), "
                f"here are the top recommended SHL test solutions:\n"
            ]
            for item in retrieved_data:
                name = item.get("name")
                url = item.get("url")
                desc = item.get("description", "")
                duration = item.get("duration", "30 minutes")
                skills = ", ".join(item.get("skills", []))
                
                reply_lines.append(
                    f"*   **[{name}]({url})**\n"
                    f"    - *Type*: {item.get('assessment_type')}\n"
                    f"    - *Duration*: {duration}\n"
                    f"    - *Skills*: {skills}\n"
                    f"    - *Description*: {desc[:180]}...\n"
                )
                
            reply_lines.append("Would you like to refine this search by adding criteria (such as duration limits or adaptive testing format)?")
            return "\n".join(reply_lines)

    def plan_response(self, messages: List[Message], state: ConversationState) -> AgentResponse:
        """Processes the state and tools outputs to build the final response."""
        latest_user_msg = [m.content for m in messages if m.role == "user"][-1]

        # Invoke tools based on state flag requirements
        retrieved_items = []
        comparison_data = {}

        if state.retrieval_required:
            search_query = f"{state.collected_information.get('job_role', '')} {state.collected_information.get('experience_level', '')} {state.collected_information.get('assessment_type', '')}"
            filters = {}
            if state.collected_information.get("assessment_type"):
                filters["category"] = state.collected_information["assessment_type"]
            if state.collected_information.get("language"):
                filters["language"] = state.collected_information["language"]
                
            retrieved_items = tools.search_assessments(search_query, filters=filters)

        elif state.comparison_requested:
            targets = self.detect_comparison_targets(latest_user_msg)
            if len(targets) == 2:
                comparison_data = tools.compare_assessments(targets[0], targets[1])
            elif len(targets) == 1:
                alt = "verify-g" if targets[0] == "opq" else "opq"
                comparison_data = tools.compare_assessments(targets[0], alt)
            else:
                comparison_data = tools.compare_assessments("opq", "verify-g")

        # Compile response text
        reply = ""
        if self.api_key:
            # Setup prompt and run Gemini
            system_instruction = SYSTEM_PROMPT + "\n" + PLANNER_PROMPT
            
            if state.intent == AgentAction.REFUSE:
                system_instruction += "\n" + REFUSAL_PROMPT
                prompt = f"User Request: '{latest_user_msg}'\nReply brief and polite."
            elif state.intent == AgentAction.CLARIFY:
                system_instruction += "\n" + CLARIFICATION_PROMPT
                prompt = (
                    f"Conversation State: {state.model_dump()}\n"
                    f"History:\n{[f'{m.role}: {m.content}' for m in messages]}\n"
                    f"Ask follow-up clarification questions."
                )
            elif state.intent == AgentAction.COMPARE:
                system_instruction += "\n" + COMPARISON_PROMPT
                prompt = f"Retrieved comparative details:\n{comparison_data}\nGenerate the side-by-side markdown comparison."
            else: # RECOMMEND or REFINE
                system_instruction += "\n" + RECOMMENDATION_PROMPT
                prompt = (
                    f"Hiring constraints: {state.collected_information}\n"
                    f"Retrieved assessments from catalog database:\n{retrieved_items}\n"
                    f"Summarize and format recommendations using bullet points and official URLs."
                )
            
            reply = self.run_live_gemini(system_instruction, prompt)
        else:
            # Consultant Simulator
            reply = self.run_consultant_simulator(state, retrieved_items, comparison_data)

        end_of_conversation = state.intent in [AgentAction.RECOMMEND, AgentAction.REFINE] and len(retrieved_items) > 0

        return AgentResponse(
            action=state.intent,
            reply=reply,
            recommendations=retrieved_items,
            end_of_conversation=end_of_conversation
        )
