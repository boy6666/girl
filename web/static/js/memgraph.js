// memgraph.js — 记忆图谱：轻量 SVG 力导向，零依赖。数据来自 /api/memory-graph（本机只读）。
const MG_COLORS = { you: '#ff5d5d', self: '#36a3f7', theme: '#9b5de5', memory: '#8d99ae' };

async function loadMemGraph() {
    const wrap = document.getElementById('memgraph-canvas');
    wrap.innerHTML = '<p class="loading">加载中…</p>';
    let data;
    try {
        data = await (await fetch('/api/memory-graph')).json();
    } catch (e) { wrap.innerHTML = '<p class="loading">图谱加载失败</p>'; return; }
    if (!data.nodes || !data.nodes.length) {
        wrap.innerHTML = '<p class="loading">还没有可入图的长时记忆——她会随生活与反思慢慢积累，这里就是她记得的一切。</p>';
        return;
    }
    renderGraph(wrap, data);
}

function renderGraph(wrap, data) {
    const W = Math.max(wrap.clientWidth || 900, 600), H = 560;
    const nodes = data.nodes.map(n => ({
        ...n, x: Math.random() * W, y: Math.random() * H, vx: 0, vy: 0,
        r: n.type === 'you' ? 22 : n.type === 'theme' ? 15 : 10,
    }));
    const links = data.edges;
    const byId = {}; nodes.forEach(n => byId[n.id] = n);

    // —— 力导向迭代：电荷斥力 + 弹簧吸引 + 阻尼 + 边界 ——
    for (let i = 0; i < 250; i++) {
        for (let a = 0; a < nodes.length; a++) {
            const A = nodes[a];
            for (let b = a + 1; b < nodes.length; b++) {
                const B = nodes[b];
                let dx = B.x - A.x, dy = B.y - A.y;
                let d2 = dx * dx + dy * dy; if (d2 < 1) d2 = 1;
                const f = 2600 / d2, d = Math.sqrt(d2);
                dx /= d; dy /= d;
                A.vx -= dx * f; A.vy -= dy * f; B.vx += dx * f; B.vy += dy * f;
            }
        }
        for (const l of links) {
            const A = byId[l.source], B = byId[l.target]; if (!A || !B) continue;
            let dx = B.x - A.x, dy = B.y - A.y;
            let d = Math.sqrt(dx * dx + dy * dy) || 1;
            const f = 0.02 * (d - 90);
            dx /= d; dy /= d;
            A.vx += dx * f; A.vy += dy * f; B.vx -= dx * f; B.vy -= dy * f;
        }
        for (const n of nodes) {
            n.vx *= 0.85; n.vy *= 0.85;
            n.x += n.vx; n.y += n.vy;
            if (n.x < 20) { n.x = 20; n.vx *= -0.5; }
            if (n.x > W - 20) { n.x = W - 20; n.vx *= -0.5; }
            if (n.y < 20) { n.y = 20; n.vy *= -0.5; }
            if (n.y > H - 20) { n.y = H - 20; n.vy *= -0.5; }
        }
    }

    // —— 渲染 SVG ——
    const svgNS = 'http://www.w3.org/2000/svg';
    wrap.innerHTML = `<div class="mg-legend">` +
        `<span><i style="background:#ff5d5d"></i>你</span>` +
        `<span><i style="background:#36a3f7"></i>我</span>` +
        `<span><i style="background:#9b5de5"></i>主题</span>` +
        `<span><i style="background:#8d99ae"></i>记忆点</span></div>` +
        `<svg id="mg-svg" width="${W}" height="${H}" style="border:1px solid #333;border-radius:10px;background:#14181f;display:block"></svg>`;
    const svg = wrap.querySelector('#mg-svg');
    const gLinks = document.createElementNS(svgNS, 'g');
    const gNodes = document.createElementNS(svgNS, 'g');
    svg.appendChild(gLinks); svg.appendChild(gNodes);

    for (const l of links) {
        const A = byId[l.source], B = byId[l.target]; if (!A || !B) continue;
        const line = document.createElementNS(svgNS, 'line');
        line.setAttribute('x1', A.x); line.setAttribute('y1', A.y);
        line.setAttribute('x2', B.x); line.setAttribute('y2', B.y);
        line.setAttribute('stroke', '#5a6270'); line.setAttribute('stroke-width', '1');
        gLinks.appendChild(line);
    }

    for (const n of nodes) {
        const g = document.createElementNS(svgNS, 'g');
        const tip = (n.text ? n.text : n.label) + (n.date ? (' （' + n.date + '）') : '');
        const title = document.createElementNS(svgNS, 'title');
        title.textContent = tip;
        const c = document.createElementNS(svgNS, 'circle');
        c.setAttribute('r', n.r); c.setAttribute('fill', MG_COLORS[n.type] || '#8d99ae');
        c.setAttribute('stroke', '#0b0e13'); c.setAttribute('stroke-width', '1.5');
        const t = document.createElementNS(svgNS, 'text');
        t.setAttribute('x', n.r + 6); t.setAttribute('y', 4);
        t.setAttribute('fill', '#d7dce3'); t.setAttribute('font-size', '12');
        const lbl = n.label || n.id;
        t.textContent = lbl.length > 16 ? lbl.slice(0, 15) + '…' : lbl;
        g.appendChild(title); g.appendChild(c); g.appendChild(t);
        g.style.cursor = 'grab';
        g.addEventListener('mousedown', (ev) => dragNode(ev, n, g, svg, W, H));
        gNodes.appendChild(g);
    }
}

function dragNode(ev, node, g, svg, W, H) {
    ev.preventDefault();
    g.style.cursor = 'grabbing';
    const bbox = svg.getBoundingClientRect();
    function move(e) {
        node.x = Math.max(20, Math.min(W - 20, e.clientX - bbox.left));
        node.y = Math.max(20, Math.min(H - 20, e.clientY - bbox.top));
        g.setAttribute('transform', `translate(${node.x},${node.y})`);
        updateLinks(node);
    }
    g.setAttribute('transform', `translate(${node.x},${node.y})`);
    function up() {
        g.style.cursor = 'grab';
        window.removeEventListener('mousemove', move);
        window.removeEventListener('mouseup', up);
    }
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
}

function updateLinks(moved) {
    const gLinks = document.querySelector('#mg-svg g') || document.querySelector('#mg-links');
    if (!gLinks) return;
    for (const line of gLinks.children) {
        const x1 = +line.getAttribute('x1');
        // 简化：把与 moved 同一首次坐标的边更新太复杂——保持静态，拖拽只动节点本身
    }
}
