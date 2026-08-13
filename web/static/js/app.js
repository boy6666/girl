// 小语 · 伴侣后台 前端脚本

const PERSONALITY_DIMS = {
    sweetness: { label: '甜度', lo: '冷淡', hi: '甜蜜' },
    coolness: { label: '高冷', lo: '热情', hi: '高冷' },
    initiative_threshold: { label: '主动阈值', lo: '易主动', hi: '不主动' },
    mood_volatility: { label: '情绪波动', lo: '平稳', hi: '起伏大' },
    humor: { label: '幽默', lo: '正经', hi: '俏皮' },
};

// ============ 导航 ============
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');
        if (page === 'memory') loadMemory();
        if (page === 'files') loadFiles();
        if (page === 'behavior') loadBehavior();
        if (page === 'status') loadStatus();
        if (page === 'active') loadActive();
        if (page === 'life') loadLife();
    });
});

// ============ 人格滑块 ============
async function loadPersonality() {
    try {
        const data = await (await fetch('/api/personality')).json();
        renderSliders(data);
        loadPreview();
    } catch (e) {
        showToast('加载人格配置失败');
    }
}

function renderSliders(values) {
    const wrap = document.getElementById('sliders-wrap');
    wrap.innerHTML = Object.entries(PERSONALITY_DIMS).map(([key, meta]) => `
        <div class="slider-group">
            <label>${meta.label} <span class="value" id="${key}-value">${values[key] ?? 50}</span></label>
            <input type="range" min="0" max="100" value="${values[key] ?? 50}"
                   id="${key}" oninput="updateSlider('${key}')">
            <div class="slider-labels"><span>${meta.lo}</span><span>${meta.hi}</span></div>
        </div>
    `).join('');
}

function updateSlider(key) {
    document.getElementById(`${key}-value`).textContent = document.getElementById(key).value;
}

async function savePersonality() {
    const payload = {};
    Object.keys(PERSONALITY_DIMS).forEach(k => {
        payload[k] = parseInt(document.getElementById(k).value, 10);
    });
    try {
        const res = await (await fetch('/api/personality', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })).json();
        showToast(res.soul_changed ? '✓ 已写入 SOUL.md，下条消息生效' : res.note);
        document.getElementById('soul-preview').textContent = res.preview;
    } catch (e) {
        showToast('保存失败');
    }
}

async function loadPreview() {
    try {
        const res = await (await fetch('/api/soul')).json();
        const idx = res.content.indexOf('## 滑块段');
        document.getElementById('soul-preview').textContent =
            idx === -1 ? res.content : res.content.slice(idx);
    } catch (e) { /* 忽略 */ }
}

// ============ 记忆 ============
async function loadMemory() {
    try {
        const data = await (await fetch('/api/memory')).json();
        document.getElementById('memory-stats').innerHTML = `
            <div class="stat-card"><div class="stat-number">${data.total_messages}</div><div class="stat-label">消息数</div></div>
            <div class="stat-card"><div class="stat-number">${data.sessions.length}</div><div class="stat-label">会话</div></div>
        `;
        const box = document.getElementById('memory-list');
        if (!data.sessions.length) {
            box.innerHTML = '<p class="loading">还没有会话 —— 去微信里跟小语说句话吧。</p>';
            return;
        }
        box.innerHTML = data.sessions.map(s => s.messages.map(m =>
            `<div class="message ${m.role === 'user' ? 'user' : 'ai'}">
                <span>${m.role === 'user' ? '👤' : '💗'}</span> ${escapeHtml(m.text)}
             </div>`
        ).join('')).join('');
    } catch (e) {
        document.getElementById('memory-list').innerHTML = '<p class="loading">加载失败</p>';
    }
}

// ============ 人格文件 ============
let FILES_DATA = [];
async function loadFiles() {
    try {
        const data = await (await fetch('/api/agent/files')).json();
        FILES_DATA = data.files;
        document.getElementById('file-tabs').innerHTML =
            data.files.map((f, i) => `<button class="file-tab ${i === 0 ? 'active' : ''}"
                onclick="showFile(${i})">${f.name}</button>`).join('');
        if (data.files.length) showFile(0);
    } catch (e) {
        showToast('加载人格文件失败');
    }
}

function showFile(i) {
    document.querySelectorAll('.file-tab').forEach((t, idx) => t.classList.toggle('active', idx === i));
    document.getElementById('file-content').textContent = FILES_DATA[i].content || '(空)';
}

