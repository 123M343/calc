import re
from typing import Any, Optional, TypeAlias

from load_operations import replace_operation_words
from typo_utils import correct_math_words

Task: TypeAlias = dict[str, Any]

NUMBER = r'-?\d+(?:\.\d+)?'
UNIT = r'[a-zA-Z]+'
EQUATION_WORDS = [
    "systems of equations",
    "system of equations",
    "linear equations",
    "quadratic equations",
    "linear equation",
    "quadratic equation",
    "what is",
    "solve",
    "find",
    "what"
]


def normalize_math_words(text: str) -> str:
    text = correct_math_words(text)

    replacements = {
        "what si": "what is",
        "whats is": "what is",
        "whats": "what is",
        "what's": "what is",
        "dived": "divide",
        "divied": "divide",
        "divided": "divide",
        "multiplied": "multiply"
    }

    for wrong, right in replacements.items():
        text = re.sub(rf'\b{re.escape(wrong)}\b', right, text)

    return text


def convert_word_operators(text: str) -> str:
    text = text.replace(" divided by ", " / ")
    text = text.replace(" divide by ", " / ")
    text = text.replace(" divide ", " / ")
    text = text.replace(" over ", " / ")

    text = text.replace(" multiplied by ", " * ")
    text = text.replace(" multiply by ", " * ")
    text = text.replace(" multiply ", " * ")
    text = text.replace(" times ", " * ")

    text = text.replace(" plus ", " + ")
    text = text.replace(" add ", " + ")

    text = text.replace(" minus ", " - ")
    text = text.replace(" subtract ", " - ")

    text = text.replace("^", "**")
    text = replace_operation_words(text)
    return " ".join(text.split())


def strip_equation_words(text: str) -> str:
    cleaned = text
    for phrase in EQUATION_WORDS:
        cleaned = cleaned.replace(phrase, " ")
    return " ".join(cleaned.split())


def normalize_equation_expression(text: str) -> str:
    cleaned = strip_equation_words(text)
    cleaned = re.sub(r'\b(system|systems|equation|equations)\b', " ", cleaned)
    cleaned = cleaned.replace(":", " ")
    cleaned = re.sub(r'\band\b', " ; ", cleaned)
    cleaned = re.sub(r'[,\n]+', " ; ", cleaned)
    cleaned = convert_word_operators(cleaned)
    cleaned = re.sub(r'^\s*of\b', " ", cleaned)
    cleaned = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', cleaned)
    cleaned = re.sub(r'\b([a-zA-Z])\(', r'\1*(', cleaned)
    cleaned = re.sub(r'\)\s*([a-zA-Z0-9])', r')*\1', cleaned)
    cleaned = re.sub(r'\s*;\s*', "; ", cleaned)
    return " ".join(cleaned.split())


def split_equations(expression: str) -> list[str]:
    return [part.strip() for part in expression.split(";") if part.strip()]


def extract_variables(expression: str) -> list[str]:
    tokens = re.findall(r'\b[a-zA-Z]\b', expression)
    return sorted(set(tokens))


def is_plain_assignment(expression: str) -> bool:
    if ";" in expression:
        return False

    match = re.fullmatch(r'([a-zA-Z]+)\s*=\s*([^=]+)', expression)
    if not match:
        return False

    right_side = match.group(2)
    return re.search(r'\b[a-zA-Z]\b', right_side) is None


def build_equation_task(text: str) -> Optional[Task]:
    cleaned = normalize_equation_expression(text)
    if not cleaned:
        return None

    equations = split_equations(cleaned)

    if not equations:
        return None

    if len(equations) == 1 and "=" not in equations[0]:
        equations[0] = f"{equations[0]} = 0"
    else:
        equations = [
            equation + " 0" if equation.endswith("=") else equation
            for equation in equations
        ]

    normalized_expression = "; ".join(equations)
    variables = extract_variables(normalized_expression)

    if not variables:
        return None

    if is_plain_assignment(normalized_expression):
        return None

    task: Task = {
        "task_type": "equation",
        "expression": normalized_expression,
        "variables": variables
    }

    if len(variables) == 1:
        task["variable"] = variables[0]

    if len(equations) > 1:
        task["equations"] = equations

    return task


