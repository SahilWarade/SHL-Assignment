COMPARISON_PROMPT = """
The user wants to compare specific SHL assessments.
Here is the retrieved metadata for the requested assessments:
{comparison_data}

Your task:
- Compare the assessments side-by-side on specific criteria: Category, Format/Type, Duration, Skills measured, Adaptive format, and Target Job Levels.
- Rely strictly on the metadata provided. If a field is empty or null, state that it is not documented in the catalog. Do not invent details.
"""
