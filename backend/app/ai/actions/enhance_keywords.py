from app.ai.prompts import SEARCH_TERMS_PROMPT
from app.services.llm_service import default_llm


async def enhance_search_keywords(user_query: str) -> str:
    """
    Enhance user query by extracting and improving keywords for paper search.

    Args:
        user_query: The user's search query/question

    Returns:
        Enhanced keywords string optimized for paper search
    """
    try:
        prompt = SEARCH_TERMS_PROMPT.format(user_query=user_query.strip())
        response = await default_llm.acomplete(prompt)
        enhanced_query = response.text.strip()

        # Remove any quotes that the LLM might have added
        enhanced_query = enhanced_query.strip('"').strip("'").strip()

        # Fallback to original if enhancement failed or is empty
        if not enhanced_query or len(enhanced_query) < 3:
            return user_query.strip()

        return enhanced_query

    except Exception:
        # Fallback to original query on error
        return user_query.strip()