def route_math_request(user_input: str) -> Optional[Task]:
    text = normalize_math_words(user_input)

    # convert 255 to binary / hex / octal / decimal
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?convert\s+(-?\d+)\s+to\s+(binary|hex|hexadecimal|octal|decimal)',
        text
    )
    if match:
        return {
            "task_type": "programmer",
            "operation": "base_convert",
            "value": int(match.group(1)),
            "to_base": match.group(2)
        }

    # 1010 AND 1100 / 12 xor 5
    match = re.fullmatch(
        r'(?:what(?:\s+is)?\s+)?([01]+|\d+)\s+(and|or|xor)\s+([01]+|\d+)',
        text
    )
    if match:
        return {
            "task_type": "programmer",
            "operation": "bitwise_binary",
            "left": match.group(1),
            "operator": match.group(2),
            "right": match.group(3)
        }

    # not 1010
    match = re.fullmatch(r'(?:what(?:\s+is)?\s+)?not\s+([01]+|\d+)', text)
    if match:
        return {
            "task_type": "programmer",
            "operation": "bitwise_not",
            "value_text": match.group(1)
        }

    # 10 miles to km / 50 fahrenheit to celsius
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})\s*({UNIT})\s+to\s+({UNIT})\s*=?',
        text
    )
    if match:
        return {
            "task_type": "conversion",
            "operation": "convert_unit",
            "value": float(match.group(1)),
            "from_unit": match.group(2),
            "to_unit": match.group(3)
        }

    # 10ft + 10cm / 10kg - 500g / 10ft / 10cm
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})\s*({UNIT})\s*([+\-*/])\s*({NUMBER})\s*({UNIT})\s*=?',
        text
    )
    if match:
        return {
            "task_type": "conversion",
            "operation": "combine_units",
            "left_value": float(match.group(1)),
            "left_unit": match.group(2),
            "operator": match.group(3),
            "right_value": float(match.group(4)),
            "right_unit": match.group(5)
        }

    # 10ft * 3 / 10kg / 2
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})\s*({UNIT})\s*([*/])\s*({NUMBER})\s*=?',
        text
    )
    if match:
        return {
            "task_type": "conversion",
            "operation": "scale_unit",
            "value": float(match.group(1)),
            "unit": match.group(2),
            "operator": match.group(3),
            "scalar": float(match.group(4))
        }

    # 3 * 10ft
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})\s*\*\s*({NUMBER})\s*({UNIT})\s*=?',
        text
    )
    if match:
        return {
            "task_type": "conversion",
            "operation": "scale_unit",
            "value": float(match.group(2)),
            "unit": match.group(3),
            "operator": "*",
            "scalar": float(match.group(1))
        }

    # half of 8
    match = re.fullmatch(rf'(?:what(?:\s+is)?\s+)?half of ({NUMBER})', text)
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "half",
            "value": float(match.group(1))
        }

    # split 18 in half
    match = re.fullmatch(rf'(?:what(?:\s+is)?\s+)?split ({NUMBER}) in half', text)
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "half",
            "value": float(match.group(1))
        }

    # 18 split in half
    match = re.fullmatch(rf'(?:what(?:\s+is)?\s+)?({NUMBER}) split in half', text)
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "half",
            "value": float(match.group(1))
        }

    # one fourth of 20
    match = re.fullmatch(rf'(?:what(?:\s+is)?\s+)?one fourth of ({NUMBER})', text)
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "fraction_of",
            "numerator": 1,
            "denominator": 4,
            "value": float(match.group(1))
        }

    # one quarter of 20
    match = re.fullmatch(rf'(?:what(?:\s+is)?\s+)?one quarter of ({NUMBER})', text)
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "fraction_of",
            "numerator": 1,
            "denominator": 4,
            "value": float(match.group(1))
        }

    # 3/4 of 20
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?(\d+)\s*/\s*(\d+)\s+of\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "fraction_of",
            "numerator": int(match.group(1)),
            "denominator": int(match.group(2)),
            "value": float(match.group(3))
        }

    # 25 percent of 80
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER}) percent of ({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "percent_of",
            "percent": float(match.group(1)),
            "whole": float(match.group(2))
        }

    # 25% of 80
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})% of ({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "special_phrase",
            "operation": "percent_of",
            "percent": float(match.group(1)),
            "whole": float(match.group(2))
        }

    # add 3 to 3 -> 3 + 3
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?add\s+({NUMBER})\s+to\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "arithmetic",
            "expression": f"{match.group(2)} + {match.group(1)}"
        }

    # subtract 3 from 10 -> 10 - 3
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?subtract\s+({NUMBER})\s+from\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "arithmetic",
            "expression": f"{match.group(2)} - {match.group(1)}"
        }

    # multiply 4 by 3 -> 4 * 3
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?multiply\s+({NUMBER})\s+by\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "arithmetic",
            "expression": f"{match.group(1)} * {match.group(2)}"
        }

    # 4 multiplied by 3 -> 4 * 3
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})\s+multiplied by\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "arithmetic",
            "expression": f"{match.group(1)} * {match.group(2)}"
        }

    # divide 10 by 2 -> 10 / 2
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?divide\s+({NUMBER})\s+by\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "arithmetic",
            "expression": f"{match.group(1)} / {match.group(2)}"
        }

    # 10 divided by 2 -> 10 / 2
    match = re.fullmatch(
        rf'(?:what(?:\s+is)?\s+)?({NUMBER})\s+divided by\s+({NUMBER})',
        text
    )
    if match:
        return {
            "task_type": "arithmetic",
            "expression": f"{match.group(1)} / {match.group(2)}"
        }

    # follow-up with "that"
    match = re.fullmatch(rf'add\s+({NUMBER})\s+to\s+that', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "+",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'subtract\s+({NUMBER})\s+from\s+that', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "-",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'multiply\s+that\s+by\s+({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "*",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'divide\s+that\s+by\s+({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "/",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'([\+\-\*/])\s*({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": match.group(1),
            "value": float(match.group(2))
        }

    # short follow-ups like "plus 2" or "times 3"
    match = re.fullmatch(rf'(?:add|plus)\s+({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "+",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'(?:subtract|minus)\s+({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "-",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'(?:multiply|times)\s+(?:by\s+)?({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "*",
            "value": float(match.group(1))
        }

    match = re.fullmatch(rf'divide\s+(?:by\s+)?({NUMBER})', text)
    if match:
        return {
            "task_type": "followup",
            "operation": "/",
            "value": float(match.group(1))
        }

    equation_task = build_equation_task(text)
    if equation_task is not None:
        return equation_task

    # arithmetic
    cleaned = text
    for phrase in ["what is", "what", "calculate"]:
        cleaned = cleaned.replace(phrase, "")
    cleaned = cleaned.strip()
    cleaned = convert_word_operators(cleaned)

    if "=" not in cleaned and any(ch.isdigit() for ch in cleaned):
        return {
            "task_type": "arithmetic",
            "expression": cleaned
        }

    return None
