import math
import re
from typing import Any, TypeAlias, cast

import sympy as sp

GRAPH_PREFIXES = ("graph ", "plot ")
GRAPH_COLORS = [
    "#61AFEF",
    "#98C379",
    "#E5C07B",
    "#E06C75",
    "#C678DD",
    "#56B6C2",
]
GraphFunction: TypeAlias = dict[str, Any]
GraphTask: TypeAlias = dict[str, Any]
GraphSeries: TypeAlias = list[dict[str, Any]]


def _sympify_expression(expression_text: str) -> Any:
    return cast(Any, sp.sympify(expression_text))  # pyright: ignore[reportUnknownMemberType]


def _numeric_value(value: Any) -> Any:
    return cast(Any, sp.N(value))  # pyright: ignore[reportUnknownMemberType]


def is_graph_request(text: str) -> bool:
    normalized = str(text).strip().lower()
    return any(normalized.startswith(prefix) for prefix in GRAPH_PREFIXES)


def _strip_graph_prefix(text: str) -> str:
    normalized = str(text).strip()
    lowered = normalized.lower()

    for prefix in GRAPH_PREFIXES:
        if lowered.startswith(prefix):
            return normalized[len(prefix):].strip()

    return normalized


def _split_functions(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*(?:,|;|\band\b)\s*", text) if part.strip()]


def _normalize_expression(part: str) -> str:
    cleaned = part.strip()

    if "=" in cleaned:
        left, right = cleaned.split("=", 1)
        left = left.strip()
        right = right.strip()

        if left.lower() == "y":
            cleaned = right
        else:
            # Turn equations like x + 2 = y into a single expression for SymPy.
            cleaned = f"({left}) - ({right})"

    cleaned = cleaned.replace("^", "**")
    # Add explicit multiplication so inputs like 2x work.
    cleaned = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", cleaned)
    cleaned = re.sub(r"([a-zA-Z])\(", r"\1*(", cleaned)
    cleaned = re.sub(r"\)\s*([a-zA-Z0-9])", r")*\1", cleaned)
    return cleaned


def parse_graph_request(text: str) -> GraphTask:
    payload = _strip_graph_prefix(text)
    if not payload:
        raise ValueError("Enter a function to graph, like: graph y = x^2")

    raw_parts = _split_functions(payload)
    if not raw_parts:
        raise ValueError("Enter at least one function to graph.")

    x_symbol = sp.Symbol("x")
    functions: list[GraphFunction] = []

    for index, raw_part in enumerate(raw_parts):
        expression_text = _normalize_expression(raw_part)
        expression = _sympify_expression(expression_text)
        free_symbols: set[Any] = cast(set[Any], expression.free_symbols)

        # Keep graphing simple by supporting x-based functions only.
        if x_symbol not in free_symbols and free_symbols:
            raise ValueError("Graphing currently supports functions written in terms of x.")

        functions.append({
            "label": raw_part,
            "expression": expression,
            "color": GRAPH_COLORS[index % len(GRAPH_COLORS)],
        })

    return {
        "functions": functions,
        "x_min": -10.0,
        "x_max": 10.0,
        "samples": 401,
    }


def build_graph_points(graph_task: GraphTask) -> GraphSeries:
    x_symbol = sp.Symbol("x")
    x_min = graph_task.get("x_min", -10.0)
    x_max = graph_task.get("x_max", 10.0)
    samples = graph_task.get("samples", 401)
    step = (x_max - x_min) / max(samples - 1, 1)
    x_values = [x_min + step * i for i in range(samples)]
    series: GraphSeries = []

    for function in graph_task["functions"]:
        y_values: list[float] = []

        for x_value in x_values:
            evaluated: Any = function["expression"].subs(x_symbol, x_value)
            numeric = _numeric_value(evaluated)

            # Use NaN for points that should not be drawn, like division by zero.
            if not numeric.is_real:
                y_values.append(float("nan"))
                continue

            y_float = float(numeric)
            if math.isfinite(y_float):
                y_values.append(y_float)
            else:
                y_values.append(float("nan"))

        series.append({
            "label": function["label"],
            "color": function["color"],
            "x": x_values,
            "y": y_values,
        })

    return series
