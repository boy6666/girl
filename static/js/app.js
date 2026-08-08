// AI Girlfriend Bot - 前端脚本

// ============ 页面导航 ============
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;

        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        // 显示对应页面
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');

        // 加载页面数据
        if (page === 'memory') loadMemoryFacts();
        if (page === 'status') loadStatus();
    });
});

// ============ 对话测试 ============
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    // 添加用户消息
    addMessage(message, 'user');
    input.value = '';

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();

        if (data.error) {
            addMessage(data.error, 'ai');
        } else {
            addMessage(data.response, 'ai', data.emotion);
        }
    } catch (e) {
        addMessage('发送失败，请检查服务器连接', 'ai');
    }
}

function addMessage(text, type, emotion = null) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `message ${type}`;

    let icon = type === 'user' ? '👤' : '🤖';
    if (emotion) {
        const icons = {
            happy: '😊', sad: '😢', angry: '😠', shy: '😳',
            cute: '🥰', confused: '😕', love: '❤️', neutral: '😐'
        };
        icon = icons[emotion] || icon;
    }

    div.innerHTML = `<span>${icon}</span> ${text}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

document.getElementById('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// ============ 人格调参 ============
async function loadPersonality() {
    try {
        const res = await fetch('/api/config/personality');
        const data = await res.json();

        ['sweetness', 'coolness', 'initiative_threshold', 'mood_volatility', 'humor'].forEach(key => {
            const slider = document.getElementById(key);
            const value = document.getElementById(`${key}-value`);
            if (slider && value) {
                slider.value = data[key];
                value.textContent = data[key];
            }
        });
    } catch (e) {
        showToast('加载人格配置失败');
    }
}

function updateSlider(key, value) {
    document.getElementById(`${key}-value`).textContent = value;
}

async function savePersonality() {
    const updates = {
        sweetness: parseInt(document.getElementById('sweetness').value),
        coolness: parseInt(document.getElementById('coolness').value),
        initiative_threshold: parseInt(document.getElementById('initiative_threshold').value),
        mood_volatility: parseInt(document.getElementById('mood_volatility').value),
        humor: parseInt(document.getElementById('humor').value)
    };

    try {
        await fetch('/api/config/personality', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        showToast('✓ 保存成功');
    } catch (e) {
        showToast('保存失败');
    }
}

// ============ 记忆管理 ============
async function loadMemoryFacts() {
    try {
        const res = await fetch('/api/memory/facts');
        const facts = await res.json();

        const container = document.getElementById('memory-list');

        if (facts.length === 0) {
            container.innerHTML = '<p class="loading">暂无记忆</p>';
            return;
        }

        container.innerHTML = facts.map(f => `
            <div class="memory-item">
                <div class="memory-content">
                    <div class="memory-triple">
                        <strong>${f.subject}</strong> ${f.predicate} ${f.object || ''}
                    </div>
                    <div class="memory-time">${f.created_at ? new Date(f.created_at).toLocaleString('zh-CN') : ''}</div>
                </div>
                <button class="delete-btn" onclick="deleteFact(${f.id})">删除</button>
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('memory-list').innerHTML = '<p class="loading">加载失败</p>';
    }
}

async function deleteFact(id) {
    if (!confirm('确定要删除这条记忆吗？')) return;

    try {
        await fetch(`/api/memory/facts/${id}`, { method: 'DELETE' });
        loadMemoryFacts();
        showToast('已删除');
    } catch (e) {
        showToast('删除失败');
    }
}

// ============ 系统状态 ============
async function loadStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        // 更新状态条
        document.getElementById('status-energy').style.width = `${data.behavior.energy}%`;
        document.getElementById('text-energy').textContent = `${Math.round(data.behavior.energy)}%`;

        document.getElementById('status-mood').style.width = `${data.behavior.mood}%`;
        document.getElementById('text-mood').textContent = `${Math.round(data.behavior.mood)}%`;

        document.getElementById('status-social').style.width = `${data.behavior.social_need}%`;
        document.getElementById('text-social').textContent = `${Math.round(data.behavior.social_need)}%`;

        // 更新统计
        document.getElementById('stat-facts').textContent = data.memory_facts;
        document.getElementById('stat-vectors').textContent = data.memory_vectors;

        // 表情包统计
        const stickerStats = document.getElementById('sticker-stats');
        const emojiMap = {
            happy: '😊', sad: '😢', angry: '😠', shy: '😳',
            cute: '🐱', confused: '🤔', neutral: '😐', love: '❤️', anxious: '😰'
        };

        stickerStats.innerHTML = Object.entries(data.sticker_stats)
            .map(([key, count]) => `
                <div class="sticker-stat">
                    <div class="emoji">${emojiMap[key] || '❓'}</div>
                    <div class="count">${count}</div>
                    <div class="label">${key}</div>
                </div>
            `).join('');
    } catch (e) {
        console.error('加载状态失败', e);
    }
}

// ============ 工具函数 ============
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    loadPersonality();
    loadStatus();

    // 每5秒刷新状态
    setInterval(loadStatus, 5000);
});