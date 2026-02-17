document.addEventListener('DOMContentLoaded', () => {
    // Автоматична ініціалізація підсвітки синтаксису для всіх уроків
    if (window.hljs) {
        hljs.highlightAll();
    }
});

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