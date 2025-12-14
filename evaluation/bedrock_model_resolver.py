"""Utility to resolve short model names to Bedrock model identifiers.

Supports both Amazon and Anthropic models. Anthropic models may require
use case form submission on some accounts.
"""

import os
import boto3


# Models that work with direct foundation model ARN (on-demand)
FOUNDATION_MODELS = {
    # Amazon models (no use case form required)
    'nova-micro': 'amazon.nova-micro-v1:0',
    'nova-lite': 'amazon.nova-lite-v1:0',
    'nova-pro': 'amazon.nova-pro-v1:0',
    'titan-express': 'amazon.titan-text-express-v1',
    'titan-lite': 'amazon.titan-text-lite-v1',

    # Anthropic models (may require use case form)
    '3-haiku': 'anthropic.claude-3-haiku-20240307-v1:0',
    '3.5-sonnet': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
    'instant': 'anthropic.claude-instant-v1',
}

# Models that require inference profiles (newer Anthropic models)
INFERENCE_PROFILE_MODELS = {
    '3.5-haiku': 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
    '4.5-haiku': 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
    '4-5': 'us.anthropic.claude-haiku-4-5-20251001-v1:0',
}


def resolve_model_arn(short_name: str) -> tuple[str, str, str]:
    """Resolve a short model name to a Bedrock model ARN.

    Args:
        short_name: Short version like "nova-micro", "3-haiku", "4-5"

    Returns:
        Tuple of (model_id, model_arn, display_name)

    Raises:
        ValueError: If no matching model found
    """
    region = os.getenv('AWS_REGION', 'us-east-1')
    normalized = short_name.lower().replace('_', '-')

    # Check foundation models first (more reliable)
    if normalized in FOUNDATION_MODELS:
        model_id = FOUNDATION_MODELS[normalized]
        model_arn = f"arn:aws:bedrock:{region}::foundation-model/{model_id}"
        display_name = _get_display_name(model_id)
        return model_id, model_arn, display_name

    # Check inference profile models
    if normalized in INFERENCE_PROFILE_MODELS:
        profile_id = INFERENCE_PROFILE_MODELS[normalized]
        # Get the full ARN from AWS
        client = boto3.client('bedrock', region_name=region)
        response = client.list_inference_profiles(maxResults=100)

        for profile in response.get('inferenceProfileSummaries', []):
            if profile.get('inferenceProfileId') == profile_id:
                profile_arn = profile.get('inferenceProfileArn')
                display_name = _get_display_name(profile_id)
                return profile_id, profile_arn, display_name

        raise ValueError(f"Inference profile '{profile_id}' not found in account")

    # Try to find by pattern matching
    available = list(FOUNDATION_MODELS.keys()) + list(INFERENCE_PROFILE_MODELS.keys())
    raise ValueError(
        f"Unknown model '{short_name}'. "
        f"Available: {available}"
    )


def _get_display_name(model_id: str) -> str:
    """Extract a display-friendly name from model ID."""
    # Handle formats:
    # "amazon.nova-micro-v1:0"
    # "anthropic.claude-3-haiku-20240307-v1:0"
    # "us.anthropic.claude-haiku-4-5-20251001-v1:0"

    # Remove provider prefix and version suffix
    name = model_id.split('.')[-1]  # Get last part after dots
    name = name.split(':')[0]  # Remove version suffix

    # Remove date and version patterns
    parts = name.split('-')
    clean_parts = []
    for part in parts:
        # Skip date patterns (8 digits) and version patterns (v1, v2)
        if len(part) == 8 and part.isdigit():
            break
        if part.startswith('v') and part[1:].isdigit():
            break
        clean_parts.append(part)

    # Format nicely
    name = ' '.join(clean_parts).title()

    # Convert version numbers like "3 5" to "3.5"
    import re
    name = re.sub(r'(\d) (\d)', r'\1.\2', name)

    return name


# Legacy functions for compatibility
def resolve_model(short_name: str, provider: str = "anthropic") -> str:
    """Legacy function - returns model_id."""
    model_id, _, _ = resolve_model_arn(short_name)
    return model_id


def resolve_inference_profile(short_name: str) -> tuple[str, str]:
    """Legacy function - returns (model_id, model_arn)."""
    model_id, model_arn, _ = resolve_model_arn(short_name)
    return model_id, model_arn


def get_model_display_name(model_id: str) -> str:
    """Legacy function - returns display name."""
    return _get_display_name(model_id)
