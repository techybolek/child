import asyncio
from agents import FileSearchTool, RunContextWrapper, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from openai.types.shared.reasoning import Reasoning
from pydantic import BaseModel

# Tool definitions
file_search = FileSearchTool(
  vector_store_ids=[
    "vs_69210129c50c81919a906d0576237ff5"
  ]
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
Your response MUST follow this exact structure:

ANSWER:
[Your 1-4 sentence response here]

SOURCES:
- [filename1.pdf]
- [filename2.pdf]

Rules for sources:
- List each source document filename on its own line, prefixed with "- "
- Only include files that directly contributed to your answer
- If no sources were used, write "- None"

Example:

**Input:**
What are the eligibility criteria for Texas childcare assistance?

**Output:**
ANSWER:
To qualify for Texas childcare assistance, you must be a Texas resident, meet income requirements based on State Median Income brackets, and be working or attending school or job training.

SOURCES:
- child-care-services-guide-twc.pdf
- bcy-26-income-eligibility-and-maximum-psoc-twc.pdf

---

**Reminder**: First, retrieve and reason using relevant information from the vector store, then provide your answer in the exact format shown above with ANSWER: and SOURCES: sections.

User query:  {workflow_input_as_text}"""
tx_childcare_rag = Agent(
  name="Tx Childcare RAG",
  instructions=tx_childcare_rag_instructions,
  model="gpt-5-nano",
  tools=[
    file_search
  ],
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="low",
      summary="auto"
    )
  )
)


class WorkflowInput(BaseModel):
  input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
  with trace("cohort-2"):
    state = {

    }
    workflow = workflow_input.model_dump()
    conversation_history: list[TResponseInputItem] = [
      {
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": workflow["input_as_text"]
          }
        ]
      }
    ]
    tx_childcare_rag_result_temp = await Runner.run(
      tx_childcare_rag,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_68f780307a90819099289673c30d5b88098cf99e2522889c"
      }),
      context=TxChildcareRagContext(workflow_input_as_text=workflow["input_as_text"])
    )

    conversation_history.extend([item.to_input_item() for item in tx_childcare_rag_result_temp.new_items])

    tx_childcare_rag_result = {
      "output_text": tx_childcare_rag_result_temp.final_output_as(str)
    }
    return tx_childcare_rag_result


if __name__ == "__main__":
    result = asyncio.run(run_workflow(WorkflowInput(input_as_text="What are the eligibility criteria for Texas childcare assistance?")))
    print(result)