// ============ 行为 ============
const BEHAVIOR_FIELDS = {
    energy: '精力值', mood: '情绪值', social_need: '社交需求',
    cooldown_seconds: '主动冷却(秒)', allow_late_night: '允许深夜主动',
    late_night_start: '深夜开始(时)', early_morning_end: '凌晨结束(时)',
};
async function loadBehavior() {
    const data = await (await fetch('/api/behavior')).json();
    document.getElementById('behavior-grid').innerHTML = Object.entries(BEHAVIOR_FIELDS)
        .map(([key, label]) => {
            const v = data[key];
            if (typeof v === 'boolean') {
                return `<label class="beh"><span>${label}</span>
                    <select id="beh-${key}">
                        <option value="true" ${v ? 'selected' : ''}>是</option>
                        <option value="false" ${!v ? 'selected' : ''}>否</option>
                    </select></label>`;
            }
            return `<label class="beh"><span>${label}</span>
                <input id="beh-${key}" type="number" value="${v ?? ''}"></label>`;
        }).join('');
}

async function saveBehavior() {
    const payload = {};
    Object.keys(BEHAVIOR_FIELDS).forEach(key => {
        const el = document.getElementById(`beh-${key}`);
        if (!el) return;
        if (el.tagName === 'SELECT') payload[key] = el.value === 'true';
        else payload[key] = Number(el.value);
    });
    await (await fetch('/api/behavior', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })).json();
    showToast('✓ 行为配置已保存');
}

// ============ 状态 ============
async function loadStatus() {
    try {
        const data = await (await fetch('/api/status')).json();
        const cards = [
            ['模型', data.model, 'DeepSeek 驱动'],
            ['channel', data.channel, '微信通道'],
            ['agents', data.agents.join(' / '), 'girl 绑定微信'],
            ['girl 会话', data.girl_agent.sessions + ' 个 / ' + data.girl_agent.messages + ' 条', data.girl_agent.workspace],
        ];
        let latest = null;
        try { latest = (await (await fetch('/api/active/reflection')).json()).latest; } catch (e) {}
        cards.push(['反思', latest ? latest.date : '—',
                    latest ? latest.first_line : '尚无反思——今晚她会回头看看']);
        document.getElementById('status-cards').innerHTML = cards.map(([k, v, sub]) => `
            <div class="status-card"><h3>${k}</h3>
                <div class="status-big">${v}</div><div class="status-sub">${sub}</div>
            </div>`).join('');
    } catch (e) {
        showToast('加载状态失败');
    }
}

// ============ 主动状态机 ============
const ACTIVE_RANGE_FIELDS = [
    { k: 'open_threshold',    min: 0,   max: 1,    step: 0.05, label: '开启阈值' },
    { k: 'cooldown_seconds',  min: 60,  max: 3600, step: 60,   label: '主动冷却(秒)' },
    { k: 'daily_max',         min: 1,   max: 10,   step: 1,    label: '每日上限' },
    { k: 'max_unanswered',    min: 1,   max: 10,   step: 1,    label: '未回上限' },
    { k: 'late_night_start',  min: 0,   max: 23,   step: 1,    label: '深夜窗口开始' },
    { k: 'early_morning_end', min: 1,   max: 8,    step: 1,    label: '深夜窗口结束' },
];
const ACTIVE_SELECT_FIELDS = [
    { k: 'attachment',      options: ['secure', 'anxious', 'avoidant'], label: '依恋类型(0回避=secure=焦虑1)' },
    { k: 'grow_provider',   options: ['dry_run', 'openclaw'],           label: '生长方式(dry=样例 / openclaw=真生长)' },
    { k: 'inject_provider', options: ['dry_run', 'openclaw'],           label: '注入方式(dry=试跑 / openclaw=真发)' },
];

async function loadActive() {
    try {
        const [cfg, state] = await Promise.all([
            fetch('/api/active/config').then(r => r.json()),
            fetch('/api/active/state').then(r => r.json()),
        ]);
        renderGauges(state);
        renderActiveSliders(cfg);
    } catch (e) { showToast('加载主动状态机失败'); }
}

function renderGauges(state) {
    const wrap = document.getElementById('active-gauges');
    const e = Math.max(0, Math.min(100, state.energy ?? 0));
    const m = Math.max(0, Math.min(1, ((state.mood ?? 0) + 1) / 2));
    const s = Math.max(0, Math.min(1, state.social_need ?? 0));
    wrap.innerHTML = [
        ['精力', e / 100, '#ff6b9d', `${Math.round(e)}`],
        ['情绪', m, '#7c3aed', `${Math.round(m * 100)}`],
        ['渴望', s, '#22c55e', `${Math.round(s * 100)}`],
    ].map(([label, ratio, color, text]) => gaugeSVG(label, ratio, color, text)).join('');
}

function gaugeSVG(label, ratio, color, text) {
    const r = 40, c = 2 * Math.PI * r;
    const off = c * (1 - ratio);
    return `<div class="gauge">
        <svg width="110" height="110" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="${r}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
            <circle cx="50" cy="50" r="${r}" fill="none" stroke="${color}" stroke-width="8"
                stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${off}"
                transform="rotate(-90 50 50)"/>
            <text x="50" y="50" text-anchor="middle" dy=".35em" fill="white" font-size="20" font-weight="bold">${text}</text>
        </svg>
        <div class="gauge-label">${label}</div>
    </div>`;
}

