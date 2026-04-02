document.addEventListener('DOMContentLoaded', () => {
    // Автоматична ініціалізація підсвітки синтаксису для всіх уроків
    if (window.hljs) {
        hljs.highlightAll();
    }

    // Tutor chat widget for Python practice pages
    try {
        // initTutorChatWidget();
    } catch (_) {
        // fail silently
    }
});

function initTutorChatWidget() {
    const path = window.location.pathname || "";
    const isPythonPractice = path.includes("/python/lesson") && path.endsWith("/practice.html");
    if (!isPythonPractice) return;

    // If page already has a chat widget (lesson2 currently), do nothing.
    if (document.getElementById("lessonChat") || document.getElementById("chatToggleBtn")) return;

    const apiUrl =
        window.location.hostname === "itschoolhub.site"
            ? "https://ithub-brown.vercel.app/api/chat"
            : "/api/chat";

    // Derive lesson id from path (e.g. /python/lesson9/practice.html)
    const lessonMatch = path.match(/\/python\/(lesson\d+)\//);
    const lessonId = lessonMatch ? `python/${lessonMatch[1]}` : "python/practice";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.id = "chatToggleBtn";
    btn.className =
        "fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-5 py-4 rounded-2xl shadow-2xl hover:bg-black transition-all font-bold";
    btn.setAttribute("aria-controls", "lessonChat");
    btn.setAttribute("aria-expanded", "false");
    btn.textContent = "Чат ➔";

    const overlay = document.createElement("div");
    overlay.id = "chatSidebarOverlay";
    overlay.className = "fixed inset-0 z-40 bg-black/30 hidden";

    const panel = document.createElement("section");
    panel.id = "lessonChat";
    panel.className =
        "fixed top-0 right-0 z-50 h-screen w-[22rem] md:w-[26rem] max-w-[calc(100vw-2rem)] bg-white border-l border-slate-200 shadow-2xl overflow-hidden transform translate-x-full transition-transform duration-200";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Чат допомоги");

    panel.innerHTML = `
      <header class="p-5 bg-slate-900 text-white flex items-center justify-between gap-3">
        <div>
          <div class="text-xs uppercase tracking-widest text-slate-300 font-black">IT School Hub</div>
          <div class="text-lg font-extrabold">Чат-помічник</div>
        </div>
        <div class="flex items-center gap-2">
          <button type="button" id="chatControlsToggleBtn" class="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 transition text-xs font-black uppercase tracking-widest">
            Згорнути
          </button>
          <button type="button" id="chatCloseBtn" class="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 transition">✕</button>
        </div>
      </header>
      <div class="p-5 flex flex-col gap-4 h-[calc(100vh-76px)]">
        <div class="text-sm text-slate-600">
          Напиши запитання по практиці. Я підкажу, що поправити, але не напишу готову програму.
        </div>

        <div id="chatLog" class="space-y-3 flex-1 min-h-0 overflow-auto pr-1">
          <div class="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-sm text-slate-700">
            Привіт! Опиши, що має робити код і що виходить зараз — я підкажу, куди дивитися.
          </div>
        </div>

        <form id="chatForm" class="space-y-3">
          <div id="chatControls" class="space-y-3">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label class="text-xs font-black uppercase tracking-widest text-slate-500">
                Провайдер
                <select id="chatProvider"
                  class="mt-2 w-full p-3 border-2 border-slate-100 rounded-2xl outline-none focus:ring-2 focus:ring-[#e2f0d9]/40 focus:border-[#e2f0d9] text-sm">
                  <option value="auto" selected>auto</option>
                  <option value="gemini">gemini</option>
                  <option value="openai">openai</option>
                </select>
              </label>
              <div class="text-xs text-slate-500 leading-relaxed mt-1 md:mt-6">
                Якщо один провайдер недоступний — обери інший або залиш <b>auto</b>.
              </div>
            </div>

            <textarea id="chatMessage"
              class="w-full h-24 p-4 border-2 border-slate-100 rounded-2xl outline-none focus:ring-2 focus:ring-[#e2f0d9]/40 focus:border-[#e2f0d9] font-mono text-sm"
              placeholder="Наприклад: чому в мене помилка TypeError?" required></textarea>

            <div class="flex items-center gap-3">
              <button id="chatSendBtn" type="submit"
                class="btn-action px-10 py-4 bg-[#0f172a] text-white hover:bg-black transition-all">
                Надіслати ➔
              </button>
              <div id="chatStatus" class="text-xs text-slate-500"></div>
            </div>
          </div>
          <button type="button" id="chatControlsExpandBtn"
            class="hidden w-full p-4 rounded-2xl border-2 border-dashed border-slate-200 text-slate-600 text-sm font-bold hover:border-[#e2f0d9] transition-all">
            Форма згорнута — розгорнути
          </button>
        </form>
      </div>
    `;

    document.body.appendChild(btn);
    document.body.appendChild(overlay);
    document.body.appendChild(panel);

    const chatLog = panel.querySelector("#chatLog");
    const chatForm = panel.querySelector("#chatForm");
    const chatMessage = panel.querySelector("#chatMessage");
    const chatProvider = panel.querySelector("#chatProvider");
    const chatSendBtn = panel.querySelector("#chatSendBtn");
    const chatCloseBtn = panel.querySelector("#chatCloseBtn");
    const chatControls = panel.querySelector("#chatControls");
    const chatControlsToggleBtn = panel.querySelector("#chatControlsToggleBtn");
    const chatControlsExpandBtn = panel.querySelector("#chatControlsExpandBtn");

    function setOpen(open) {
        overlay.classList.toggle("hidden", !open);
        panel.classList.toggle("translate-x-full", !open);
        btn.setAttribute("aria-expanded", String(open));
        if (open && chatMessage) chatMessage.focus();
    }

    function setControlsCollapsed(collapsed) {
        if (!chatControls || !chatControlsToggleBtn || !chatControlsExpandBtn) return;
        chatControls.classList.toggle("hidden", collapsed);
        chatControlsExpandBtn.classList.toggle("hidden", !collapsed);
        chatControlsToggleBtn.textContent = collapsed ? "Розгорнути" : "Згорнути";
        if (chatMessage) {
            chatMessage.required = !collapsed;
        }
        if (chatSendBtn) {
            chatSendBtn.disabled = collapsed;
        }
        if (!collapsed && chatMessage) {
            chatMessage.focus();
        }
    }

    function appendBubble(text, kind) {
        if (!chatLog) return;
        const el = document.createElement("div");
        const base = "p-4 rounded-2xl text-sm whitespace-pre-wrap";
        if (kind === "user") {
            el.className = base + " bg-[#e2f0d9]/40 border border-[#e2f0d9] text-slate-900";
        } else if (kind === "error") {
            el.className = base + " bg-red-50 border border-red-200 text-red-800";
        } else {
            el.className = base + " bg-slate-50 border border-slate-100 text-slate-700";
        }

        const full = String(text ?? "");
        const shouldCollapse = kind !== "user" && full.length > 1200;
        const preview = shouldCollapse ? (full.slice(0, 800) + "\n\n…(скорочено) …") : full;

        if (!shouldCollapse) {
            el.textContent = full;
        } else {
            const textEl = document.createElement("div");
            textEl.textContent = preview;

            const btnWrap = document.createElement("div");
            btnWrap.className = "mt-3";

            const toggleBtn = document.createElement("button");
            toggleBtn.type = "button";
            toggleBtn.className =
                "px-4 py-2 rounded-xl border border-slate-200 bg-white/60 text-slate-700 text-xs font-black uppercase tracking-widest hover:border-[#e2f0d9] transition-all";
            toggleBtn.textContent = "Показати повністю";

            let expanded = false;
            toggleBtn.addEventListener("click", () => {
                expanded = !expanded;
                textEl.textContent = expanded ? full : preview;
                toggleBtn.textContent = expanded ? "Згорнути" : "Показати повністю";
                chatLog.scrollTop = chatLog.scrollHeight;
            });

            btnWrap.appendChild(toggleBtn);
            el.appendChild(textEl);
            el.appendChild(btnWrap);
        }

        chatLog.appendChild(el);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function gatherCode() {
        const parts = [];
        const textareas = Array.from(document.querySelectorAll("textarea")).filter((t) => t.id !== "chatMessage");
        for (const ta of textareas) {
            const v = (ta.value || "").trim();
            if (!v) continue;
            parts.push(`${ta.id || "textarea"}:\n${v}`);
        }
        // some tasks use text inputs
        const inputs = Array.from(document.querySelectorAll('input[type="text"]'));
        for (const inp of inputs) {
            const v = (inp.value || "").trim();
            if (!v) continue;
            parts.push(`${inp.id || "input"}: ${v}`);
        }
        const joined = parts.join("\n\n");
        return joined.length > 2000 ? joined.slice(0, 2000) + "\n... (обрізано) ..." : joined;
    }

    btn.addEventListener("click", () => setOpen(panel.classList.contains("translate-x-full")));
    overlay.addEventListener("click", () => setOpen(false));
    if (chatCloseBtn) chatCloseBtn.addEventListener("click", () => setOpen(false));
    if (chatControlsToggleBtn) chatControlsToggleBtn.addEventListener("click", () => {
        const collapsed = !chatControls.classList.contains("hidden");
        setControlsCollapsed(collapsed);
    });
    if (chatControlsExpandBtn) chatControlsExpandBtn.addEventListener("click", () => setControlsCollapsed(false));

    if (chatForm) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const message = (chatMessage?.value || "").trim();
            if (!message || chatSendBtn.disabled) return;

            appendBubble(message, "user");
            chatMessage.value = "";
            chatSendBtn.disabled = true;

            const typing = document.createElement("div");
            typing.className = "p-4 rounded-2xl bg-slate-50 border border-slate-100 w-16";
            typing.innerHTML = `
              <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
              </div>
            `;
            chatLog.appendChild(typing);
            chatLog.scrollTop = chatLog.scrollHeight;

            try {
                const resp = await fetch(apiUrl, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        message,
                        provider: chatProvider?.value || "auto",
                        lesson: lessonId,
                        task: "practice-chat",
                        code: gatherCode(),
                    }),
                });

                const data = await resp.json().catch(() => ({}));
                typing.remove();

                if (!resp.ok || data.ok === false) {
                    const mainErr = (data && (data.error || data.message)) || "Ой, щось пішло не так.";
                    const details = data?.meta?.error ? `\n\nДеталі провайдера: ${data.meta.error}` : "";
                    appendBubble(`${mainErr}${details}`, "error");
                } else {
                    appendBubble(data.reply || "Хм, я задумався. Спробуй перепитати.", "bot");
                }
            } catch (_) {
                typing.remove();
                appendBubble("Помилка мережі. Перевір зв'язок.", "error");
            } finally {
                chatSendBtn.disabled = false;
            }
        });
    }
}

