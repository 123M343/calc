from bot_response import get_bot_response
from save_chat import save_message
from load_operations import load_operations
from database_utilities import show_databases, show_tables, find_custom_command
from history import clear_history
from teach_system import handle_teach
from last_10_messages import show_last_10_messages
from search_data import search_all_data
from export_csv import export_all_data_to_csv
from math_logic import (
    apply_followup_operation,
    extract_expression,
    calculator,
    initialize_variables,
    set_last_result,
    get_last_result
)
from math_llm_router import route_math_request
from math_engine import solve_math_task
from logger import logger

last_user_input = None


def process_user_input(user_input):
    global last_user_input

    save_message("user", user_input)
    lower = user_input.lower().strip()

    if lower == "exit":
        last_user_input = lower
        return get_bot_response("goodbye")

    if lower in ["hi", "hello", "hey"]:
        if last_user_input == lower:
            last_user_input = lower
            return "You already said hello. Try asking a math question."
        last_user_input = lower
        return get_bot_response("greeting")

    if lower == "help":
        last_user_input = lower
        return get_bot_response("help")

    custom = find_custom_command(lower)
    if custom:
        last_user_input = lower
        return custom

    if lower == "clear history":
        last_user_input = lower
        return clear_history()

    if lower == "show databases":
        last_user_input = lower
        return show_databases()

    if lower.startswith("show tables"):
        last_user_input = lower
        return show_tables("Chat_Bot_DB")

    if lower == "show last 10":
        last_user_input = lower
        return show_last_10_messages()

    if lower.startswith("search "):
        last_user_input = lower
        return search_all_data(user_input[7:])

    if lower == "export csv":
        last_user_input = lower
        return export_all_data_to_csv()

    if lower.startswith("teach"):
        last_user_input = lower
        return handle_teach(user_input)

    routed_task = route_math_request(user_input)
    if routed_task is not None:
        # route "that" follow-ups into the existing follow-up engine
        if routed_task.get("task_type") == "followup":
            current = get_last_result()
            if current is None:
                last_user_input = lower
                return get_bot_response("no_previous_result")

            op = routed_task["operation"]
            value = routed_task["value"]

            followup_input = f"{op} {value}"
            result = apply_followup_operation(followup_input)
            last_user_input = lower
            return result

        result = solve_math_task(routed_task)
        if result and result.get("success"):
            if "value" in result:
                set_last_result(result["value"])
            last_user_input = lower
            return result["response"]

    followup_result = apply_followup_operation(user_input)
    if followup_result is not None:
        last_user_input = lower
        return followup_result

    expr = extract_expression(user_input)
    if expr == "":
        last_user_input = lower
        return "I’m not sure how to solve that yet. Try rewording it."

    try:
        result = calculator(expr)
        last_user_input = lower
        return result
    except Exception:
        logger.exception("Fallback calculator path failed")
        return "I’m not sure how to solve that yet. Try rewording it."


def get_startup_messages():
    load_operations()
    initialize_variables()
    return [
        get_bot_response("greeting"),
        "Try: what is 5 + 5, solve x^2 + 5x + 6 = 0, add 3, divide by 2, or teach add merge +"
    ]


def run_terminal_chatbot():
    load_operations()
    initialize_variables()

    print(f"ChatBot: {get_bot_response('greeting')}")
    print("ChatBot: Try: what is 5 + 5, solve x^2 + 5x + 6 = 0, add 3, divide by 2, or teach add merge +")

    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\nChatBot: Goodbye!")
            break

        response = process_user_input(user_input)
        print(f"\nChatBot:\n{response}\n")
        save_message("bot", response)

        if user_input.lower().strip() == "exit":
            break


if __name__ == "__main__":
    run_terminal_chatbot()
