import re
from typing import Any, Optional, TypeAlias, cast

import sympy as sp
from math_logic import get_sympy_locals, normalize_scientific_expression

Task: TypeAlias = dict[str, Any]
MathResult: TypeAlias = dict[str, Any]

LENGTH_TO_METERS = {
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
    "yd": 0.9144,
    "yard": 0.9144,
    "yards": 0.9144,
    "mi": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,
}

WEIGHT_TO_KILOGRAMS = {
    "mg": 0.000001,
    "milligram": 0.000001,
    "milligrams": 0.000001,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "kg": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "oz": 0.028349523125,
    "ounce": 0.028349523125,
    "ounces": 0.028349523125,
    "ton": 907.18474,
    "tons": 907.18474,
}

TEMPERATURE_UNITS = {
    "c": "celsius",
    "celsius": "celsius",
    "f": "fahrenheit",
    "fahrenheit": "fahrenheit",
    "k": "kelvin",
    "kelvin": "kelvin",
}


def _sympify_expression(expression: str) -> Any:
    return cast(Any, sp.sympify(expression, locals=get_sympy_locals()))  # pyright: ignore[reportUnknownMemberType]


def _numeric_value(value: Any) -> Any:
    return cast(Any, sp.N(value))  # pyright: ignore[reportUnknownMemberType]


def _simplify_value(value: Any) -> Any:
    return cast(Any, sp.simplify(value))  # pyright: ignore[reportUnknownMemberType]


def _expand_value(value: Any) -> Any:
    return cast(Any, sp.expand(value))  # pyright: ignore[reportUnknownMemberType]


def _solve_value(*args: Any, **kwargs: Any) -> Any:
    return cast(Any, sp.solve(*args, **kwargs))  # pyright: ignore[reportUnknownMemberType]


def format_result(value: Any) -> str:
    try:
        simplified: Any = _simplify_value(value)

        if simplified.is_number:
            numeric: Any = _numeric_value(simplified)

            if numeric.is_real:
                as_float = float(numeric)

                if as_float.is_integer():
                    return str(int(as_float))

                return str(round(as_float, 10)).rstrip("0").rstrip(".")

        return str(simplified)

    except Exception:
        return str(value)


def format_solution_set(variable_name: str, solutions: list[Any]) -> str:
    if not solutions:
        return f"No solution for {variable_name}."

    if len(solutions) == 1:
        return f"{variable_name} = {format_result(solutions[0])}"

    joined = " and ".join(
        f"{variable_name} = {format_result(solution)}"
        for solution in solutions
    )
    return joined


def parse_equation_text(expression: str) -> tuple[Any, Any]:
    if "=" in expression:
        left_text, right_text = expression.split("=", 1)
    else:
        left_text = expression
        right_text = "0"

    left_expr: Any = _sympify_expression(normalize_scientific_expression(left_text))
    right_expr: Any = _sympify_expression(normalize_scientific_expression(right_text))
    return left_expr, right_expr


def solve_system(task: Task) -> MathResult:
    equations_text = task.get("equations", [])
    variable_names = task.get("variables", [])

    try:
        symbols = [sp.Symbol(name) for name in variable_names]
        equations: list[Any] = []

        for expression in equations_text:
            left_expr, right_expr = parse_equation_text(expression)
            equations.append(sp.Eq(left_expr, right_expr))

        solutions: list[dict[Any, Any]] = _solve_value(equations, symbols, dict=True)

        if not solutions:
            return {
                "success": True,
                "response": (
                    "You’re solving a system of equations:\n"
                    f"{chr(10).join(equations_text)}\n\n"
                    "Final Answer:\nNo solution found."
                )
            }

        first_solution = solutions[0]
        ordered_answers = [
            f"{name} = {format_result(first_solution[sp.Symbol(name)])}"
            for name in variable_names
            if sp.Symbol(name) in first_solution
        ]

        return {
            "success": True,
            "response": (
                "You’re solving a system of equations:\n"
                f"{chr(10).join(equations_text)}\n\n"
                "Step 1: Solve the equations together\n"
                "Step 2: Read off each variable\n"
                f"{chr(10).join(ordered_answers)}\n\n"
                "Final Answer:\n"
                f"{', '.join(ordered_answers)}"
            )
        }

    except Exception:
        return {
            "success": False,
            "response": "I could not solve that system of equations."
        }


