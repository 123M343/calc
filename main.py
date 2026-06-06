import re
import time
from typing import Any, Optional
from bot_response import get_bot_response
from save_chat import save_message
from load_operations import load_operations
from database_utilities import (
    ensure_saved_equations_table,
    ensure_user_memory_table,
    find_custom_command,
    get_user_memory,
    load_saved_equation,
    save_user_memory,
    save_equation_to_db,
    show_databases,
    show_tables,
)
from history import clear_history
from teach_system import handle_teach
from last_10_messages import show_last_10_messages
from search_data import search_all_data
from export_csv import export_all_data_to_csv
from graphing import is_graph_request
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
from logger import log_command, log_crash, log_result
from typo_utils import correct_command_text

last_user_input: Optional[str] = None
last_unit_result: Optional[dict[str, Any]] = None


def normalize_memory_key(key: str) -> str:
    return " ".join(str(key).lower().strip().split())


def parse_memory_store(text: str) -> Optional[tuple[str, str]]:
    match = re.fullmatch(r'my\s+(.+?)\s+is\s+(.+)', text, re.IGNORECASE)
    if not match:
        return None

    key = normalize_memory_key(match.group(1))
    value = match.group(2).strip()

    if not key or not value:
        return None

    return key, value


def parse_memory_lookup(text: str) -> Optional[str]:
    patterns = [
        r'what is my\s+(.+)',
        r"what's my\s+(.+)",
        r'tell me my\s+(.+)',
    ]

    for pattern in patterns:
        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if match:
            key = normalize_memory_key(match.group(1))
            if key:
                return key

    return None


def parse_save_equation(text: str) -> Optional[tuple[str, str]]:
    patterns = [
        r'save equation\s+([a-zA-Z][a-zA-Z0-9_\-\s]*)\s*=\s*(.+)',
        r'save equation\s+([a-zA-Z][a-zA-Z0-9_\-\s]*)\s+as\s+(.+)',
    ]

    for pattern in patterns:
        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if match:
            name = normalize_memory_key(match.group(1))
            equation = match.group(2).strip()
            if name and equation:
                return name, equation

    return None


def parse_load_equation(text: str) -> Optional[str]:
    patterns = [
        r'load equation\s+([a-zA-Z][a-zA-Z0-9_\-\s]*)',
        r'load\s+([a-zA-Z][a-zA-Z0-9_\-\s]*)',
    ]

    for pattern in patterns:
        match = re.fullmatch(pattern, text, re.IGNORECASE)
        if match:
            name = normalize_memory_key(match.group(1))
            if name:
                return name

    return None


