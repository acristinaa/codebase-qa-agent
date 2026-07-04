import json

from dotenv import load_dotenv
from openai import OpenAI
import os

from tools import search_code, read_file, find_dependents, find_definition

load_dotenv()

client = OpenAI()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

SYSTEM_PROMPT = (
    "you are a codebase assistant. use tools to investigate before answering. "
    "chain tool calls with a clear purpose — don't repeat a search with slightly "
    "reworded queries; if a search doesn't help, try a different tool instead. "
    "for 'what would break if X changed' questions: first find X's definition, "
    "then call find_dependents with X's bare name (no class prefix) to find callers, "
    "then only read_file if you need to see a specific caller's context. "
    "stop and answer as soon as you have enough evidence — you don't need to see "
    "every line of a file to answer. always ground your answer in what the tools "
    "actually returned, and cite file:line for anything you claim."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Semantic search over the codebase. Returns the top-k relevant code chunks (functions/classes) for a natural language query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language description of what to find"},
                    "k": {"type": "integer", "description": "Number of results to return", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file (optionally a specific line range) from the target repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the repo root, e.g. 'src/flask/app.py'"},
                    "start_line": {"type": "integer", "description": "First line to read (1-indexed)"},
                    "end_line": {"type": "integer", "description": "Last line to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_dependents",
            "description": "Find likely callers/usages of a function or class name across the repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string", "description": "The exact function or class name to search for"},
                },
                "required": ["function_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_definition",
            "description": "Find where a function or class is defined in the repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The exact function or class name to find"},
                },
                "required": ["name"],
            },
        },
    },
]

TOOL_FUNCS = {
    "search_code": search_code,
    "read_file": read_file,
    "find_dependents": find_dependents,
    "find_definition": find_definition,
}


def call_tool(name, args):
    try:
        return TOOL_FUNCS[name](**args)
    except Exception as e:
        return {"error": str(e)}


def run_agent(question, max_turns=8, verbose=True):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            if verbose:
                print(f"[tool call] {name}({args})")

            result = call_tool(name, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, default=str)[:4000],  # cap size fed back to the model
            })

    return "Stopped after max_turns without a final answer — the question may need a narrower scope."


if __name__ == "__main__":
    questions = [
        "What calls add_url_rule?",
        "What would break if I changed the signature of Scaffold.route?",
    ]
    for q in questions:
        print(f"\n{'=' * 60}\nQ: {q}\n{'=' * 60}")
        answer = run_agent(q)
        print(f"\nA: {answer}\n")