def solve_math_task(task: Task) -> Optional[MathResult]:
    task_type = task.get("task_type")

    if task_type == "arithmetic":
        return solve_arithmetic(task)

    if task_type == "equation":
        return solve_equation(task)

    if task_type == "conversion":
        return solve_conversion(task)

    if task_type == "programmer":
        return solve_programmer_task(task)

    if task_type == "special_phrase":
        return solve_special_phrase(task)

    return None


def solve_arithmetic(task: Task) -> MathResult:
    expression = task.get("expression", "")

    try:
        normalized = normalize_scientific_expression(expression)
        result: Any = _sympify_expression(normalized).evalf()
        result_float = float(result)
        return {
            "success": True,
            "value": result_float,
            "response": f"Final Answer:\n{format_result(result)}"
        }
    except Exception:
        return {
            "success": False,
            "response": "I could not solve that arithmetic expression."
        }


def solve_special_phrase(task: Task) -> MathResult:
    operation = task.get("operation")
    value = task.get("value")
    percent = task.get("percent")
    whole = task.get("whole")
    numerator = task.get("numerator")
    denominator = task.get("denominator")

    try:
        if operation == "half":
            if value is None:
                return {
                    "success": False,
                    "response": "I could not solve that special phrase."
                }
            result = value / 2
            return {
                "success": True,
                "value": result,
                "response": (
                    "You’re solving a special phrase:\n"
                    f"Half of {format_result(value)}\n\n"
                    "Step 1: Half means divide by 2\n"
                    f"Step 2: {format_result(value)} ÷ 2 = {format_result(result)}\n\n"
                    f"Final Answer:\n{format_result(result)}"
                )
            }

        if operation == "fraction_of":
            if value is None or numerator is None or denominator in (None, 0):
                return {
                    "success": False,
                    "response": "I could not solve that special phrase."
                }
            fraction_value = numerator / denominator
            result = fraction_value * value
            return {
                "success": True,
                "value": result,
                "response": (
                    "You’re solving a fraction problem:\n"
                    f"{numerator}/{denominator} of {format_result(value)}\n\n"
                    "Step 1: Convert the phrase into multiplication\n"
                    f"({numerator}/{denominator}) × {format_result(value)}\n"
                    "Step 2: Compute the fraction\n"
                    f"{numerator}/{denominator} = {format_result(fraction_value)}\n"
                    "Step 3: Multiply\n"
                    f"{format_result(fraction_value)} × {format_result(value)} = {format_result(result)}\n\n"
                    f"Final Answer:\n{format_result(result)}"
                )
            }

        if operation == "percent_of":
            if percent is None or whole is None:
                return {
                    "success": False,
                    "response": "I could not solve that special phrase."
                }
            decimal_percent = percent / 100
            result = decimal_percent * whole
            return {
                "success": True,
                "value": result,
                "response": (
                    "You’re solving a percent problem:\n"
                    f"{format_result(percent)}% of {format_result(whole)}\n\n"
                    f"Step 1: Convert {format_result(percent)}% to decimal\n"
                    f"{format_result(percent)}% = {format_result(decimal_percent)}\n"
                    f"Step 2: Multiply by {format_result(whole)}\n"
                    f"{format_result(decimal_percent)} × {format_result(whole)} = {format_result(result)}\n\n"
                    f"Final Answer:\n{format_result(result)}"
                )
            }

        return {
            "success": False,
            "response": "I do not recognize that special phrase yet."
        }

    except Exception:
        return {
            "success": False,
            "response": "I could not solve that special phrase."
        }


def normalize_length_unit(unit: Any) -> str:
    return str(unit).lower().strip()


def normalize_weight_unit(unit: Any) -> str:
    return str(unit).lower().strip()


def normalize_temperature_unit(unit: Any) -> Optional[str]:
    return TEMPERATURE_UNITS.get(str(unit).lower().strip())


def get_unit_dimension(unit: Any) -> Optional[str]:
    normalized_unit = str(unit).lower().strip()
    if normalized_unit in LENGTH_TO_METERS:
        return "length"
    if normalized_unit in WEIGHT_TO_KILOGRAMS:
        return "weight"
    if normalize_temperature_unit(normalized_unit):
        return "temperature"
    return None


