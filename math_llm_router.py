import re
from load_operations import replace_operation_words

NUMBER = r'-?\d+(?:\.\d+)?'


def normalize_math_words(text):
    text = text.lower().strip()

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


def convert_word_operators(text):
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


def route_math_request(user_input):
    text = normalize_math_words(user_input)

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

    # equations with x
    if "x" in text:
        cleaned = text
        for phrase in ["what is", "what", "solve"]:
            cleaned = cleaned.replace(phrase, "")
        cleaned = cleaned.strip()

        cleaned = convert_word_operators(cleaned)

        if "=" not in cleaned:
            cleaned = f"{cleaned} = 0"
        elif cleaned.endswith("="):
            cleaned = cleaned + " 0"

        cleaned = re.sub(r'(\d)x', r'\1*x', cleaned)

        return {
            "task_type": "equation",
            "expression": cleaned,
            "variable": "x"
        }

    # arithmetic
    cleaned = text
    for phrase in ["what is", "what", "calculate"]:
        cleaned = cleaned.replace(phrase, "")
    cleaned = cleaned.strip()
    cleaned = convert_word_operators(cleaned)

    if any(ch.isdigit() for ch in cleaned):
        return {
            "task_type": "arithmetic",
            "expression": cleaned
        }

    return None
