from chatbot.chatbot import TexasChildcareChatbot
import sys


def main():
    print("=" * 60)
    print("Texas Childcare Chatbot - Interactive Mode")
    print("=" * 60)
    print("\nInitializing chatbot...")

    try:
        chatbot = TexasChildcareChatbot()
    except Exception as e:
        print(f"Error initializing chatbot: {e}")
        sys.exit(1)

    # Check if question provided as command-line argument
    if len(sys.argv) > 1:
        question = ' '.join(sys.argv[1:])
        response = chatbot.ask(question)
        print("\nANSWER:")
        print(response['answer'])
        if response['sources']:
            print("\n\nSOURCES:")
            for i, source in enumerate(response['sources'], 1):
                print(f"{i}. {source['doc']}, Page {source['page']}")
        return

    print("Ready! Ask me anything about Texas childcare assistance.")
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            # Get user input
            print("-" * 60)
            question = input("\nYour question: ").strip()

            # Check for exit commands
            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            if not question:
                print("Please enter a question.")
                continue

            # Get answer
            print()
            response = chatbot.ask(question)

            # Display answer
            print("\nANSWER:")
            print(response['answer'])

            # Display sources
            if response['sources']:
                print("\n\nSOURCES:")
                for i, source in enumerate(response['sources'], 1):
                    print(f"{i}. {source['doc']}, Page {source['page']}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == '__main__':
    main()
