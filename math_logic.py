import re
from typing import Any, TypeAlias, cast

import sympy as sp
from bot_response import get_bot_response
from database_utilities import load_saved_variables, save_variable_to_db
from load_operations import replace_operation_words
from logger import logger
from typo_utils import correct_math_words

SympyLocals: TypeAlias = dict[str, Any]
variables: dict[str, Any] = {}
last_result: Any | None = None

SCIENTIFIC_CONSTANTS = {
    "pi": sp.pi,
    "e": sp.E,
}


def _sympify_value(expr: str, locals_map: SympyLocals) -> Any:
    return cast(Any, sp.sympify(expr, locals=locals_map))  # pyright: ignore[reportUnknownMemberType]


def _numeric_value(value: Any) -> Any:
    return cast(Any, sp.N(value))  # pyright: ignore[reportUnknownMemberType]


def _sin_degrees(value: Any) -> Any:
    return sp.sin(sp.pi * value / 180)


def _cos_degrees(value: Any) -> Any:
    return sp.cos(sp.pi * value / 180)


def _tan_degrees(value: Any) -> Any:
    return sp.tan(sp.pi * value / 180)


def _asin_degrees(value: Any) -> Any:
    result: Any = sp.asin(value)
    return result * 180 / sp.pi


def _acos_degrees(value: Any) -> Any:
    result: Any = sp.acos(value)
    return result * 180 / sp.pi


def _atan_degrees(value: Any) -> Any:
    result: Any = sp.atan(value)
    return result * 180 / sp.pi


def _log_base_10(value: Any, base: int = 10) -> Any:
    return sp.log(value, base)


def _sqrt_value(value: Any) -> Any:
    return cast(Any, sp.sqrt(value))  # pyright: ignore[reportUnknownMemberType]


def _to_radians(value: Any) -> Any:
    return value * sp.pi / 180


def _to_degrees(value: Any) -> Any:
    return value * 180 / sp.pi


SCIENTIFIC_FUNCTIONS: dict[str, Any] = {
    "sin": _sin_degrees,
    "cos": _cos_degrees,
    "tan": _tan_degrees,
    "asin": _asin_degrees,
    "acos": _acos_degrees,
    "atan": _atan_degrees,
    "sind": _sin_degrees,
    "cosd": _cos_degrees,
    "tand": _tan_degrees,
    "sinr": sp.sin,
    "cosr": sp.cos,
    "tanr": sp.tan,
    "sqrt": _sqrt_value,
    "ln": sp.log,
    "log": _log_base_10,
    "exp": sp.exp,
    "abs": sp.Abs,
    "factorial": sp.factorial,
    "rad": _to_radians,
    "deg": _to_degrees,
}


def get_sympy_locals() -> SympyLocals:
    return {
        **SCIENTIFIC_CONSTANTS,
        **SCIENTIFIC_FUNCTIONS,
        **variables,
    }


def set_last_result(value: Any) -> None:
    global last_result
    last_result = value


def get_last_result() -> Any:
    return last_result


def initialize_variables() -> None:
    global variables
    variables = load_saved_variables()


def normalize(text: str) -> str:
    text = correct_math_words(text)

    fixes = {
        "what si": "what is",
        "whats is": "what is",
        "whats": "what is",
        "what's": "what is",
        "dived": "divide",
        "divied": "divide",
        "divided": "divide",
        "multiplied": "multiply"
    }

    for wrong, right in fixes.items():
        text = re.sub(rf'\b{re.escape(wrong)}\b', right, text)

    return text


