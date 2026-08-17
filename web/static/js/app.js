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
        if (page === 'setup') loadSetup();
        if (page === 'memory') loadMemory();
        if (page === 'files') loadFiles();
        if (page === 'behavior') loadBehavior();
        if (page === 'status') loadStatus();
        if (page === 'active') loadActive();
        if (page === 'life') loadLife();
        if (page === 'memgraph') loadMemGraph();
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

// ============ 基础设定 ============
const GIRL_FIELDS = [
    ['name', '名字'], ['relation', '与主人的关系'], ['age', '年龄'],
    ['birthday', '生日'], ['background', '背景故事'],
    ['core_personality', '核心性格'], ['positioning', '定位'],
];
const OWNER_FIELDS = [
    ['nickname', '怎么称呼'], ['age', '年龄'], ['job', '职业'], ['schedule', '作息'],
    ['interests', '兴趣爱好'], ['dislikes', '不喜欢的事'],
    ['topics', '聊得来的话题'], ['important', '重要的事 / 约定 / 时刻'],
];
let SETUP = { girl: {}, owner: {}, init_mode: 'web_fill' };

async function loadSetup() {
    try {
        SETUP = await (await fetch('/api/setup')).json();
    } catch (e) { showToast('加载基础设定失败'); return; }
    // 初始化方式（单选按钮组）
    const modes = [
        ['wechat_ask', '微信一步步问', '让 AI 在微信里自然地问你关于你的事，慢慢了解你'],
        ['web_fill', '已在 Web 填好', '资料已在下面填好，AI 照着认识你，不再反复问你'],
    ];
    document.getElementById('setup-init').innerHTML = modes.map(([v, label, desc]) => `
        <label class="setup-mode ${SETUP.init_mode === v ? 'chosen' : ''}" data-v="${v}">
            <input type="radio" name="setup-init-mode" value="${v}"
                ${SETUP.init_mode === v ? 'checked' : ''} onchange="pickInitMode('${v}')">
            <strong>${label}</strong>
            <span class="setup-mode-desc">${desc}</span>
        </label>`).join('');
    renderSetupBlock('setup-girl', GIRL_FIELDS, SETUP.girl, 'girl');
    renderSetupBlock('setup-owner', OWNER_FIELDS, SETUP.owner, 'owner');
    renderSetupPreview();
    loadInitStatus();
}

function renderSetupBlock(elId, fields, values, prefix) {
    document.getElementById(elId).innerHTML = fields.map(([key, label]) => `
        <label class="beh"><span>${label}</span>
            <input id="su-${prefix}-${key}" value="${escapeHtml(values[key] ?? '')}"></label>
    `).join('');
}

function pickInitMode(v) {
    SETUP.init_mode = v;
    document.querySelectorAll('#setup-init .setup-mode').forEach(el =>
        el.classList.toggle('chosen', el.dataset.v === v));
    renderSetupPreview();
}

function collectSetup() {
    SETUP.girl = Object.fromEntries(GIRL_FIELDS.map(([k]) => [k, document.getElementById(`su-girl-${k}`).value]));
    SETUP.owner = Object.fromEntries(OWNER_FIELDS.map(([k]) => [k, document.getElementById(`su-owner-${k}`).value]));
    return SETUP;
}

function renderSetupPreview() {
    const pre = document.getElementById('setup-preview');
    if (!pre) return;
    const mode = SETUP.init_mode === 'wechat_ask'
        ? '微信一步步问：AI 会在相处里自然地问你关于你的事，慢慢了解你。'
        : '已在 Web 填好：AI 照着下方资料认识你，不再反复问你。';
    pre.textContent = `📌 初始化方式：${mode}`;
}

async function saveSetup() {
    const payload = collectSetup();
    try {
        const res = await (await fetch('/api/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })).json();
        SETUP = res;
        showToast(`✓ 基础设定已保存，已写入 ${res.written.join(' / ')}，下条消息生效`);
        renderSetupPreview();
    } catch (e) { showToast('保存失败'); }
}

// ============ 自动初始化 ============
async function loadInitStatus() {
    const el = document.getElementById('setup-init-status');
    if (!el) return;
    try {
        const d = await (await fetch('/api/active/init/status')).json();
        el.textContent = d.initialized
            ? `✅ ${d.note}\n\n--- 她已长成 ---\n${d.story}`
            : (d.note || '');
    } catch (e) { el.textContent = '（后台未起，读不到初始化状态）'; }
}

async function triggerInit() {
    const el = document.getElementById('setup-init-status');
    try {
        const d = await (await fetch('/api/active/init/trigger', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
        })).json();
        if (d.card) {
            el.textContent = `【成长请求卡（目标 ${d.target_age} 岁）· ${d.inject.provider}】\n\n${d.card}\n\n→ ${d.inject.note || ''}`;
            showToast('已生成成长请求（默认 dry_run，不真影响小语）');
        } else {
            el.textContent = d.note || '';
            showToast(d.note || '还差目标年龄');
        }
    } catch (e) { showToast('触发初始化失败'); }
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
        let ref = null;
        try { ref = await (await fetch('/api/active/reflection')).json(); } catch (e) {}
        const latest = ref && ref.latest;
        cards.push(['反思', latest ? latest.date : '—',
                    latest ? latest.first_line : '尚无反思——今晚她会回头看看']);
        let gr = null;
        try { gr = await (await fetch('/api/active/growth')).json(); } catch (e) {}
        if (gr && gr.config) {
            cards.push(['持续生长', gr.status.state === 'live' ? '每' + (gr.config.interval_days || 3) + '天 / 接真'
                        : gr.status.state === 'paused' ? '已暂停'
                        : '试跑中',
                    gr.status.live ? '有真实沉淀会续写 GROWTH.md' : '未接真 · 不会自动续写']);
        }
        document.getElementById('status-cards').innerHTML = cards.map(([k, v, sub]) => `
            <div class="status-card"><h3>${k}</h3>
                <div class="status-big">${v}</div><div class="status-sub">${sub}</div>
            </div>`).join('');
        if (ref) renderReflectionLink(ref);
        loadGrowthPanel();
    } catch (e) {
        showToast('加载状态失败');
    }
}

