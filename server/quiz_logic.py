# quiz_logic.py
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Question:
    qid: str
    text: str
    choices: List[str]
    answer: str


class QuizGame:
    def __init__(self, questions_path: str = "server/questions.json"):
        self.round_players: set[str] = set()
        self.questions_path = questions_path

        # Config (loaded from JSON)
        self.title = "Quiz"
        self.time_limit_sec = 10
        self.base_score = 100
        self.fast_bonus_max = 50

        # Question bank
        self.questions: List[Question] = []
        self.question_map: Dict[str, Question] = {}

        # Game state
        self.q_index = 0
        self.round_active = False
        self.round_qid: Optional[str] = None
        self.round_start = 0.0
        self.running = False

        # answers[qid][player] = (answer, elapsed)
        self.answers: Dict[str, Dict[str, Tuple[str, float]]] = {}

        # scoreboard[player] = stats
        self.scoreboard: Dict[str, Dict[str, int]] = {}

        self.load_questions()

    # ---------- loading ----------

    def load_questions(self) -> None:
        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.title = data.get("title", self.title)
        self.time_limit_sec = int(data.get("time_limit_sec", self.time_limit_sec))
        self.base_score = int(data.get("base_score", self.base_score))
        self.fast_bonus_max = int(data.get("fast_bonus_max", self.fast_bonus_max))

        self.questions.clear()
        self.question_map.clear()

        for item in data["questions"]:
            q = Question(
                qid=item["id"],
                text=item["question"],
                choices=item["choices"],
                answer=item["answer"],
            )
            self.questions.append(q)
            self.question_map[q.qid] = q

        self.q_index = 0

    # ---------- game flow ----------

    def has_next_question(self) -> bool:
        return self.q_index < len(self.questions)

    def start_round(self) -> Dict:
        if not self.has_next_question():
            self.running = False
            return {"type": "game_over"}

        q = self.questions[self.q_index]
        self.q_index += 1

        self.round_active = True
        self.round_qid = q.qid
        self.round_start = time.time()
        self.running = True

        self.answers[q.qid] = {}

        return {
            "type": "question",
            "qid": q.qid,
            "question": q.text,
            "choices": q.choices,
            "time_limit_sec": self.time_limit_sec,
            "server_time": self.round_start,
        }

    def submit_answer(self, player: str, qid: str, answer: str) -> Dict:
        if not self.round_active or qid != self.round_qid:
            return {
                "type": "answer_ack",
                "ok": False,
                "reason": "round_not_active",
            }

        elapsed = time.time() - self.round_start
        late = elapsed > self.time_limit_sec

        # prevent double answers
        if player in self.answers[qid]:
            return {
                "type": "answer_ack",
                "ok": False,
                "reason": "already_answered",
            }

        # ALWAYS record the answer (even if late)
        self.answers[qid][player] = (answer, elapsed, late)

        self._ensure_player(player)

        return {
            "type": "answer_ack",
            "ok": True,
            "elapsed": round(elapsed, 3),
            "late": late,
        }


    def end_round_and_score(self) -> Dict:
        if not self.round_active or not self.round_qid:
            return {"type": "round_result", "ok": False}

        qid = self.round_qid
        q = self.question_map.get(qid)
        correct = q.answer if q else ""

        # --- determine correct (on-time) players ---
        correct_players: list[tuple[str, float]] = []

        for player, (ans, elapsed, late) in self.answers[qid].items():
            if not late and self._normalize(ans) == self._normalize(correct):
                correct_players.append((player, elapsed))

        # fastest correct wins
        correct_players.sort(key=lambda x: x[1])
        winner = correct_players[0][0] if correct_players else None

        # --- build details & score ---
        details = []

        for player, (ans, elapsed, late) in self.answers[qid].items():
            is_correct = self._normalize(ans) == self._normalize(correct)
            scored = is_correct and not late

            bonus = self._speed_bonus(elapsed) if scored else 0
            points = (self.base_score + bonus) if scored else 0

            if scored:
                self.scoreboard[player]["score"] += points

            details.append(
                {
                    "player": player,
                    "answer": ans,
                    "time_sec": round(elapsed, 3),
                    "late": late,
                    "correct": is_correct,
                    "points": points,
                    "bonus": bonus,
                }
            )

        # winner gets win
        if winner:
            self.scoreboard[winner]["wins"] += 1

        # count round participation for ALL players
        self._finalize_round_participation()

        # close round
        self.round_active = False
        self.round_qid = None
        self.round_start = 0.0

        return {
            "type": "round_result",
            "ok": True,
            "qid": qid,
            "correct_answer": correct,
            "winner": winner,
            "details": details,
            "leaderboard": self.get_leaderboard(),
        }


    # ---------- leaderboard ----------

    def get_leaderboard(self) -> List[Dict]:
        board = [
            {
                "player": p,
                "score": s["score"],
                "wins": s["wins"],
                "rounds": s["rounds"],
            }
            for p, s in self.scoreboard.items()
        ]
        board.sort(key=lambda x: (x["score"], x["wins"]), reverse=True)
        return board


    # ---------- helpers ----------

    def reset(self) -> None:
        """Hard reset for new game (use when all players leave)"""
        self.q_index = 0
        self.round_active = False
        self.round_qid = None
        self.round_start = 0.0
        self.answers.clear()
        self.scoreboard.clear()
        self.round_players.clear()   # 👈 NEW
        self.running = False


    def _ensure_player(self, player: str) -> None:
        if player not in self.scoreboard:
            self.scoreboard[player] = {
                "score": 0,
                "wins": 0,
                "rounds": 0,
            }


    def _register_round_players(self, players: list[str]) -> None:
        """
        Call once at the start of a round.
        Every player here will get rounds += 1 when the round ends.
        """
        self.round_players = set(players)
        for p in self.round_players:
            self._ensure_player(p)


    def _finalize_round_participation(self) -> None:
        """
        Call once when the round ends.
        Counts the round for ALL players, even if they answered late or not at all.
        """
        for p in self.round_players:
            self.scoreboard[p]["rounds"] += 1

        self.round_players.clear()


    def _speed_bonus(self, elapsed: float) -> int:
        if elapsed <= 0:
            return self.fast_bonus_max
        if elapsed >= self.time_limit_sec:
            return 0
        return int(round(self.fast_bonus_max * (1 - elapsed / self.time_limit_sec)))


    @staticmethod
    def _normalize(s: str) -> str:
        return (s or "").strip().lower()