def normalize_scientific_expression(expr: Any) -> str:
    expr = str(expr).strip()
    expr = expr.replace("π", "pi")
    expr = expr.replace("^", "**")
    expr = re.sub(r'(\d)\s*!', r'\1!', expr)
    expr = re.sub(r'\bdegrees\b', "deg", expr)
    expr = re.sub(r'\bdegree\b', "deg", expr)
    expr = re.sub(r'\bradians\b', "rad", expr)
    expr = re.sub(r'\bradian\b', "rad", expr)

    # sin^2(x) -> sin(x)**2
    expr = re.sub(
        r'\b(sin|cos|tan|asin|acos|atan|log|ln|sqrt)\s*\*\*\s*(\d+)\s*\(([^()]*)\)',
        lambda match: f"{match.group(1)}({match.group(3)})**{match.group(2)}",
        expr
    )
    expr = re.sub(
        r'\b(sin|cos|tan|asin|acos|atan|log|ln|sqrt)\s*(\d+)\s*\(([^()]*)\)',
        lambda match: f"{match.group(1)}({match.group(3)})**{match.group(2)}",
        expr
    )

    expr = re.sub(r'(\d|\))\s*([a-zA-Z(])', r'\1*\2', expr)

    # n! -> factorial(n)
    while re.search(r'(\b\w+\b|\([^()]+\))!', expr):
        expr = re.sub(r'(\b\w+\b|\([^()]+\))!', r'factorial(\1)', expr)

    return expr


def safe_eval_expr(expr: Any) -> Any:
    normalized = normalize_scientific_expression(expr)
    result: Any = _sympify_value(normalized, get_sympy_locals())
    return _numeric_value(result)


def extract_expression(text: str) -> str:
    text = normalize(text)

    filler_phrases = [
        "what is",
        "what",
        "now",
        "that",
        "please",
        "can you",
        "calculate",
        "solve"
    ]

    for phrase in filler_phrases:
        text = text.replace(phrase, " ")

    text = " ".join(text.split())
    text = replace_operation_words(text)
    text = normalize_scientific_expression(text)

    return text


def apply_followup_operation(user_input: str) -> str | None:
    global last_result

    text = normalize(user_input)
    text = replace_operation_words(text)

    shortcut_match = re.fullmatch(r'([\+\-\*/])\s*(-?\d+(?:\.\d+)?)', text)
    if shortcut_match:
        if last_result is None:
            return get_bot_response("no_previous_result")

        op = shortcut_match.group(1)
        num = float(shortcut_match.group(2))

        if op == "+":
            last_result += num
        elif op == "-":
            last_result -= num
        elif op == "*":
            last_result *= num
        elif op == "/":
            if num == 0:
                return get_bot_response("divide_by_zero")
            last_result /= num

        return str(last_result)

    word_match = re.fullmatch(
        r'(add|plus|subtract|minus|multiply|times|divide)\s*(?:by)?\s*(-?\d+(?:\.\d+)?)',
        text
    )
    if word_match:
        if last_result is None:
            return get_bot_response("no_previous_result")

        op_word = word_match.group(1)
        num = float(word_match.group(2))

        if op_word in ["add", "plus"]:
            last_result += num
        elif op_word in ["subtract", "minus"]:
            last_result -= num
        elif op_word in ["multiply", "times"]:
            last_result *= num
        elif op_word == "divide":
            if num == 0:
                return get_bot_response("divide_by_zero")
            last_result /= num

        return str(last_result)

    return None


def calculator(expr: str) -> str:
    global last_result

    try:
        expr = expr.strip()

        if expr == "":
            return get_bot_response("no_math_found")

        if "=" in expr:
            var, val = expr.split("=", 1)
            var = var.strip()
            val = val.strip()

            if not var.isalpha():
                return get_bot_response("invalid_variable")

            result = safe_eval_expr(val)
            variables[var] = result
            save_variable_to_db(var, result)
            last_result = result
            return f"{var} = {result}"

        result = safe_eval_expr(expr)
        last_result = result
        return str(result)

    except NameError:
        return get_bot_response("undefined_variable")
    except ZeroDivisionError:
        return get_bot_response("divide_by_zero")
    except Exception:
        logger.exception("calculator failed")
        return get_bot_response("calc_error")
