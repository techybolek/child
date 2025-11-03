"""
Auto-generated test for failed evaluation

Source: bcy-26-income-eligibility-and-maximum-psoc-twc-qa.md Q4
Composite Score: 41.7/100 (Failed threshold: 70)
Generated: 2025-11-01 13:01:40
"""

from chatbot.handlers.rag_handler import RAGHandler

# Expected answer (from Q&A file):
# A family of 5 with bi-weekly income must earn no more than $4,106 per pay period to remain eligible for the program in Board Contract Year 2026. This corresponds to an annual income limit of $106,768.

# Initialize handler (bypasses intent detection, goes directly to RAG)
handler = RAGHandler()

# Failed question
question = 'If a family of 5 earns income bi-weekly, what is their maximum income to remain eligible for the program in 2026?'

# Query chatbot via RAGHandler
response = handler.handle(question)

print("QUESTION:")
print(question)

print("\nEXPECTED ANSWER:")
print("""A family of 5 with bi-weekly income must earn no more than $4,106 per pay period to remain eligible for the program in Board Contract Year 2026. This corresponds to an annual income limit of $106,768.""")

print("\nCHATBOT ANSWER:")
print(response['answer'])

print("\nSOURCES:")
if response['sources']:
    for source in response['sources']:
        print(f"- {source['doc']}, Page {source['page']}")
else:
    print("No sources cited")