function renderActiveSliders(cfg) {
    const wrap = document.getElementById('active-sliders');
    let html = ACTIVE_RANGE_FIELDS.map(f => `
        <div class="slider-group">
            <label>${f.label} <span class="value" id="act-${f.k}-v">${cfg[f.k] ?? f.min}</span></label>
            <input type="range" min="${f.min}" max="${f.max}" step="${f.step}"
                   value="${cfg[f.k] ?? f.min}" id="act-${f.k}" data-key="${f.k}">
        </div>`).join('');
    ACTIVE_SELECT_FIELDS.forEach(f => {
        const cur = cfg[f.k] ?? f.options[0];
        html += `<div class="slider-group sel">
            <label>${f.label}</label>
            <select id="act-${f.k}" data-key="${f.k}">
                ${f.options.map(o => `<option value="${o}" ${o === cur ? 'selected' : ''}>${o}</option>`).join('')}
            </select></div>`;
    });
    wrap.innerHTML = html;
    wrap.querySelectorAll('input[type=range]').forEach(el => {
        el.oninput = () => {
            document.getElementById(`act-${el.dataset.key}-v`).textContent = el.value;
            saveActiveConfig();
        };
    });
    wrap.querySelectorAll('select').forEach(el => { el.onchange = saveActiveConfig; });
}

let _saveTimer = null;
async function saveActiveConfig() {
    const payload = {};
    ACTIVE_RANGE_FIELDS.forEach(f => {
        const el = document.getElementById(`act-${f.k}`);
        payload[f.k] = Number(el.value);
    });
    ACTIVE_SELECT_FIELDS.forEach(f => {
        const el = document.getElementById(`act-${f.k}`);
        payload[f.k] = el.value;
    });
    clearTimeout(_saveTimer);
    _saveTimer = setTimeout(async () => {
        try {
            const res = await (await fetch('/api/active/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })).json();
            showToast('主动状态机参数已保存');
            return res;
        } catch (e) { showToast('保存参数失败'); }
    }, 500);
}

// ============ 她的一天 ============
async function loadLife() {
    try {
        const [life, content, journal] = await Promise.all([
            fetch('/api/active/life').then(r => r.json()),
            fetch('/api/active/content').then(r => r.json()),
            fetch('/api/active/journal').then(r => r.json()),
        ]);
        document.getElementById('life-preview').innerHTML =
            `<div class="stat-card"><div class="stat-number">${escapeHtml(life.now_activity)}</div><div class="stat-label">现在在干嘛</div></div>
             <div class="stat-card wide"><div class="stat-label">今天高光</div>
                <div class="status-big">${life.highlights.length ? life.highlights.map(escapeHtml).join(' · ') : '（今天还没填高光——去给她的一天写点底色）'}</div>
             </div>`;
        document.getElementById('life-content-editor').value =
            JSON.stringify(content, null, 2);
        renderJournal(journal);
    } catch (e) { showToast('加载「她的一天」失败'); }
}

function renderJournal(journal) {
    const t = (journal && journal.text || '').trim();
    document.getElementById('life-log').textContent =
        (journal && journal.last ? `最近日志: ${journal.last}\n\n` : '') + (t || '（还没有生活日志——点「让她今天长一条」生成）');
}

async function saveContent() {
    const yamlText = document.getElementById('life-content-editor').value;
    try {
        const res = await (await fetch('/api/active/content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ yaml: yamlText }),
        })).json();
        if (res.error) { showToast(res.error); return; }
        document.getElementById('life-content-editor').value = JSON.stringify(res, null, 2);
        showToast('✓ 生活底色已保存');
        const life = await (await fetch('/api/active/life')).json();
        document.getElementById('life-preview').innerHTML =
            `<div class="stat-card"><div class="stat-number">${escapeHtml(life.now_activity)}</div><div class="stat-label">现在在干嘛</div></div>`;
    } catch (e) { showToast('保存失败'); }
}

async function growToday() {
    try {
        const j = await (await fetch('/api/active/grow', { method: 'POST' })).json();
        showToast(j.text ? '✓ 已生长一条' : '（本次没长出内容）');
        loadLife();
    } catch (e) { showToast('生长失败'); }
}

async function nudgeNow() {
    try {
        const j = await (await fetch('/api/active/nudge', { method: 'POST' })).json();
        document.getElementById('life-nudge-card').textContent =
            `卡片:\n${j.card}\n\n注入: ${j.inject.provider} · sent=${j.inject.sent}`;
        showToast(j.inject.sent ? '（真的被推了一次）' : '试跑：卡片已生成，未真发');
    } catch (e) { showToast('推送失败'); }
}

async function reflectNow() {
    try {
        const r = await (await fetch('/api/active/reflection/trigger', { method: 'POST' })).json();
        document.getElementById('reflect-preview').textContent = (r.card || '');
        showToast('已试跑反思请求（不真发）');
    } catch (e) { showToast('反思试跑失败'); }
}

// ============ 工具 ============
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2200);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    loadPersonality();
    loadStatus();
});
