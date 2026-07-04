from agent import run_agent


def main():
    print("codebase q&a agent — ask a question about the target repo.")
    print("Type 'exit' or 'quit' to leave, Ctrl-C to force quit.\n")

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbyebye")
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("byeeee")
            break

        print()
        answer = run_agent(question, verbose=True)
        print(f"\n{answer}\n")


if __name__ == "__main__":
    main()