/**
 * Універсальна функція зворотного зв'язку
 */
function displayFeedback(elementId, isSuccess, text) {
    const feedbackEl = document.getElementById(elementId);
    if (!feedbackEl) return;

    feedbackEl.textContent = text;
    feedbackEl.className = `mt-3 text-sm font-bold ${isSuccess ? 'text-green-600' : 'text-red-600'}`;
    feedbackEl.classList.remove('hidden');
}

/**
 * Перевірка коду (regex або строкове порівняння)
 */
function validateExercise(inputId, feedbackId, correctPattern) {
    const userInput = document.getElementById(inputId).value.trim();
    const isValid = userInput.includes(correctPattern); 
    
    if (isValid) {
        displayFeedback(feedbackId, true, "✅ Чудово! Завдання виконано вірно.");
    } else {
        displayFeedback(feedbackId, false, "❌ Спробуй ще раз, зверни увагу на синтаксис.");
    }
}

/**
 * Функція для відображення зворотного зв'язку (успіх/помилка)
 * @param {string} id - ID елемента для виведення тексту
 * @param {boolean} isSuccess - чи правильна відповідь
 * @param {string} message - текст повідомлення
 */
function showFeedback(id, isSuccess, message) {
    const el = document.getElementById(id);
    if (!el) return;

    // Очищуємо попередні класи
    el.classList.remove('hidden', 'bg-green-100', 'text-green-700', 'bg-red-100', 'text-red-700', 'success-animation');
    
    // Встановлюємо нові класи залежно від результату
    el.innerText = message;
    el.classList.add(isSuccess ? 'bg-green-100' : 'bg-red-100');
    el.classList.add(isSuccess ? 'text-green-700' : 'text-red-700');
    
    if (isSuccess) {
        el.classList.add('success-animation');
    }
    
    el.classList.remove('hidden');
}

