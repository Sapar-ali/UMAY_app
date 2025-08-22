// VoiceWizard Web Component: step-by-step voice questionnaire
// Uses Web Speech API for recognition (ru-KZ with ru-RU fallback) and SpeechSynthesis for TTS prompts.
(function() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    function speak(text, lang) {
        try {
            if (!('speechSynthesis' in window)) return Promise.resolve();
            return new Promise((resolve) => {
                const utter = new SpeechSynthesisUtterance(text);
                utter.lang = lang || 'ru-RU';
                utter.rate = 1;
                utter.onend = resolve;
                // Stop any ongoing speech first
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utter);
            });
        } catch (_) {
            return Promise.resolve();
        }
    }

    function nowHHMM() {
        const d = new Date();
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        return `${hh}:${mm}`;
    }

    function todayYMD() {
        const d = new Date();
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    }

    function normalize(text) {
        return (text || '').toString().trim().toLowerCase();
    }

    function isNegativeOrSkip(text) {
        const t = normalize(text);
        return /(нет|не надо|пропусти|пропустить|далее|skip|no)/i.test(t);
    }

    function parseNumber(text) {
        const t = normalize(text).replace(/,/, '.');
        const m = t.match(/\d+[\.,]?\d*/);
        if (!m) return null;
        const num = parseFloat(m[0].replace(',', '.'));
        return isNaN(num) ? null : num;
    }

    function parseInteger(text) {
        const m = normalize(text).match(/\d{1,4}/);
        if (!m) return null;
        const n = parseInt(m[0], 10);
        return isNaN(n) ? null : n;
    }

    function parseBP(text) {
        const t = normalize(text);
        const m = t.match(/(\d{2,3})\s*(?:на|\/|\\|\-|—|:)\s*(\d{2,3})/);
        if (!m) return null;
        const sys = parseInt(m[1], 10), dia = parseInt(m[2], 10);
        if (isNaN(sys) || isNaN(dia)) return null;
        return { sys, dia };
    }

    function parseDate(text) {
        const t = normalize(text);
        if (/сегодня/.test(t)) return todayYMD();
        if (/вчера/.test(t)) {
            const d = new Date();
            d.setDate(d.getDate() - 1);
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            return `${yyyy}-${mm}-${dd}`;
        }
        // dd.mm.yyyy or dd.mm
        const m1 = t.match(/\b(\d{1,2})[\.\-/](\d{1,2})(?:[\.\-/](\d{2,4}))?\b/);
        if (m1) {
            const dd = String(parseInt(m1[1], 10)).padStart(2, '0');
            const mm = String(parseInt(m1[2], 10)).padStart(2, '0');
            let yyyy = m1[3] ? parseInt(m1[3], 10) : (new Date()).getFullYear();
            if (yyyy < 100) yyyy = 2000 + yyyy; // 24 -> 2024
            return `${yyyy}-${mm}-${dd}`;
        }
        return null;
    }

    function parseTime(text) {
        const t = normalize(text);
        if (/сейчас|текущее/.test(t)) return nowHHMM();
        const m = t.match(/\b(\d{1,2})[\.:\-\s](\d{1,2})\b/);
        if (m) {
            const hh = String(parseInt(m[1], 10)).padStart(2, '0');
            const mm = String(parseInt(m[2], 10)).padStart(2, '0');
            return `${hh}:${mm}`;
        }
        return null;
    }

    function setFieldValue(form, selector, value) {
        if (!form || !selector) return false;
        const el = form.querySelector(selector);
        if (!el) return false;
        if (el.tagName === 'SELECT') {
            // try direct match, else by option text
            let matched = false;
            for (const opt of el.options) {
                if (normalize(opt.value) === normalize(value) || normalize(opt.text) === normalize(value)) {
                    el.value = opt.value;
                    matched = true;
                    break;
                }
            }
            if (!matched) el.value = value;
        } else {
            el.value = value;
        }
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        try {
            el.classList.add('ring-2');
            setTimeout(() => el.classList.remove('ring-2'), 1200);
        } catch (_) {}
        return true;
    }

    function checkBox(form, selector, checked) {
        const el = form.querySelector(selector);
        if (!el) return false;
        el.checked = !!checked;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    const DISEASE_KEYWORDS = {
        gestosis: [/гестоз/i],
        diabetes: [/диабет/i, /сахар/i],
        hypertension: [/гипертони/i, /давлен/i],
        anemia: [/анеми/i],
        infections: [/инфекц/i, /вирус/i],
        placenta_pathology: [/патолог(ия|ии)\s+плацент/i, /плацент[аы]/i],
        polyhydramnios: [/многовод/i],
        oligohydramnios: [/маловод/i],
        pls: [/плс/i],
        pts: [/птс/i],
        eclampsia: [/эклампси/i]
    };

    const BIRTH_COMPLICATIONS_KEYWORDS = {
        gestational_hypertension: [/гестационн(ая|ой)\s+гипертенз/i],
        placenta_previa: [/плотн(ое|ого)\s+прикреплен/i],
        shoulder_dystocia: [/дистоц/i, /плечик/i],
        third_degree_tear: [/разрыв\s*3/i, /треть(ей|я)\s+степен/i],
        cord_prolapse: [/выпаден(ие|ия)\s+пуповин/i],
        postpartum_hemorrhage: [/прк/i, /кровопотер/i],
        placental_abruption: [/понрп/i, /отслойк[аи]\s+плацент/i]
    };

    class VoiceWizard extends HTMLElement {
        constructor() {
            super();
            this.attachShadow({ mode: 'open' });
            this.recognition = null;
            this.isListening = false;
            this.stopRequested = false;
            this.langPrimary = this.getAttribute('data-lang-primary') || 'ru-KZ';
            this.langFallback = this.getAttribute('data-lang-fallback') || 'ru-RU';
            this.form = null;
            this.stepIndex = 0;
            this.steps = [];
        }

        connectedCallback() {
            this.form = this.closest('form') || document.querySelector(this.getAttribute('data-form-selector') || 'form');
            this.render();

            if (!SpeechRecognition) {
                this.showUnsupported();
                return;
            }
            try {
                this.recognition = new SpeechRecognition();
                this.recognition.lang = this.langPrimary;
                this.recognition.interimResults = true;
                this.recognition.continuous = false;
                this.recognition.onresult = (e) => this.onResult(e);
                this.recognition.onend = () => this.onEnd();
                this.recognition.onerror = (e) => this.onError(e);
            } catch (_) {
                this.showUnsupported();
                return;
            }

            this.buildSteps();
            this.updateUI();
            this.bindEvents();
        }

        render() {
            const style = `
                :host { display: block; margin-top: 8px; }
                .box { background: rgba(255,255,255,0.8); border: 1px solid #e5e7eb; border-radius: 16px; padding: 12px; }
                .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
                .btn { cursor: pointer; border: 0; border-radius: 12px; padding: 10px 14px; font-weight: 700; color: white; background: linear-gradient(90deg,#10b981,#3b82f6); display: inline-flex; align-items: center; gap: 8px; }
                .btn[disabled] { opacity: .6; cursor: not-allowed; }
                .btn-stop { background: linear-gradient(90deg,#f59e0b,#ef4444); }
                .btn-secondary { cursor: pointer; border: 1px solid #d1d5db; background: white; color: #374151; padding: 8px 12px; border-radius: 10px; font-weight: 600; }
                .status { font-size: .95rem; color: #374151; }
                .q { margin-top: 8px; font-weight: 700; color: #111827; }
                .tx { margin-top: 6px; width: 100%; min-height: 64px; resize: vertical; border: 1px solid #e5e7eb; border-radius: 12px; padding: 8px; background: #f9fafb; }
                .prog { margin-top: 6px; color: #6b7280; font-size: .9rem; }
            `;
            const html = `
                <div class="box">
                    <div class="row">
                        <button type="button" class="btn" id="startBtn">🎧 Голосовой ввод пациента</button>
                        <button type="button" class="btn btn-stop" id="stopBtn" hidden>⏹️ Стоп</button>
                        <button type="button" class="btn-secondary" id="skipBtn" hidden>Пропустить</button>
                        <span class="status" id="status">Готов</span>
                    </div>
                    <div class="q" id="question"></div>
                    <textarea class="tx" id="answer" placeholder="Ответ будет здесь" readonly></textarea>
                    <div class="prog" id="progress"></div>
                </div>
            `;
            this.shadowRoot.innerHTML = `<style>${style}</style>${html}`;
            this.$ = (id) => this.shadowRoot.getElementById(id);
        }

        showUnsupported() {
            this.shadowRoot.innerHTML = `
                <div class="box"><div class="status">Ваш браузер не поддерживает голосовой ввод</div></div>
            `;
        }

        bindEvents() {
            this.$('startBtn').addEventListener('click', () => this.startWizard());
            this.$('stopBtn').addEventListener('click', () => this.stopWizard());
            this.$('skipBtn').addEventListener('click', () => this.nextStep(true));
        }

        buildSteps() {
            const sel = (name) => this.getAttribute(`data-${name}-selector`) || `input[name="${name}"]`;
            const sels = {
                patient_name: sel('patient_name'),
                age: sel('age'),
                pregnancy_weeks: sel('pregnancy_weeks'),
                weight_before: sel('weight_before'),
                weight_after: sel('weight_after'),
                sys: this.getAttribute('data-sys-selector') || 'input[name="blood_pressure_sys"]',
                dia: this.getAttribute('data-dia-selector') || 'input[name="blood_pressure_dia"]',
                complications: this.getAttribute('data-complications-selector') || 'textarea[name="complications"]',
                notes: this.getAttribute('data-notes-selector') || 'textarea[name="notes"]',
                birth_date: sel('birth_date'),
                birth_time: sel('birth_time'),
                child_gender: 'select[name="child_gender"]',
                child_weight: sel('child_weight'),
                delivery_method: 'select[name="delivery_method"]',
                anesthesia: 'select[name="anesthesia"]',
                blood_loss: sel('blood_loss'),
                labor_duration: sel('labor_duration')
            };

            this.steps = [
                { key: 'patient_name', question: 'Назовите фамилию и имя пациентки', selector: sels.patient_name, type: 'text' },
                { key: 'age', question: 'Возраст пациентки в годах?', selector: sels.age, type: 'int' },
                { key: 'pregnancy_weeks', question: 'Срок беременности в неделях?', selector: sels.pregnancy_weeks, type: 'int' },
                { key: 'weight_before', question: 'Вес до родов в килограммах?', selector: sels.weight_before, type: 'number' },
                { key: 'weight_after', question: 'Вес после родов в килограммах?', selector: sels.weight_after, type: 'number' },
                { key: 'bp', question: 'Артериальное давление? Например: 120 на 80', selector: [sels.sys, sels.dia], type: 'bp' },
                { key: 'complications', question: 'Осложнения в родах? Если нет, скажите: нет', selector: sels.complications, type: 'text' },
                { key: 'notes', question: 'Примечания по пациентке? Если нет, скажите: нет', selector: sels.notes, type: 'text' },
                { key: 'birth_date', question: 'Дата родов? Например: 15.01.2024 или скажите сегодня', selector: sels.birth_date, type: 'date' },
                { key: 'birth_time', question: 'Время родов? Например: 14 30 или 14:30', selector: sels.birth_time, type: 'time' },
                { key: 'child_gender', question: 'Пол ребенка? Мальчик или Девочка', selector: sels.child_gender, type: 'select', options: { 'мальчик': 'Мальчик', 'девочка': 'Девочка' } },
                { key: 'child_weight', question: 'Вес ребенка в граммах?', selector: sels.child_weight, type: 'int' },
                { key: 'delivery_method', question: 'Способ родоразрешения? Естественные, Кесарево, Вакуум, Щипцы', selector: sels.delivery_method, type: 'select', options: { 'естественные': 'Естественные роды', 'кесарево': 'Кесарево сечение', 'вакуум': 'Вакуум-экстракция', 'щипцы': 'Акушерские щипцы' } },
                { key: 'anesthesia', question: 'Анестезия? Нет, Эпидуральная, Спинальная, Общая, Местная', selector: sels.anesthesia, type: 'select', options: { 'нет': 'Нет', 'без': 'Нет', 'эпидураль': 'Эпидуральная', 'спинал': 'Спинальная', 'общая': 'Общая', 'местная': 'Местная' } },
                { key: 'blood_loss', question: 'Кровопотеря в миллилитрах?', selector: sels.blood_loss, type: 'int' },
                { key: 'labor_duration', question: 'Продолжительность родов в часах?', selector: sels.labor_duration, type: 'number' },
                { key: 'diseases', question: 'Есть ли сопутствующие заболевания? Перечислите. Скажите: нет — если нет', selector: null, type: 'checkboxes-disease' },
                { key: 'birth_complications', question: 'Были ли осложнения в родах? Перечислите. Скажите: нет — если нет', selector: null, type: 'checkboxes-birth' }
            ];
        }

        updateUI() {
            const total = this.steps.length;
            const idx = Math.min(this.stepIndex, total - 1);
            const step = this.steps[idx];
            this.$('question').textContent = step ? step.question : 'Готово';
            this.$('progress').textContent = step ? `Шаг ${idx + 1} из ${total}` : `Готово (${total} шагов)`;
        }

        async startWizard() {
            this.stopRequested = false;
            this.stepIndex = 0;
            this.$('startBtn').hidden = true;
            this.$('stopBtn').hidden = false;
            this.$('skipBtn').hidden = false;
            this.$('status').textContent = 'Начинаем голосовой ввод пациента';
            await this.askCurrent();
        }

        stopWizard() {
            this.stopRequested = true;
            try { if (this.recognition && this.isListening) this.recognition.stop(); } catch(_) {}
            this.$('startBtn').hidden = false;
            this.$('stopBtn').hidden = true;
            this.$('skipBtn').hidden = true;
            this.$('status').textContent = 'Остановлено';
        }

        async askCurrent() {
            if (this.stopRequested) return;
            const step = this.steps[this.stepIndex];
            if (!step) {
                this.$('status').textContent = 'Ввод завершён';
                this.$('question').textContent = 'Готово';
                return;
            }
            this.updateUI();
            await speak(step.question, this.langFallback);
            this.startListening();
        }

        startListening() {
            if (!this.recognition) return;
            try {
                this.isListening = true;
                this.$('status').textContent = 'Слушаю...';
                this.$('answer').value = '';
                this.recognition.lang = this.langPrimary;
                this.recognition.start();
            } catch (_) {}
        }

        onResult(event) {
            let finalText = '';
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const res = event.results[i];
                if (res.isFinal) finalText += res[0].transcript + ' ';
                else interim += res[0].transcript + ' ';
            }
            const combined = (finalText + interim).trim();
            this.$('answer').value = combined;
        }

        onEnd() {
            this.isListening = false;
            const text = this.$('answer').value.trim();
            if (!text && this.recognition && this.recognition.lang !== this.langFallback) {
                try { this.recognition.lang = this.langFallback; this.recognition.start(); return; } catch (_) {}
            }
            // Process the captured text
            this.applyAnswer(text);
        }

        onError(e) {
            this.isListening = false;
            this.$('status').textContent = 'Ошибка распознавания';
            // Proceed to next to avoid stuck
            this.nextStep(true);
        }

        applyAnswer(text) {
            const step = this.steps[this.stepIndex];
            if (!step) return;
            const neg = isNegativeOrSkip(text);
            let applied = false;
            if (!neg) {
                switch (step.type) {
                    case 'text':
                        applied = setFieldValue(this.form, step.selector, text);
                        break;
                    case 'int': {
                        const n = parseInteger(text);
                        if (n !== null) applied = setFieldValue(this.form, step.selector, String(n));
                        break;
                    }
                    case 'number': {
                        const n = parseNumber(text);
                        if (n !== null) applied = setFieldValue(this.form, step.selector, String(n));
                        break;
                    }
                    case 'bp': {
                        const bp = parseBP(text);
                        if (bp) {
                            const [selSys, selDia] = step.selector;
                            setFieldValue(this.form, selSys, String(bp.sys));
                            setFieldValue(this.form, selDia, String(bp.dia));
                            applied = true;
                        }
                        break;
                    }
                    case 'date': {
                        const d = parseDate(text);
                        if (d) applied = setFieldValue(this.form, step.selector, d);
                        break;
                    }
                    case 'time': {
                        const t = parseTime(text);
                        if (t) applied = setFieldValue(this.form, step.selector, t);
                        break;
                    }
                    case 'select': {
                        const t = normalize(text);
                        let value = null;
                        for (const key in step.options || {}) {
                            if (t.includes(key)) { value = step.options[key]; break; }
                        }
                        if (!value) value = text;
                        applied = setFieldValue(this.form, step.selector, value);
                        break;
                    }
                    case 'checkboxes-disease': {
                        const t = text.toLowerCase();
                        let any = false;
                        for (const name in DISEASE_KEYWORDS) {
                            const patterns = DISEASE_KEYWORDS[name];
                            if (patterns.some(rx => rx.test(t))) {
                                any = checkBox(this.form, `input[name="${name}"]`, true) || any;
                            }
                        }
                        applied = any;
                        break;
                    }
                    case 'checkboxes-birth': {
                        const t = text.toLowerCase();
                        let any = false;
                        for (const name in BIRTH_COMPLICATIONS_KEYWORDS) {
                            const patterns = BIRTH_COMPLICATIONS_KEYWORDS[name];
                            if (patterns.some(rx => rx.test(t))) {
                                any = checkBox(this.form, `input[name="${name}"]`, true) || any;
                            }
                        }
                        applied = any;
                        break;
                    }
                }
            }
            this.$('status').textContent = applied ? 'Записано' : 'Пропущено';
            this.nextStep(false);
        }

        async nextStep(skippedByUser) {
            if (this.stopRequested) return;
            this.stepIndex += 1;
            if (this.stepIndex >= this.steps.length) {
                await speak('Опрос завершён', this.langFallback);
                this.stopWizard();
                return;
            }
            await this.askCurrent();
        }
    }

    if (!customElements.get('voice-wizard')) {
        customElements.define('voice-wizard', VoiceWizard);
    }
})();


