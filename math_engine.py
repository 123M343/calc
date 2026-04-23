import sympy as sp


def format_result(value):
    try:
        simplified = sp.simplify(value)

        if simplified.is_number:
            numeric = sp.N(simplified)

            if numeric.is_real:
                as_float = float(numeric)

                if as_float.is_integer():
                    return str(int(as_float))

                return str(round(as_float, 10)).rstrip("0").rstrip(".")

        return str(simplified)

    except Exception:
        return str(value)


def solve_math_task(task):
    task_type = task.get("task_type")

    if task_type == "arithmetic":
        return solve_arithmetic(task)

    if task_type == "equation":
        return solve_equation(task)

    if task_type == "special_phrase":
        return solve_special_phrase(task)

    return None


def solve_arithmetic(task):
    expression = task.get("expression", "")

    try:
        result = sp.sympify(expression).evalf()
        return {
            "success": True,
            "value": float(result),
            "response": f"Final Answer:\n{format_result(result)}"
        }
    except Exception:
        return {
            "success": False,
            "response": "I could not solve that arithmetic expression."
        }


def solve_special_phrase(task):
    operation = task.get("operation")
    value = task.get("value")
    percent = task.get("percent")
    whole = task.get("whole")
    numerator = task.get("numerator")
    denominator = task.get("denominator")

    try:
        if operation == "half":
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


def solve_equation(task):
    expression = task.get("expression", "")
    variable_name = task.get("variable", "x")

    try:
        var = sp.Symbol(variable_name)

        if "=" in expression:
            left_text, right_text = expression.split("=", 1)
        else:
            left_text = expression
            right_text = "0"

        left_expr = sp.sympify(left_text)
        right_expr = sp.sympify(right_text)

        eq = sp.Eq(left_expr, right_expr)
        combined = sp.expand(left_expr - right_expr)

        degree = sp.Poly(combined, var).degree()

        if degree == 1:
            solutions = sp.solve(eq, var)
            solution = solutions[0]

            return {
                "success": True,
                "response": (
                    "You’re solving a linear equation:\n"
                    f"{expression}\n\n"
                    "Step 1: Move everything to one side\n"
                    f"{sp.expand(combined)} = 0\n"
                    "Step 2: Solve for x\n"
                    f"x = {format_result(solution)}\n\n"
                    "Final Answer:\n"
                    f"x = {format_result(solution)}"
                )
            }

        if degree == 2:
            factored = sp.factor(combined)
            solutions = sp.solve(eq, var)

            if factored != combined:
                return {
                    "success": True,
                    "response": (
                        "You’re solving a quadratic equation:\n"
                        f"{expression}\n\n"
                        "Step 1: Factor\n"
                        f"{sp.expand(combined)} = {factored}\n"
                        "Step 2: Set each factor equal to 0\n"
                        "Step 3: Solve\n"
                        f"x = {format_result(solutions[0])}\n"
                        f"x = {format_result(solutions[1])}\n\n"
                        "Final Answer:\n"
                        f"x = {format_result(solutions[0])} and x = {format_result(solutions[1])}"
                    )
                }

            poly = sp.Poly(combined, var)
            a, b, c = poly.all_coeffs()
            disc = sp.expand(b**2 - 4*a*c)

            return {
                "success": True,
                "response": (
                    "You’re solving a quadratic equation:\n"
                    f"{expression}\n\n"
                    "Step 1: Identify a, b, and c\n"
                    f"a = {format_result(a)}, b = {format_result(b)}, c = {format_result(c)}\n"
                    "Step 2: Use the quadratic formula\n"
                    "x = (-b ± √(b² - 4ac)) / (2a)\n"
                    f"Discriminant = {format_result(disc)}\n"
                    "Step 3: Solve\n"
                    f"x = {format_result(solutions[0])}\n"
                    f"x = {format_result(solutions[1])}\n\n"
                    "Final Answer:\n"
                    f"x = {format_result(solutions[0])} and x = {format_result(solutions[1])}"
                )
            }

        solutions = sp.solve(eq, var)

        return {
            "success": True,
            "response": (
                "I solved the equation.\n\n"
                "Final Answer:\n"
                f"{[format_result(s) for s in solutions]}"
            )
        }

    except Exception:
        return {
            "success": False,
            "response": "I could not solve that equation."
        }