def convert_dimension_value(value: float, from_unit: str, to_unit: str) -> float:
    normalized_from = str(from_unit).lower().strip()
    normalized_to = str(to_unit).lower().strip()

    if normalized_from in LENGTH_TO_METERS and normalized_to in LENGTH_TO_METERS:
        base_value = value * LENGTH_TO_METERS[normalized_from]
        return base_value / LENGTH_TO_METERS[normalized_to]

    if normalized_from in WEIGHT_TO_KILOGRAMS and normalized_to in WEIGHT_TO_KILOGRAMS:
        base_value = value * WEIGHT_TO_KILOGRAMS[normalized_from]
        return base_value / WEIGHT_TO_KILOGRAMS[normalized_to]

    normalized_from_temp = normalize_temperature_unit(normalized_from)
    normalized_to_temp = normalize_temperature_unit(normalized_to)
    if normalized_from_temp and normalized_to_temp:
        return convert_temperature(value, normalized_from_temp, normalized_to_temp)

    raise ValueError("Unsupported unit conversion")


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit == to_unit:
        return value

    if from_unit == "fahrenheit":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "kelvin":
        celsius = value - 273.15
    else:
        celsius = value

    if to_unit == "fahrenheit":
        return celsius * 9 / 5 + 32
    if to_unit == "kelvin":
        return celsius + 273.15
    return celsius


def solve_conversion(task: Task) -> MathResult:
    operation = task.get("operation")

    try:
        if operation == "convert_unit":
            value = task.get("value")
            from_unit = str(task.get("from_unit", "")).lower().strip()
            to_unit = str(task.get("to_unit", "")).lower().strip()
            if value is None:
                return {
                    "success": False,
                    "response": "I could not solve that unit conversion."
                }
            if get_unit_dimension(from_unit) != get_unit_dimension(to_unit):
                return {
                    "success": False,
                    "response": "Those units are not compatible."
                }

            result = convert_dimension_value(value, from_unit, to_unit)
            return {
                "success": True,
                "value": result,
                "unit": to_unit,
                "dimension": get_unit_dimension(to_unit),
                "response": (
                    "You’re converting units:\n"
                    f"{format_result(value)} {from_unit} to {to_unit}\n\n"
                    "Final Answer:\n"
                    f"{format_result(result)} {to_unit}"
                )
            }

        if operation == "combine_units":
            left_value = task.get("left_value")
            right_value = task.get("right_value")
            left_unit = str(task.get("left_unit")).lower().strip()
            right_unit = str(task.get("right_unit")).lower().strip()
            operator = task.get("operator")
            left_dimension = get_unit_dimension(left_unit)
            right_dimension = get_unit_dimension(right_unit)

            if left_dimension is None or right_dimension is None:
                return {
                    "success": False,
                    "response": "I do not recognize those units yet."
                }
            if left_value is None or right_value is None:
                return {
                    "success": False,
                    "response": "I could not solve that unit conversion."
                }

            if left_dimension != right_dimension:
                return {
                    "success": False,
                    "response": "Those units are not compatible."
                }

            right_in_left_unit = convert_dimension_value(right_value, right_unit, left_unit)

            if operator in ["+", "-"]:
                result = left_value + right_in_left_unit if operator == "+" else left_value - right_in_left_unit
                return {
                    "success": True,
                    "value": result,
                    "unit": left_unit,
                    "dimension": left_dimension,
                    "response": (
                        "You’re combining units:\n"
                        f"{format_result(left_value)} {left_unit} {operator} {format_result(right_value)} {right_unit}\n\n"
                        f"Step 1: Convert {format_result(right_value)} {right_unit} to {left_unit}\n"
                        f"{format_result(right_value)} {right_unit} = {format_result(right_in_left_unit)} {left_unit}\n"
                        "Step 2: Compute the result\n"
                        f"{format_result(result)} {left_unit}\n\n"
                        "Final Answer:\n"
                        f"{format_result(result)} {left_unit}"
                    )
                }

            if operator == "/":
                if right_in_left_unit == 0:
                    return {
                        "success": False,
                        "response": "You cannot divide by zero."
                    }
                result = left_value / right_in_left_unit
                return {
                    "success": True,
                    "value": result,
                    "response": (
                        "You’re comparing compatible units:\n"
                        f"{format_result(left_value)} {left_unit} / {format_result(right_value)} {right_unit}\n\n"
                        f"Step 1: Convert {format_result(right_value)} {right_unit} to {left_unit}\n"
                        f"{format_result(right_in_left_unit)} {left_unit}\n"
                        "Step 2: Divide\n"
                        f"{format_result(result)}\n\n"
                        "Final Answer:\n"
                        f"{format_result(result)}"
                    )
                }

            return {
                "success": False,
                "response": "Multiplying two unit values is not supported yet. Try multiplying a unit by a number instead."
            }

        if operation == "scale_unit":
            value = task.get("value")
            unit = str(task.get("unit")).lower().strip()
            operator = task.get("operator")
            scalar = task.get("scalar")

            if get_unit_dimension(unit) is None:
                return {
                    "success": False,
                    "response": "I do not recognize that unit yet."
                }
            if value is None or scalar is None:
                return {
                    "success": False,
                    "response": "I could not solve that unit conversion."
                }

            if operator == "/":
                if scalar == 0:
                    return {
                        "success": False,
                        "response": "You cannot divide by zero."
                    }
                result = value / scalar
            else:
                result = value * scalar

            return {
                "success": True,
                "value": result,
                "unit": unit,
                "dimension": get_unit_dimension(unit),
                "response": (
                    "You’re scaling a unit value:\n"
                    f"{format_result(value)} {unit} {operator} {format_result(scalar)}\n\n"
                    "Final Answer:\n"
                    f"{format_result(result)} {unit}"
                )
            }

        return {
            "success": False,
            "response": "I could not solve that unit conversion."
        }

    except Exception:
        return {
            "success": False,
            "response": "I could not solve that unit conversion."
        }


