from math_llm_router import route_math_request
from math_engine import solve_math_task


def solve_linear_equation_with_steps(user_input):
    task = route_math_request(user_input)

    if task is None:
        return None

    if task.get("task_type") != "equation":
        return None

    result = solve_math_task(task)

    if result and result.get("success"):
        return result["response"]

    return None