// ============ 反思链路开关（两个开关都开 = 全自动） ============
function renderReflectionLink(ref) {
    const cfg = ref.config || {};
    const st = ref.status || {};
    const panel = document.getElementById('reflection-link-panel');
    if (!panel) return;
    const stateLabel = st.state === 'live' ? '已接真 · 每晚自动反思'
        : st.state === 'paused' ? '反思已暂停'
        : '试跑中 · 未接真（不会每晚自动反思）';
    const color = st.state === 'live' ? '#22c55e' : '#f59e0b';
    panel.innerHTML = `
        <h3 style="margin:0 0 6px;">反思链路 <span style="color:${color}">● ${stateLabel}</span></h3>
        <p class="description" style="margin-bottom:12px;">${escapeHtml(st.hint || '')}</p>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
            <label class="beh" style="flex:1;min-width:180px;">
                <span>开关一 · 每晚反思（enabled）</span>
                <select id="rl-enabled">
                    <option value="true" ${cfg.enabled ? 'selected' : ''}>开</option>
                    <option value="false" ${!cfg.enabled ? 'selected' : ''}>关</option>
                </select>
            </label>
            <label class="beh" style="flex:1;min-width:180px;">
                <span>开关二 · 注入方式（provider）</span>
                <select id="rl-provider">
                    <option value="dry_run" ${cfg.provider === 'dry_run' ? 'selected' : ''}>试跑（只拼不写）</option>
                    <option value="openclaw" ${cfg.provider === 'openclaw' ? 'selected' : ''}>接真（写 reflect.md）</option>
                </select>
            </label>
        </div>
        <button class="btn-ghost" onclick="saveReflectionConfig()">保存这两个开关</button>`;
}

async function saveReflectionConfig() {
    const payload = {
        enabled: document.getElementById('rl-enabled').value === 'true',
        provider: document.getElementById('rl-provider').value,
    };
    try {
        const res = await (await fetch('/api/active/reflection/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })).json();
        showToast(res.status.live ? '✓ 已接真：每晚自动反思' : '设置已保存（未接真）');
        renderReflectionLink({ config: res.config, status: res.status });
    } catch (e) {
        showToast('保存反思开关失败');
    }
}

// ============ 持续生长（在 GROWTH.md 底子上续长） ============
async function loadGrowthPanel() {
    try {
        const g = await (await fetch('/api/active/growth')).json();
        renderGrowthLink(g);
    } catch (e) { /* 后台未起则静默 */ }
}

function renderGrowthLink(g) {
    const panel = document.getElementById('growth-link-panel');
    if (!panel) return;
    const cfg = g.config || {};
    const st = g.status || {};
    const stateLabel = st.state === 'live' ? '已接真 · 有真实沉淀会续写 GROWTH.md'
        : st.state === 'paused' ? '持续生长已暂停'
        : '试跑中 · 未接真（不会自动续写）';
    const color = st.live ? '#22c55e' : '#f59e0b';
    panel.innerHTML = `
        <h3 style="margin:0 0 6px;">持续生长 <span style="color:${color}">● ${stateLabel}</span></h3>
        <p class="description" style="margin-bottom:12px;">${escapeHtml(st.hint || '')}</p>
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
            <label class="beh" style="flex:1;min-width:160px;">
                <span>节奏（interval_days 天一次）</span>
                <input id="gw-interval" type="number" min="1" value="${cfg.interval_days || 3}" style="padding:6px;">
            </label>
            <label class="beh" style="flex:1;min-width:180px;">
                <span>注入方式（provider）</span>
                <select id="gw-provider">
                    <option value="dry_run" ${cfg.provider === 'dry_run' ? 'selected' : ''}>试跑（只拼不写）</option>
                    <option value="openclaw" ${cfg.provider === 'openclaw' ? 'selected' : ''}>接真（写 growth_in.md）</option>
                </select>
            </label>
        </div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;">
            <button class="btn-ghost" onclick="saveGrowthConfig()">保存持续生长</button>
            <button class="btn-ghost" onclick="growthTrigger()">现在拼一张看看</button>
        </div>
        <pre id="growth-card-preview" class="preview-box" style="min-height:70px;margin-top:12px;"></pre>`;
}

async function saveGrowthConfig() {
    const payload = {
        interval_days: parseInt(document.getElementById('gw-interval').value, 10) || 3,
        provider: document.getElementById('gw-provider').value,
    };
    try {
        const res = await (await fetch('/api/active/growth/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })).json();
        showToast(res.status.live ? '✓ 已接真：有真实沉淀会自动续长' : '设置已保存（未接真）');
        renderGrowthLink({ config: res.config, status: res.status });
    } catch (e) {
        showToast('保存持续生长失败');
    }
}

async function growthTrigger() {
    const el = document.getElementById('growth-card-preview');
    if (!el) return;
    try {
        const d = await (await fetch('/api/active/growth/trigger', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
        })).json();
        el.textContent = d.card
            ? `【此刻拼出的持续长成请求 · ${d.inject.provider}】\n\n${d.card}`
            : (d.note || '');
    } catch (e) { el.textContent = '拼卡失败'; }
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