def normalize_base_name(base_name: Any) -> Optional[str]:
    mapping = {
        "binary": "binary",
        "hex": "hexadecimal",
        "hexadecimal": "hexadecimal",
        "octal": "octal",
        "decimal": "decimal",
    }
    return mapping.get(str(base_name).lower().strip())


def detect_programmer_base(value_text: Any) -> int:
    stripped = str(value_text).strip()
    if re.fullmatch(r'[01]+', stripped):
        return 2
    return 10


def format_in_base(value: int, base_name: str) -> str:
    if base_name == "binary":
        return bin(value)[2:]
    if base_name == "hexadecimal":
        return hex(value)[2:].upper()
    if base_name == "octal":
        return oct(value)[2:]
    return str(value)


def solve_programmer_task(task: Task) -> MathResult:
    operation = task.get("operation")

    try:
        if operation == "base_convert":
            raw_value = task.get("value")
            to_base = normalize_base_name(task.get("to_base"))
            if raw_value is None or to_base is None:
                return {
                    "success": False,
                    "response": "I could not solve that programmer-mode request."
                }
            value = int(raw_value)
            converted = format_in_base(value, to_base)
            return {
                "success": True,
                "response": (
                    "You’re converting number formats:\n"
                    f"{value} to {to_base}\n\n"
                    "Final Answer:\n"
                    f"{converted}"
                )
            }

        if operation == "bitwise_binary":
            left_text = task.get("left")
            right_text = task.get("right")
            if left_text is None or right_text is None:
                return {
                    "success": False,
                    "response": "I could not solve that programmer-mode request."
                }
            operator = str(task.get("operator")).lower().strip()
            left_base = detect_programmer_base(left_text)
            right_base = detect_programmer_base(right_text)
            result_base = 2 if left_base == right_base == 2 else 10
            left_value = int(left_text, left_base)
            right_value = int(right_text, right_base)

            if operator == "and":
                result_value = left_value & right_value
            elif operator == "or":
                result_value = left_value | right_value
            else:
                result_value = left_value ^ right_value

            result_text = format_in_base(result_value, "binary" if result_base == 2 else "decimal")
            return {
                "success": True,
                "response": (
                    "You’re doing a bitwise operation:\n"
                    f"{left_text} {operator.upper()} {right_text}\n\n"
                    "Final Answer:\n"
                    f"{result_text}"
                    + (f" (decimal {result_value})" if result_base == 2 else "")
                )
            }

        if operation == "bitwise_not":
            value_text = task.get("value_text")
            if value_text is None:
                return {
                    "success": False,
                    "response": "I could not solve that programmer-mode request."
                }
            base = detect_programmer_base(value_text)
            value = int(value_text, base)
            bit_length = max(len(str(value_text)), 1) if base == 2 else max(value.bit_length(), 1)
            mask = (1 << bit_length) - 1
            result_value = (~value) & mask
            result_text = format_in_base(result_value, "binary" if base == 2 else "decimal")
            return {
                "success": True,
                "response": (
                    "You’re doing a bitwise NOT:\n"
                    f"NOT {value_text}\n\n"
                    "Final Answer:\n"
                    f"{result_text}"
                    + (f" (decimal {result_value})" if base == 2 else "")
                )
            }

        return {
            "success": False,
            "response": "I could not solve that programmer-mode request."
        }

    except Exception:
        return {
            "success": False,
            "response": "I could not solve that programmer-mode request."
        }


