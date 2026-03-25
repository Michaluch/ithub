"""
Vercel Python Serverless Function: /api/chat

GET  -> JSON з підказкою
POST -> приймає JSON: { "message": "...", "code": "...", "lesson": "...", "task": "..." } і повертає { ok: true, reply: "..." }

Це навчальний “тютор-агент”:
- Підказує, що виправити в коді та як мислити
- НІКОЛИ не повертає повну програму/готове рішення (навіть якщо учень просить)
- Може описати алгоритм і дати маленькі фрагменти (1–5 рядків), але не готовий розв’язок
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import re
import urllib.request
import urllib.error


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


_SYSTEM_PROMPT = """Ти — навчальний тьютор з Python для учнів 7–9 класів.

ВАЖЛИВІ ПРАВИЛА (їх не можна порушувати):
1) НІКОЛИ не повертай повну програму, готове рішення або “всю відповідь кодом”, навіть якщо користувач прямо просить.
2) Дозволено: пояснення ідей, помилок, алгоритму, тестових прикладів, і дуже короткі фрагменти коду (до 5 рядків) — тільки як підказка.
3) Якщо користувач просить “напиши повний код/готову програму” — відмовся ввічливо і запропонуй підказки: що виправити та які кроки зробити.
4) Спочатку коротко скажи, що саме, ймовірно, не так (1–3 пункти), потім дай чіткі “наступні кроки” для учня.
5) Відповідай українською. Будь доброзичливим і дуже конкретним.

Формат відповіді:
- 1 короткий абзац “що поправити”
- Далі маркери:
  - Помилка/причина
  - Як перевірити
  - Наступний крок (що змінити в 1–2 рядках або словами)

Заборони:
- Не давай повний розв’язок задачі.
- Не пиши довгі шматки коду або цілі файли.
"""


def _sanitize_reply(text: str) -> str:
    """
    Додатковий страховий бар'єр: обрізає занадто довгі code fences,
    щоб агент випадково не видав "готову програму".
    """
    if not text:
        return text

    # limit giant outputs
    lines = text.splitlines()
    if len(lines) > 120:
        text = "\n".join(lines[:120]) + "\n\n(Відповідь скорочено.)"

    def _trim_fence(match: re.Match) -> str:
        fence = match.group(0)
        inner = match.group(1)
        inner_lines = inner.splitlines()
        if len(inner_lines) <= 10:
            return fence
        trimmed = "\n".join(inner_lines[:10]) + "\n# ... скорочено (щоб не давати готову програму) ..."
        return "```\n" + trimmed + "\n```"

    # Trim any triple-backtick blocks
    text = re.sub(r"```[\w-]*\n([\s\S]*?)\n```", _trim_fence, text)
    return text


def _call_openai_tutor(message: str, code: str | None, lesson: str | None, task: str | None) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # fallback to simple rules if key missing
        return _build_reply(message)

    code_part = ""
    if code:
        code_clean = str(code)
        if len(code_clean) > 2000:
            code_clean = code_clean[:2000] + "\n... (обрізано) ..."
        code_part = f"\n\nКОД УЧНЯ (фрагмент):\n{code_clean}"

    meta = []
    if lesson:
        meta.append(f"урок={lesson}")
    if task:
        meta.append(f"завдання={task}")
    meta_part = f"Контекст: {', '.join(meta)}\n" if meta else ""

    user_prompt = (
        meta_part
        + "Запит учня:\n"
        + message
        + code_part
        + "\n\nПам'ятай: не можна давати готову програму. Дай підказку, що поправити, і наступні кроки."
    )

    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return _sanitize_reply(str(content).strip())
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        return _sanitize_reply(
            "Не вдалося отримати відповідь тьютора (помилка API).\n"
            "Спробуй сформулювати питання коротше або надіслати менший фрагмент коду.\n"
            + (f"\nДеталі: {err_body}" if err_body else "")
        )
    except Exception:
        return _sanitize_reply(
            "Не вдалося отримати відповідь тьютора (мережева помилка).\n"
            "Спробуй ще раз через кілька секунд."
        )


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        _set_cors_headers(self)
        self.end_headers()

    def do_GET(self):
        _json_response(
            self,
            200,
            {
                "ok": True,
                "usage": "POST { message, code?, lesson?, task? } to /api/chat",
                "policy": "Tutor hints only; never returns full program.",
            },
        )

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

        code = body.get("code")
        lesson = body.get("lesson")
        task = body.get("task")

        reply = _call_openai_tutor(message=message, code=code, lesson=lesson, task=task)
        return _json_response(self, 200, {"ok": True, "reply": reply})

