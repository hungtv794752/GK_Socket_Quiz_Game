"""
protocol_message.py
-------------------
Shared protocol definitions for Quiz Game
Used by BOTH server and client
"""

from typing import Dict, List, Optional


# ================== MESSAGE TYPES ==================

# Server → Client
WELCOME = "welcome"
QUESTION = "question"
ANSWER_ACK = "answer_ack"
ROUND_RESULT = "round_result"
GAME_OVER = "game_over"
ERROR = "error"

# Client → Server
ANSWER = "answer"
START = "start"


# ================== BUILDERS ==================

def welcome(player: str) -> Dict:
    return {
        "type": WELCOME,
        "player": player,
    }

def start():
    return {
        "type": START
    }

def question(
    qid: str,
    text: str,
    choices: List[str],
    time_limit_sec: int,
    server_time: float,
) -> Dict:
    return {
        "type": QUESTION,
        "qid": qid,
        "question": text,
        "choices": choices,
        "time_limit_sec": time_limit_sec,
        "server_time": server_time,
    }


def answer(qid: str, answer: str) -> Dict:
    return {
        "type": ANSWER,
        "qid": qid,
        "answer": answer,
    }


def answer_ack(ok: bool, elapsed: Optional[float] = None, reason: Optional[str] = None) -> Dict:
    msg = {
        "type": ANSWER_ACK,
        "ok": ok,
    }
    if elapsed is not None:
        msg["elapsed"] = elapsed
    if reason:
        msg["reason"] = reason
    return msg


def round_result(
    qid: str,
    correct_answer: str,
    winner: Optional[str],
    details: List[Dict],
    leaderboard: List[Dict],
) -> Dict:
    return {
        "type": ROUND_RESULT,
        "qid": qid,
        "correct_answer": correct_answer,
        "winner": winner,
        "details": details,
        "leaderboard": leaderboard,
    }


def game_over() -> Dict:
    return {
        "type": GAME_OVER
    }


def error(reason: str) -> Dict:
    return {
        "type": ERROR,
        "reason": reason,
    }


# ================== VALIDATION ==================

def validate(msg: Dict) -> None:
    """
    Raise ValueError if protocol is invalid
    """
    if "type" not in msg:
        raise ValueError("Missing 'type' field")

    t = msg["type"]

    if t == QUESTION:
        _require(msg, "qid", "question", "choices", "time_limit_sec", "server_time")

    elif t == ANSWER:
        _require(msg, "qid", "answer")

    elif t == ANSWER_ACK:
        _require(msg, "ok")

    elif t == ROUND_RESULT:
        _require(msg, "qid", "correct_answer", "leaderboard")

    elif t == ERROR:
        _require(msg, "reason")

    elif t in (WELCOME, GAME_OVER, START):
        pass
    
    else:
        raise ValueError(f"Unknown message type: {t}")


def _require(msg: Dict, *fields: str) -> None:
    for f in fields:
        if f not in msg:
            raise ValueError(f"Missing field '{f}'")