def solve_equation(task: Task) -> MathResult:
    expression = task.get("expression", "")
    variable_name = task.get("variable")
    variable_names = task.get("variables", [])

    if len(task.get("equations", [])) > 1 or len(variable_names) > 1:
        return solve_system(task)

    try:
        if not variable_name:
            if not variable_names:
                return {
                    "success": False,
                    "response": "I could not solve that equation."
                }
            variable_name = variable_names[0]

        var = sp.Symbol(variable_name)
        left_expr, right_expr = parse_equation_text(expression)

        eq = sp.Eq(left_expr, right_expr)
        combined: Any = _expand_value(left_expr - right_expr)
        simplified: Any = _simplify_value(combined)

        if simplified == 0:
            return {
                "success": True,
                "response": (
                    "You’re checking an equation identity:\n"
                    f"{expression}\n\n"
                    "Step 1: Move everything to one side\n"
                    f"{format_result(combined)} = 0\n"
                    "Step 2: Simplify\n"
                    "0 = 0\n\n"
                    "Final Answer:\nThis equation is true for all valid values of the variable."
                )
            }

        try:
            degree = sp.Poly(combined, var).degree()
        except Exception:
            degree = None

        if degree == 1:
            solutions: list[Any] = _solve_value(eq, var)
            solution = solutions[0]
            poly = sp.Poly(combined, var)
            coefficients = poly.all_coeffs()
            if len(coefficients) == 2:
                a, b = coefficients
                isolate_step: Any = _expand_value(-b)
                divided_step: Any = _simplify_value((-b) / a)
                if a != 1 and b != 0:
                    return {
                        "success": True,
                        "response": (
                            "You’re solving a linear equation:\n"
                            f"{expression}\n\n"
                            "Step 1: Move the constant term to the other side\n"
                            f"{format_result(a)}*{variable_name} = {format_result(isolate_step)}\n"
                            f"Step 2: Divide both sides by {format_result(a)}\n"
                            f"{variable_name} = {format_result(divided_step)}\n\n"
                            "Final Answer:\n"
                            f"{variable_name} = {format_result(solution)}"
                        )
                    }

            return {
                "success": True,
                "response": (
                    "You’re solving a linear equation:\n"
                    f"{expression}\n\n"
                    "Step 1: Move everything to one side\n"
                    f"{_expand_value(combined)} = 0\n"
                    f"Step 2: Solve for {variable_name}\n"
                    f"{variable_name} = {format_result(solution)}\n\n"
                    "Final Answer:\n"
                    f"{variable_name} = {format_result(solution)}"
                )
            }

        if degree == 2:
            factored = sp.factor(combined)
            solutions: list[Any] = _solve_value(eq, var)

            if factored != combined:
                return {
                    "success": True,
                    "response": (
                        "You’re solving a quadratic equation:\n"
                        f"{expression}\n\n"
                        "Step 1: Factor\n"
                        f"{_expand_value(combined)} = {factored}\n"
                        "Step 2: Set each factor equal to 0\n"
                        "Step 3: Solve\n"
                        f"{variable_name} = {format_result(solutions[0])}\n"
                        f"{variable_name} = {format_result(solutions[1])}\n\n"
                        "Final Answer:\n"
                        f"{variable_name} = {format_result(solutions[0])} and {variable_name} = {format_result(solutions[1])}"
                    )
                }

            poly = sp.Poly(combined, var)
            a, b, c = poly.all_coeffs()
            disc: Any = _expand_value(b**2 - 4*a*c)

            return {
                "success": True,
                "response": (
                    "You’re solving a quadratic equation:\n"
                    f"{expression}\n\n"
                    "Step 1: Identify a, b, and c\n"
                    f"a = {format_result(a)}, b = {format_result(b)}, c = {format_result(c)}\n"
                    "Step 2: Use the quadratic formula\n"
                    f"{variable_name} = (-b ± √(b² - 4ac)) / (2a)\n"
                    f"Discriminant = {format_result(disc)}\n"
                    "Step 3: Solve\n"
                    f"{variable_name} = {format_result(solutions[0])}\n"
                    f"{variable_name} = {format_result(solutions[1])}\n\n"
                    "Final Answer:\n"
                    f"{variable_name} = {format_result(solutions[0])} and {variable_name} = {format_result(solutions[1])}"
                )
            }

        solutions: list[Any] = _solve_value(eq, var)

        return {
            "success": True,
            "response": (
                "I solved the equation.\n\n"
                "Final Answer:\n"
                f"{format_solution_set(variable_name, solutions)}"
            )
        }

    except Exception:
        return {
            "success": False,
            "response": "I could not solve that equation."
        }
