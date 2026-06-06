from contextlib import asynccontextmanager
from typing import Any, TypeAlias

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import database_utilities
import main as chatbot_main
from graphing import GraphSeries, GraphTask, build_graph_points, parse_graph_request
from load_operations import load_operations
from logger import logger
from math_logic import initialize_variables

JsonDict: TypeAlias = dict[str, Any]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: Any


class GraphRequest(BaseModel):
    query: str


class EquationSaveRequest(BaseModel):
    name: str
    equation: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Prepare shared data once when the API server starts.
        load_operations()
        initialize_variables()
        database_utilities.ensure_user_memory_table()
        database_utilities.ensure_saved_equations_table()
        logger.info("api_startup_complete")
    except Exception:
        logger.exception("api_startup_failed")
    yield


app = FastAPI(
    title="Math ChatBot API",
    version="1.0.0",
    description="Backend API for the Math ChatBot GUI, future web apps, mobile apps, and cloud chatbot deployments.",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    # Simple health endpoint for local checks or deployment monitoring.
    return {"status": "ok"}


@app.get("/startup-messages")
def get_startup_messages() -> dict[str, list[str]]:
    return {"messages": chatbot_main.get_startup_messages()}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> JsonDict:
    # Reuse the same chatbot logic the GUI and terminal mode already use.
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return {"response": chatbot_main.process_user_input(request.message)}


@app.post("/graph")
def graph_preview(request: GraphRequest) -> JsonDict:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        graph_task: GraphTask = parse_graph_request(request.query)
        series: GraphSeries = build_graph_points(graph_task)
        return {
            "graph": graph_task,
            "series": series,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/equations/save")
def save_equation(request: EquationSaveRequest) -> JsonDict:
    saved, error_message = database_utilities.save_equation_to_db(request.name, request.equation)
    if not saved:
        status_code = 409 if error_message and "already saved" in error_message.lower() else 500
        raise HTTPException(status_code=status_code, detail=error_message or "Could not save equation.")
    return {"saved": True, "name": request.name.strip().lower(), "equation": request.equation.strip()}


@app.get("/equations/{equation_name}")
def load_equation(equation_name: str) -> JsonDict:
    equation = database_utilities.load_saved_equation(equation_name)
    if equation is None:
        raise HTTPException(status_code=404, detail="Equation not found.")
    return {"name": equation_name.strip().lower(), "equation": equation}


@app.get("/equations")
def list_equations() -> JsonDict:
    equations = database_utilities.get_saved_equations()
    return {
        "equations": [
            {"name": name, "equation": equation}
            for name, equation in equations
        ]
    }
