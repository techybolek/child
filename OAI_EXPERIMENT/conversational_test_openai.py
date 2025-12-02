"""
Conversational Intelligence Test for OpenAI Agent
"""

import asyncio
import time

from agents import FileSearchTool, RunContextWrapper, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from openai.types.shared.reasoning import Reasoning

from test_definitions import TESTS, save_results, write_report


# Agent setup
file_search = FileSearchTool(
    vector_store_ids=["vs_69210129c50c81919a906d0576237ff5"]
)


class TxChildcareRagContext:
    def __init__(self, workflow_input_as_text: str):
        self.workflow_input_as_text = workflow_input_as_text


def tx_childcare_rag_instructions(run_context: RunContextWrapper[TxChildcareRagContext], _agent: Agent[TxChildcareRagContext]):
    workflow_input_as_text = run_context.context.workflow_input_as_text
    return f"""Concisely answer user questions about Texas childcare assistance programs using information retrieved from the vector store. Focus on providing clear, accurate, and relevant information tailored to the user's query. If information is not found, state this rather than speculating. Ensure that all reasoning (i.e., summarizing or interpreting relevant information from the vector store) is performed before you provide your final answer.

- Use the vector store to retrieve relevant facts or passages.
- Condense the information into a brief, direct response that fully addresses the question.
- If a question is ambiguous, politely ask for clarification.
- If pertinent information is not available, state "No information found in the vector store for this question."

Output format:
- Respond using 1-3 concise sentences per question.
- Do not include any extraneous detail, speculation, or unrelated context.

User query: {workflow_input_as_text}"""


tx_childcare_rag = Agent(
    name="Tx Childcare RAG",
    instructions=tx_childcare_rag_instructions,
    model="gpt-5",
    tools=[file_search],
    model_settings=ModelSettings(
        store=True,
        reasoning=Reasoning(effort="low", summary="auto")
    )
)


async def run_conversation(test: dict) -> dict:
    """Run a single test conversation and capture all turns."""
    print(f"\n{'='*60}")
    print(f"Running: {test['name']}")
    print(f"{'='*60}")

    conversation_history: list[TResponseInputItem] = []
    turns_results = []

    for i, user_query in enumerate(test["turns"], 1):
        print(f"\n[Turn {i}] User: {user_query}")

        conversation_history.append({
            "role": "user",
            "content": [{"type": "input_text", "text": user_query}]
        })

        start_time = time.time()

        with trace("conversational-test"):
            result = await Runner.run(
                tx_childcare_rag,
                input=conversation_history,
                run_config=RunConfig(trace_metadata={
                    "__trace_source__": "conversational-test",
                    "test_id": test["id"],
                    "turn": i
                }),
                context=TxChildcareRagContext(workflow_input_as_text=user_query)
            )

        elapsed = time.time() - start_time

        conversation_history.extend([item.to_input_item() for item in result.new_items])

        response = result.final_output_as(str)
        print(f"[Turn {i}] Assistant: {response}")
        print(f"[Turn {i}] Time: {elapsed:.2f}s")

        turns_results.append({
            "turn": i,
            "user": user_query,
            "assistant": response,
            "elapsed_seconds": round(elapsed, 2)
        })

    return {
        "test_id": test["id"],
        "test_name": test["name"],
        "description": test["description"],
        "success_criteria": test["success_criteria"],
        "turns": turns_results,
        "total_turns": len(turns_results)
    }


async def main():
    print("=" * 60)
    print("CONVERSATIONAL INTELLIGENCE TEST - OAI AGENT")
    print("=" * 60)

    results = {
        "system": "oai_agent",
        "model": "gpt-5",
        "tests": []
    }

    for test in TESTS:
        test_result = await run_conversation(test)
        results["tests"].append(test_result)

    json_path = save_results(results, "conversational_test_openai")
    report_path = write_report(results, "conversational_test_openai", "OAI Agent (GPT-5)")

    print(f"\n{'='*60}")
    print(f"Results saved to: {json_path}")
    print(f"Report saved to: {report_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
