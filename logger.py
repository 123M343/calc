import logging
from pathlib import Path

LOG_FILE = Path(__file__).with_name("app.log")

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("math_chatbot")


def log_command(command_text: str) -> None:
    logger.info("command_received | %s", command_text)


def log_result(command_text: str, duration_ms: float, outcome: str) -> None:
    logger.info(
        "command_completed | command=%s | duration_ms=%.2f | outcome=%s",
        command_text,
        duration_ms,
        outcome,
    )


def log_crash(context: str) -> None:
    logger.exception("crash_detected | %s", context)
