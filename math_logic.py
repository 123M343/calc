import ast
import operator
import re
from bot_response import get_bot_response
from database_utilities import load_saved_variables, save_variable_to_db
from load_operations import replace_operation_words
from logger import logger

variables = {}
last_result = None

BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow
}

UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg
}


def set_last_result(value):
    global last_result
    last_result = value


def get_last_result():
    return last_result


def initialize_variables():
    global variables
    variables = load_saved_variables()


def normalize(text):
    text = text.lower().strip()

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


def safe_eval_expr(expr):
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Invalid constant")

        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise NameError(node.id)

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in BIN_OPS:
                raise ValueError("Unsupported operator")
            return BIN_OPS[op_type](_eval(node.left), _eval(node.right))

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in UNARY_OPS:
                raise ValueError("Unsupported unary operator")
            return UNARY_OPS[op_type](_eval(node.operand))

        raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree)


def extract_expression(text):
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
    text = text.replace("^", "**")

    return text


def apply_followup_operation(user_input):
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

        return last_result

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

        return last_result

    return None


def calculator(expr):
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
        return result

    except NameError:
        return get_bot_response("undefined_variable")
    except ZeroDivisionError:
        return get_bot_response("divide_by_zero")
    except Exception:
        logger.exception("calculator failed")
        return get_bot_response("calc_error")
