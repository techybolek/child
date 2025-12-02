from chatbot.chatbot import TexasChildcareChatbot
from chatbot import config
import argparse
import os
import sys


def get_handler(mode: str):
    """Get appropriate handler based on mode"""
    if mode == 'kendra':
        from chatbot.handlers.kendra_handler import KendraHandler
        return KendraHandler()
    elif mode == 'openai':
        from chatbot.handlers.openai_agent_handler import OpenAIAgentHandler
        return OpenAIAgentHandler()
    else:
        # For hybrid/dense, use the standard chatbot which handles mode internally
        return None


def main():
    parser = argparse.ArgumentParser(description='Texas Childcare Chatbot - Interactive Mode')
    parser.add_argument('--mode', type=str, choices=['hybrid', 'dense', 'kendra', 'openai'],
                        help='Retrieval mode (default: from RETRIEVAL_MODE env or config)')
    parser.add_argument('question', nargs='*', help='Question to ask (optional)')
    args = parser.parse_args()

    # Determine mode from args, env, or config
    mode = args.mode or os.getenv('RETRIEVAL_MODE', config.RETRIEVAL_MODE)

    print("=" * 60)
    print("Texas Childcare Chatbot - Interactive Mode")
    print("=" * 60)
    print(f"\nMode: {mode}")
    print("Initializing chatbot...")

    try:
        if mode in ('kendra', 'openai'):
            handler = get_handler(mode)
            chatbot = None
        else:
            chatbot = TexasChildcareChatbot()
            handler = None
    except Exception as e:
        print(f"Error initializing chatbot: {e}")
        sys.exit(1)

    # Helper function to ask question
    def ask_question(question):
        if handler:
            return handler.handle(question)
        else:
            return chatbot.ask(question)

    # Check if question provided as command-line argument
    if args.question:
        question = ' '.join(args.question)
        response = ask_question(question)
        print("\nANSWER:")
        print(response['answer'])
        if response['sources']:
            print("\n\nSOURCES:")
            for i, source in enumerate(response['sources'], 1):
                print(f"{i}. {source['doc']}, Page {source.get('page', 'N/A')}")
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
            response = ask_question(question)

            # Display answer
            print("\nANSWER:")
            print(response['answer'])

            # Display sources
            if response['sources']:
                print("\n\nSOURCES:")
                for i, source in enumerate(response['sources'], 1):
                    print(f"{i}. {source['doc']}, Page {source.get('page', 'N/A')}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")


if __name__ == '__main__':
    main()