def parse_followup_unit_conversion(text: str) -> Optional[str]:
    match = re.fullmatch(r'(?:convert\s+)?to\s+([a-zA-Z]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).lower().strip()
    return None


def process_user_input(user_input: str) -> str:
    global last_user_input, last_unit_result

    # This is the main runtime entry for chat requests from the GUI, API, and terminal app.
    start_time = time.perf_counter()
    save_message("user", user_input)
    lower = user_input.lower().strip()
    command_text = correct_command_text(lower)
    log_command(user_input)
    ensure_user_memory_table()
    ensure_saved_equations_table()

    if command_text == "exit":
        last_user_input = lower
        response = get_bot_response("goodbye")
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if lower in ["hi", "hello", "hey"]:
        if last_user_input == lower:
            last_user_input = lower
            response = "You already said hello. Try asking a math question."
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
            return response
        last_user_input = lower
        response = get_bot_response("greeting")
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text == "help":
        last_user_input = lower
        response = get_bot_response("help")
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    custom = find_custom_command(lower)
    if custom:
        last_user_input = lower
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return custom

    if command_text == "clear history":
        last_user_input = lower
        response = clear_history()
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text == "show databases":
        last_user_input = lower
        response = show_databases()
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text.startswith("show tables"):
        last_user_input = lower
        response = show_tables("Chat_Bot_DB")
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text == "show last 10":
        last_user_input = lower
        response = show_last_10_messages()
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text.startswith("search "):
        last_user_input = lower
        response = search_all_data(command_text[7:])
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text == "export csv":
        last_user_input = lower
        response = export_all_data_to_csv()
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if command_text.startswith("teach"):
        last_user_input = lower
        response = handle_teach(command_text)
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    saved_equation = parse_save_equation(user_input)
    if saved_equation is not None:
        name, equation = saved_equation
        last_user_input = lower
        saved, error_message = save_equation_to_db(name, equation)
        if saved:
            response = f'Saved equation "{name}": {equation}'
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
            return response
        response = error_message or "I tried to save that equation, but the database was unavailable."
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
        return response

    load_equation_name = parse_load_equation(user_input)
    if load_equation_name is not None:
        equation = load_saved_equation(load_equation_name)
        last_user_input = lower
        if equation is None:
            response = f'I do not have a saved equation named "{load_equation_name}".'
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
            return response
        response = f'{load_equation_name} = {equation}'
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    memory_store = parse_memory_store(user_input)
    if memory_store is not None:
        key, value = memory_store
        if save_user_memory(key, value):
            last_user_input = lower
            response = f"I’ll remember that your {key} is {value}."
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
            return response
        last_user_input = lower
        response = "I tried to save that memory, but the database was unavailable."
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
        return response

    memory_lookup = parse_memory_lookup(user_input)
    if memory_lookup is not None:
        remembered_value = get_user_memory(memory_lookup)
        last_user_input = lower
        if remembered_value is None:
            response = f"I don’t know your {memory_lookup} yet."
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
            return response
        response = f"Your {memory_lookup} is {remembered_value}."
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    if is_graph_request(user_input):
        last_user_input = lower
        response = "Graph requests are available in the Qt GUI. Try: graph y = x^2 and y = 2x + 1"
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return response

    followup_unit = parse_followup_unit_conversion(user_input)
    if followup_unit is not None and last_unit_result is not None:
        followup_task: dict[str, Any] = {
            "task_type": "conversion",
            "operation": "convert_unit",
            "value": last_unit_result["value"],
            "from_unit": last_unit_result["unit"],
            "to_unit": followup_unit,
        }
        result = solve_math_task(followup_task)
        last_user_input = lower
        if result and result.get("success"):
            if "value" in result:
                set_last_result(result["value"])
            if "unit" in result:
                last_unit_result = {
                    "value": result["value"],
                    "unit": result["unit"],
                    "dimension": result.get("dimension"),
                }
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
            return result["response"]
        response = result["response"] if result else "I could not convert that unit."
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
        return response

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
            if result is None:
                log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
                return get_bot_response("no_previous_result")
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
            return result

        result = solve_math_task(routed_task)
        if result and result.get("success"):
            if "value" in result:
                set_last_result(result["value"])
            if "unit" in result:
                last_unit_result = {
                    "value": result["value"],
                    "unit": result["unit"],
                    "dimension": result.get("dimension"),
                }
            last_user_input = lower
            log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
            return result["response"]

    followup_result = apply_followup_operation(user_input)
    if followup_result is not None:
        last_user_input = lower
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return followup_result

    expr = extract_expression(user_input)
    if expr == "":
        last_user_input = lower
        response = "I’m not sure how to solve that yet. Try rewording it."
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "error")
        return response

    try:
        result = calculator(expr)
        last_unit_result = None
        last_user_input = lower
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "success")
        return result
    except Exception:
        log_crash("Fallback calculator path failed")
        response = "I’m not sure how to solve that yet. Try rewording it."
        log_result(user_input, (time.perf_counter() - start_time) * 1000, "crash")
        return response


def get_startup_messages() -> list[str]:
    # Load shared app state before building the first messages shown to the user.
    load_operations()
    initialize_variables()
    ensure_user_memory_table()
    ensure_saved_equations_table()
    return [
        get_bot_response("greeting"),
        "Try: what is 400 divided by 2, save equation velocity = distance / time, load velocity, graph y = x^2, or times 3"
    ]


def run_terminal_chatbot():
    # This runner starts the plain terminal version of the chatbot.
    load_operations()
    initialize_variables()
    ensure_user_memory_table()
    ensure_saved_equations_table()

    print(f"ChatBot: {get_bot_response('greeting')}")
    print("ChatBot: Try: what is 400 divided by 2, save equation velocity = distance / time, load velocity, graph y = x^2, or times 3")

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
    # Running this file directly starts the terminal chatbot instead of the Qt GUI.
    run_terminal_chatbot()
