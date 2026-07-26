# Simple in-memory session store (swap for Redis if you have time later —
# fine for a hackathon single-instance demo, resets on backend restart)
SESSIONS = {}

MAX_TURNS_STORED = 20  # soft cap so a long demo session doesn't grow unbounded


def get_session(session_id: str):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = []
    return SESSIONS[session_id]


def add_turn(session_id: str, role: str, content: str):
    session = get_session(session_id)
    session.append({"role": role, "content": content})
    if len(session) > MAX_TURNS_STORED:
        del session[: len(session) - MAX_TURNS_STORED]