/** ПЕРЕВІРКА ЗАВДАНЬ УРОКУ №2 **/

function checkTask1() {
    const code = document.getElementById('task1').value;
    // Перевірка наявності ключових змінних (повний контент збережено)
    if (code.includes('nickname') && code.includes('level') && code.includes('is_online')) {
        showFeedback('feedback1', true, '✅ Супер! Усі змінні оголошені правильно. Тепер ти справжній розробник ігор.');
    } else {
        showFeedback('feedback1', false, '❌ Схоже, ти забув одну зі змінних або зробив помилку в назві. Перевір написання nickname, level та is_online.');
    }
}

function checkTask2() {
    const code = document.getElementById('task2').value;
    // Перевірка логіки обчислення площі (повний контент збережено)
    if (code.includes('area') && (code.includes('a * b') || code.includes('5 * 8'))) {
        showFeedback('feedback2', true, '✅ Вірно! Розрахунок площі виконано бездоганно.');
    } else {
        showFeedback('feedback2', false, '❌ Використай формулу area = a * b, щоб отримати результат.');
    }
}

function checkTask3() {
    const val = document.getElementById('task3').value.trim();
    // Перевірка чутливості до регістру (повний контент збережено)
    if (val === 'my_score') {
        showFeedback('feedback3', true, '✅ Саме так! Python чутливий до регістру літер. my_score != My_Score.');
    } else {
        showFeedback('feedback3', false, '❌ Спробуй ще раз. Пам\'ятай: у коді була маленька m та маленька s.');
    }
}

/** ПЕРЕВІРКА ЗАВДАНЬ УРОКУ №3 **/

function check3_1() {
    const val = document.getElementById('ans1').value.replace(/\s+/g, '');
    if(val === 'price=float(price)' || val === 'price=float("15000.50")') {
        showFeedback('feedback1', true, "✅ Вірно! Тепер з ціною можна проводити математичні операції.");
    } else {
        showFeedback('feedback1', false, "❌ Спробуй ще раз. Використовуй функцію float().");
    }
}

function check3_2(ans) {
    if(ans === '1010') {
        showFeedback('feedback2', true, "✅ Правильно! Функція str() перетворила числа на текст, а текст просто 'склеївся'.");
    } else {
        showFeedback('feedback2', false, "❌ Ні, це була пастка! Числа перетворені на рядки.");
    }
}

function check3_3() {
    const val = document.getElementById('ans3').value.trim().toLowerCase();
    if(val === 'str()' || val === 'str') {
        showFeedback('feedback3', true, "✅ Точно! Функція str() ідеально підходить для перетворення результатів у текст.");
    } else {
        showFeedback('feedback3', false, "❌ Не зовсім. Подумай, яка функція робить 'string'?");
    }
}