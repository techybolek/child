from chatbot.chatbot import TexasChildcareChatbot

chatbot = TexasChildcareChatbot()

q1 = "How much is the maximum parent share of cost for a single-person household on a monthly basis?"
q2 = "What are the income limits for a family of 3 in BCY 2026?"
# Ask a question
response = chatbot.ask(q1)

print("ANSWER:")
print(response['answer'])

print("\nSOURCES:")
for source in response['sources']:
    print(f"- {source['doc']}, Page {source['page']}")
