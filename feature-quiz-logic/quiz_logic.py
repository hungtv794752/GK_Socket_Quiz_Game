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
    """
    Quiz logic:
    - Load question bank from JSON
    - Start a round -> broadcast question + start_time
    - Accept answers from many clients
    - Score:
        + Correct: base_score + speed bonus
        + Wrong/timeout: 0
      Speed bonus: faster -> higher
    """

    def __init__(self, questions_path: str = "questions.json"):
        self.questions_path = questions_path
        self.title = "Quiz"
        self.time_limit_sec = 10
        self.base_score = 100
        self.fast_bonus_max = 50

        self.questions: List[Question] = []
        self.q_index = 0

        # Round state
        self.round_active = False
        self.round_qid: Optional[str] = None
        self.round_start = 0.0

        # answers[qid][player] = (answer, time_sec)
        self.answers: Dict[str, Dict[str, Tuple[str, float]]] = {}

        # scoreboard[player] = {"score": int, "wins": int, "rounds": int}
        self.scoreboard: Dict[str, Dict[str, int]] = {}

        self.load_questions()

    def load_questions(self) -> None:
        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.title = data.get("title", self.title)
        self.time_limit_sec = int(data.get("time_limit_sec", self.time_limit_sec))
        self.base_score = int(data.get("base_score", self.base_score))
        self.fast_bonus_max = int(data.get("fast_bonus_max", self.fast_bonus_max))

        qs = []
        for item in data["questions"]:
            qs.append(
                Question(
                    qid=item["id"],
                    text=item["question"],
                    choices=item["choices"],
                    answer=item["answer"],
                )
            )
        self.questions = qs
        self.q_index = 0

    def has_next_question(self) -> bool:
        return self.q_index < len(self.questions)

    def start_round(self) -> Dict:
        """
        Start a new round and return a payload that server can broadcast.
        """
        if not self.has_next_question():
            return {"type": "game_over", "message": "No more questions"}

        q = self.questions[self.q_index]
        self.q_index += 1

        self.round_active = True
        self.round_qid = q.qid
        self.round_start = time.time()

        if q.qid not in self.answers:
            self.answers[q.qid] = {}

        return {
            "type": "question",
            "qid": q.qid,
            "question": q.text,
            "choices": q.choices,
            "time_limit_sec": self.time_limit_sec,
            "server_time": self.round_start,  # optional
        }

    def submit_answer(self, player: str, qid: str, answer: str) -> Dict:
        """
        Server calls this when a client answers.
        Return an ack payload.
        """
        if not self.round_active or qid != self.round_qid:
            return {"type": "answer_ack", "ok": False, "reason": "round_not_active"}

        elapsed = time.time() - self.round_start
        if elapsed > self.time_limit_sec:
            return {"type": "answer_ack", "ok": False, "reason": "timeout"}

        # Only take the first answer per player per question
        if player in self.answers[qid]:
            return {"type": "answer_ack", "ok": False, "reason": "already_answered"}

        self.answers[qid][player] = (answer, elapsed)

        # Track rounds participated
        self._ensure_player(player)
        self.scoreboard[player]["rounds"] += 1

        return {"type": "answer_ack", "ok": True, "elapsed": round(elapsed, 3)}

    def end_round_and_score(self) -> Dict:
        """
        End current round, score everyone, determine fastest correct winner.
        Return a payload for server broadcast: results + leaderboard.
        """
        if not self.round_active or not self.round_qid:
            return {"type": "round_result", "ok": False, "reason": "no_active_round"}

        qid = self.round_qid
        q = next((x for x in self.questions if x.qid == qid), None)
        # q might be not found because self.questions was advanced, so find in bank by id safely:
        correct = self._get_correct_answer(qid)

        # Determine correct answers and fastest time
        correct_players: List[Tuple[str, float]] = []
        for player, (ans, t) in self.answers.get(qid, {}).items():
            if self._normalize(ans) == self._normalize(correct):
                correct_players.append((player, t))

        correct_players.sort(key=lambda x: x[1])  # fastest first
        winner = correct_players[0][0] if correct_players else None

        # Score each player who answered
        scored_detail = []
        for player, (ans, t) in self.answers.get(qid, {}).items():
            is_correct = self._normalize(ans) == self._normalize(correct)
            pts = 0
            bonus = 0

            if is_correct:
                bonus = self._speed_bonus(t)
                pts = self.base_score + bonus
                self.scoreboard[player]["score"] += pts

            scored_detail.append(
                {
                    "player": player,
                    "answer": ans,
                    "time_sec": round(t, 3),
                    "correct": is_correct,
                    "bonus": bonus,
                    "points": pts,
                }
            )

        # Winner gets a "win" count (ai trả lời đúng nhanh nhất)
        if winner:
            self.scoreboard[winner]["wins"] += 1

        # round ends
        self.round_active = False
        self.round_qid = None
        self.round_start = 0.0

        return {
            "type": "round_result",
            "ok": True,
            "qid": qid,
            "correct_answer": correct,
            "winner": winner,
            "details": scored_detail,
            "leaderboard": self.get_leaderboard(),
        }

    def get_leaderboard(self) -> List[Dict]:
        """
        Return sorted leaderboard by score desc, then wins desc
        """
        items = []
        for player, stats in self.scoreboard.items():
            items.append(
                {
                    "player": player,
                    "score": stats["score"],
                    "wins": stats["wins"],
                    "rounds": stats["rounds"],
                }
            )
        items.sort(key=lambda x: (x["score"], x["wins"]), reverse=True)
        return items

    # ----------------- helpers -----------------
    def _ensure_player(self, player: str) -> None:
        if player not in self.scoreboard:
            self.scoreboard[player] = {"score": 0, "wins": 0, "rounds": 0}

    def _speed_bonus(self, elapsed: float) -> int:
        """
        Bonus decreases linearly from fast_bonus_max at t=0
        to 0 at t=time_limit_sec.
        """
        if elapsed <= 0:
            return self.fast_bonus_max
        if elapsed >= self.time_limit_sec:
            return 0
        ratio = 1.0 - (elapsed / self.time_limit_sec)
        return int(round(self.fast_bonus_max * ratio))

    def _get_correct_answer(self, qid: str) -> str:
        # Find from loaded questions bank by qid
        for item in self.questions:
            if item.qid == qid:
                return item.answer
        # If not found (edge), load again or return empty
        # But normally should exist
        return ""

    @staticmethod
    def _normalize(s: str) -> str:
        return (s or "").strip().lower()
