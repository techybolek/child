"""Intent classification node for LangGraph RAG pipeline"""

from openai import OpenAI
from groq import Groq
from ... import config
from ...prompts import INTENT_CLASSIFICATION_PROMPT


def classify_node(state: dict) -> dict:
    """Classify intent using LLM.

    Reuses the same logic as IntentRouter.classify_intent().

    Args:
        state: RAGState with 'query' field

    Returns:
        dict with 'intent' field ('information' or 'location_search')
    """
    query = state["query"]

    # Check for overrides in state, fall back to config
    provider = state.get("provider_override") or config.INTENT_CLASSIFIER_PROVIDER
    model = state.get("intent_model_override") or config.INTENT_CLASSIFIER_MODEL

    # Initialize client based on provider
    if provider == 'groq':
        client = Groq(api_key=config.GROQ_API_KEY)
    else:
        client = OpenAI(api_key=config.OPENAI_API_KEY)

    print(f"[Classify Node] Using model: {model}")
    prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)

    # Build API parameters
    params = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "seed": config.SEED,
    }

    # Check if model supports reasoning (GPT-5 or openai/gpt-oss-20b)
    is_reasoning_model = (
        model.startswith('gpt-5') or
        model == 'openai/gpt-oss-20b'
    )

    if is_reasoning_model:
        if model.startswith('gpt-5'):
            params['max_completion_tokens'] = 200
        else:
            params['max_tokens'] = 200
    else:
        params['max_tokens'] = 50

    try:
        response = client.chat.completions.create(**params)

        content = response.choices[0].message.content
        if content is None:
            print(f"[Classify Node] WARNING: Response content is None, defaulting to 'information'")
            return {"intent": "information"}

        intent = content.strip().lower()
        print(f"[Classify Node] Raw response: {intent}")

        # Validate intent
        valid_intents = ["information", "location_search"]
        if intent not in valid_intents:
            print(f"[Classify Node] WARNING: Unknown intent '{intent}', defaulting to 'information'")
            intent = "information"

        print(f"[Classify Node] Classified as: {intent}")
        return {"intent": intent}

    except Exception as e:
        print(f"[Classify Node] ERROR: {type(e).__name__}: {str(e)}")
        print(f"[Classify Node] Defaulting to 'information' due to error")
        return {"intent": "information"}
