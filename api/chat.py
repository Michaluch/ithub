"""
Vercel Python Serverless Function: /api/chat

GET  -> JSON з підказкою
POST -> приймає JSON: { "message": "...", "code"?: "...", "lesson"?: "...", "task"?: "...", "provider"?: "gemini|openai|auto" } і повертає { ok: true, reply: "..." }

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


def _fallback_tutor(message: str, code: str | None, lesson: str | None, task: str | None) -> str:
    """
    Fallback-тьютор без LLM: дає підказки і ніколи не повертає готову програму.
    """
    msg = (message or "").strip()
    code_text = (code or "").strip()
    hay = (msg + "\n" + code_text).lower()

    hints: list[str] = []

    if code_text:
        # типові помилки для 7–9 класу
        if ("if " in hay or "for " in hay or "while " in hay or "def " in hay) and ":" not in code_text:
            hints.append("Схоже, десь пропущена двокрапка `:` після if/for/while/def.")
        if "\t" in code_text:
            hints.append("Краще робити відступи пробілами (4 пробіли), а не табуляціями.")

    if "input" in hay:
        hints.append("Пам’ятай: `input()` повертає `str`. Для чисел використовуй `int(input(...))` або `float(input(...))`.")
    if "area" in hay or "пло" in hay:
        hints.append("Для площі: `area = a * b`. Перевір, що `a` і `b` — числа, а не рядки.")
    if "my_score" in hay or "my score" in hay or "case" in hay:
        hints.append("Python чутливий до регістру: `my_score` і `My_Score` — різні імена.")
    if "print" not in hay and (("task1" in hay) or ("task2" in hay) or ("task3" in hay)):
        hints.append("Не забудь `print(...)`, якщо завдання просить вивести результат.")

    if not hints:
        hints.append("Опиши, що саме не працює (помилка або неправильний результат) — і я підкажу, що перевірити.")

    context = []
    if lesson:
        context.append(str(lesson))
    if task:
        context.append(str(task))
    ctx_line = f"Контекст: {', '.join(context)}\n\n" if context else ""

    bullets = "\n".join([f"- {h}" for h in hints[:4]])
    return (
        ctx_line
        + "Зараз працюю у режимі підказок.\n\n"
        + "Що поправити (ймовірно):\n"
        + bullets
        + "\n\nНаступний крок: надішли 1) умову задачі, 2) твій код, 3) що виводить і що має вивести — і я вкажу конкретне місце, яке треба змінити."
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


def _is_truthy(val: object) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "y", "on")


def _truncate(s: str, limit: int) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= limit else (s[:limit] + "…")


def _call_gemini_tutor(message: str, code: str | None, lesson: str | None, task: str | None) -> tuple[str, bool, str | None]:
    """
    Gemini через Google Generative Language API.
    Env: GEMINI_API_KEY або GOOGLE_API_KEY
    Env optional: GEMINI_MODEL (default: gemini-1.5-flash)
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return ("", False, "missing_gemini_api_key")

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

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

    user_text = (
        meta_part
        + "Запит учня:\n"
        + message
        + code_part
        + "\n\nПам'ятай: не можна давати готову програму. Дай підказку, що поправити, і наступні кроки."
    )

    payload = {
        "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600},
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            if not candidates:
                return ("", False, "no_candidates")
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = ""
            if parts and isinstance(parts, list):
                text = str(parts[0].get("text", "")).strip()
            if not text:
                return ("", False, "empty_text")
            return (_sanitize_reply(text), True, None)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        # quota/rate/auth errors -> fallback hints
        if e.code in (401, 402, 403, 429):
            return ("", False, f"gemini_http_{e.code}: {_truncate(err_body, 2000)}")
        # Often: 400 bad request (payload/systemInstruction/model), 404 model not found, etc.
        # We still return an error code/snippet for debugging.
        err_short = f"gemini_http_{e.code}"
        if err_body:
            err_short = err_short + ": " + _truncate(err_body, 2000)
        return ("", False, err_short)
    except Exception:
        return ("", False, "gemini_network_error")


def _call_openai_tutor(message: str, code: str | None, lesson: str | None, task: str | None) -> tuple[str, bool, str | None]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # fallback to simple rules if key missing
        return ("", False, "missing_openai_api_key")

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
            text = _sanitize_reply(str(content).strip())
            if not text:
                return ("", False, "openai_empty_text")
            return (text, True, None)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        # If quota is exceeded -> fallback hints
        try:
            parsed = json.loads(err_body) if err_body else {}
        except Exception:
            parsed = {}
        err_type = ((parsed.get("error") or {}).get("type")) or ((parsed.get("error") or {}).get("code"))
        if err_type == "insufficient_quota":
            return ("", False, "openai_insufficient_quota")
        err_short = f"openai_http_{e.code}"
        if err_body:
            err_short = err_short + ": " + _truncate(err_body, 2000)
        return (_sanitize_reply(
            "Не вдалося отримати відповідь тьютора (помилка API).\n"
            "Спробуй сформулювати питання коротше або надіслати менший фрагмент коду.\n"
            + (f"\nДеталі: {err_body}" if err_body else "")
        ), False, err_short)
    except Exception:
        return ("", False, "openai_network_error")


def _pick_provider(raw: object) -> str:
    p = str(raw or "").strip().lower()
    if p in ("gemini", "openai", "auto"):
        return p
    return "auto"


def _call_tutor(provider: str, message: str, code: str | None, lesson: str | None, task: str | None) -> tuple[str, str, str | None]:
    """
    Returns: (reply, provider_used, error_code_or_snippet)
    provider_used: gemini | openai | fallback
    """
    if provider == "gemini":
        reply, used, err = _call_gemini_tutor(message, code, lesson, task)
        return (reply, "gemini" if used else "gemini", err)
    if provider == "openai":
        reply, used, err = _call_openai_tutor(message, code, lesson, task)
        return (reply, "openai" if used else "openai", err)

    # auto: try gemini then openai then fallback
    reply_g, used_g, err_g = _call_gemini_tutor(message, code, lesson, task)
    if used_g:
        return (reply_g, "gemini", None)

    reply_o, used_o, err_o = _call_openai_tutor(message, code, lesson, task)
    if used_o:
        return (reply_o, "openai", None)

    # both failed -> return an error (fallback disabled for debugging)
    return ("", "auto", err_g or err_o or "unknown_error")


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
                "usage": "POST { message, code?, lesson?, task?, provider?: gemini|openai|auto } to /api/chat",
                "policy": "Tutor hints only; never returns full program.",
                "providers": ["gemini", "openai", "auto"],
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
        provider = _pick_provider(body.get("provider"))
        debug = _is_truthy(body.get("debug")) or _is_truthy(os.environ.get("CHAT_DEBUG"))

        reply, provider_used, err = _call_tutor(provider=provider, message=message, code=code, lesson=lesson, task=task)
        meta = {"providerRequested": provider, "providerUsed": provider_used}
        if err:
            # For debugging: surface provider error (without secrets). You can also send debug=true from client.
            meta["error"] = err
            return _json_response(self, 502, {"ok": False, "error": "Tutor provider failed", "meta": meta})

        return _json_response(self, 200, {"ok": True, "reply": reply, "meta": meta})

