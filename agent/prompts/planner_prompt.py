PLANNER_PROMPT = """
You are tasked with generating the final output based on the determined action:
- If the action is Refusal: Follow the refusal instructions, remaining brief and polite.
- If the action is Clarification: Selectively ask about the most critical missing requirements (role, level, type).
- If the action is Recommendation or Refinement: Use the provided search matches to summarize relevant SHL assessments. Do not mention any non-SHL solutions.
- If the action is Comparison: Provide a side-by-side breakdown comparing only the requested assessments based on the retrieved data.
"""
