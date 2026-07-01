RECOMMENDATION_PROMPT = """
You have collected sufficient information to recommend SHL assessments.
Here is the list of top semantically matching SHL assessments retrieved from the database:
{retrieved_data}

Your task:
- Formulate a response explaining why these specific assessments fit the user's requirements (job role, levels, constraints).
- Mention the key details of the assessments (such as name, format, duration, skills measured, and catalog URL) strictly using the retrieved metadata.
- Provide links to their official URLs exactly as retrieved.
- Keep the response organized, utilizing bullet points.
"""
