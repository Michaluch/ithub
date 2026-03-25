"""
Vercel Python Serverless Function: /api/chat

GET  -> JSON з підказкою
POST -> приймає JSON: { "message": "..." } і повертає { ok: true, reply: "..." }

Це демо-чат без зовнішніх ключів/інтеграцій: відповіді будуються простими правилами.
"""

from http.server import BaseHTTPRequestHandler
import json


_ALLOWED_ORIGINS = {
    "https://itschoolhub.site",
    "https://ithub-brown.vercel.app",
}


def _get_cors_origin(handler: BaseHTTPRequestHandler) -> str | None:
    origin = handler.headers.get("origin")
    if origin in _ALLOWED_ORIGINS:
        return origin
    return None


def _set_cors_headers(handler: BaseHTTPRequestHandler):
    origin = _get_cors_origin(handler)
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    _set_cors_headers(handler)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _build_reply(message: str) -> str:
    normalized = message.lower()
    short = message if len(message) <= 400 else (message[:400] + "…")

    if "змінн" in normalized or "variable" in normalized:
        return (
            "Змінна — це ім’я для значення. Приклад: name = \"Olia\".\n"
            "Тип можна подивитись так: type(name)."
        )
    if "тип" in normalized or "int" in normalized or "float" in normalized:
        return (
            "У Python типи бувають int, float, str, bool.\n"
            "Перетворення: int(\"10\"), float(\"3.14\"), str(5)."
        )
    if "input" in normalized:
        return (
            "input() завжди повертає рядок (str).\n"
            "Якщо треба число — зроби int(input(...)) або float(input(...))."
        )
    if "if" in normalized or "умов" in normalized:
        return "Умова виглядає так:\nif x > 0:\n    print(\"+\")\nelse:\n    print(\"-\")"
    if "for" in normalized or "while" in normalized or "цикл" in normalized:
        return (
            "Цикли: for — коли перебираємо range() або список; while — коли повторюємо, поки умова True.\n"
            "Не забудь умову зупинки."
        )
    if "спис" in normalized or "list" in normalized:
        return "Список: items = [1, 2, 3]; додати: items.append(4); довжина: len(items)."

    return (
        "Я отримав твоє повідомлення:\n\n"
        + short
        + "\n\nПідказка: напиши “змінні”, “типи”, “input”, “if”, “цикли” або “списки”, і я дам приклад."
    )


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        _set_cors_headers(self)
        self.end_headers()

    def do_GET(self):
        _json_response(self, 200, {"ok": True, "usage": "POST { message } to /api/chat"})

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            length = 0

        raw = self.rfile.read(length) if length > 0 else b""
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}

        message = str(body.get("message", "")).strip()
        if not message:
            return _json_response(self, 400, {"ok": False, "error": "Empty message"})

        reply = _build_reply(message)
        return _json_response(self, 200, {"ok": True, "reply": reply})

