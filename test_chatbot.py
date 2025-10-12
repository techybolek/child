from chatbot.chatbot import TexasChildcareChatbot

chatbot = TexasChildcareChatbot()

# Ask a question
response = chatbot.ask("What are the income limits for a family of 3 in BCY 2026?")

print("ANSWER:")
print(response['answer'])

print("\nSOURCES:")
for source in response['sources']:
    print(f"- {source['doc']}, Page {source['page']}")
