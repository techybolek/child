"""
Master context prompt for contextual retrieval.

This static context is prepended to all documents and chunks to establish
the domain and ensure consistent semantic grounding across all retrieval.
"""

MASTER_CONTEXT = """This is official Texas Workforce Commission (TWC) documentation regarding childcare assistance programs. The content covers program eligibility requirements, income limits, payment procedures, provider regulations, and administrative guidelines for childcare services in Texas. The primary programs discussed are the Child Care Development Fund (CCDF) and Provider Services Operational Consultation (PSOC)."""
