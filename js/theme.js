/*
 * Перемикач дизайну IT School Hub.
 * Підключається в <head> БЕЗ defer, щоб клас теми з'явився до першого малювання сторінки
 * (інакше сторінка на мить блимне класичним дизайном).
 *
 * Класичний дизайн — основний. Новий (2026) вмикається кнопкою на головній
 * і запам'ятовується в localStorage для всіх сторінок сайту.
 * Також можна відкрити будь-яку сторінку з ?design=2026 або ?design=classic.
 */
(function () {
    var KEY = 'ithub-design';
    var NEW = '2026';
    var CLASS = 'theme-2026';
    var FONTS = 'https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700;800' +
        '&family=Unbounded:wght@500;700;800&family=JetBrains+Mono:wght@400;600&display=swap';
    var root = document.documentElement;

    function read() {
        try { return localStorage.getItem(KEY); } catch (e) { return null; }
    }

    function write(value) {
        try {
            if (value) localStorage.setItem(KEY, value);
            else localStorage.removeItem(KEY);
        } catch (e) { /* приватний режим тощо — просто не запам'ятовуємо */ }
    }

    // Шрифти й плавні переходи між сторінками — лише для нового дизайну
    function loadExtras() {
        if (document.getElementById('ithub-2026-fonts')) return;
        var head = document.head || document.getElementsByTagName('head')[0];

        ['https://fonts.googleapis.com', 'https://fonts.gstatic.com'].forEach(function (href, i) {
            var pc = document.createElement('link');
            pc.rel = 'preconnect';
            pc.href = href;
            if (i === 1) pc.crossOrigin = '';
            head.appendChild(pc);
        });

        var fonts = document.createElement('link');
        fonts.id = 'ithub-2026-fonts';
        fonts.rel = 'stylesheet';
        fonts.href = FONTS;
        head.appendChild(fonts);

        var vt = document.createElement('style');
        vt.id = 'ithub-2026-vt';
        vt.textContent = '@view-transition { navigation: auto; }';
        head.appendChild(vt);
    }

    function apply(isNew) {
        root.classList.toggle(CLASS, isNew);
        if (isNew) loadExtras();
        else {
            var vt = document.getElementById('ithub-2026-vt');
            if (vt) vt.remove();
        }
    }

    // ?design=2026 / ?design=classic у адресі
    try {
        var q = new URLSearchParams(window.location.search).get('design');
        if (q === NEW) write(NEW);
        if (q === 'classic') write(null);
    } catch (e) { /* старі браузери */ }

    apply(read() === NEW);

    function isNew() { return root.classList.contains(CLASS); }

    function updateButtons() {
        var buttons = document.querySelectorAll('[data-design-toggle]');
        for (var i = 0; i < buttons.length; i++) {
            var b = buttons[i];
            // Формат атрибута: "довгий напис|короткий напис (для вузьких екранів)"
            var parts = (isNew() ? b.getAttribute('data-label-classic') : b.getAttribute('data-label-new')).split('|');
            b.innerHTML = '';
            var long = document.createElement('span');
            long.className = 'dt-long';
            long.textContent = parts[0];
            var short = document.createElement('span');
            short.className = 'dt-short';
            short.textContent = parts[1] || parts[0];
            b.appendChild(long);
            b.appendChild(short);
            b.setAttribute('aria-pressed', isNew() ? 'true' : 'false');
        }
    }

    function toggle() {
        var next = !isNew();
        write(next ? NEW : null);
        var run = function () { apply(next); updateButtons(); };
        var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (document.startViewTransition && !reduce) document.startViewTransition(run);
        else run();
    }

    window.ITHubDesign = { toggle: toggle, isNew: isNew };

    document.addEventListener('DOMContentLoaded', function () {
        updateButtons();
        document.addEventListener('click', function (e) {
            var t = e.target.closest && e.target.closest('[data-design-toggle]');
            if (t) { e.preventDefault(); toggle(); }
        });
    });
})();
