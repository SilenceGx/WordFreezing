/**
 * MathPin — 学习页 JS
 * 流程：加载题目 → 用户写解答 → AI评判 → 追问讨论 → 下一题
 */

let currentProblem = null;
let currentNodes = [];
let currentMode = 'new';  // 'new' | 'review'
let isSubmitting = false;

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', function() {
    loadNextProblem();
});

// ===== KaTeX 渲染工具 =====
function renderKatex(container, text) {
    if (!text || !text.trim()) {
        container.innerHTML = '(空)';
        return;
    }
    try {
        // 先渲染块级公式 $$...$$
        let html = text;
        // 处理行内公式 $...$
        html = html.replace(/\$\$(.+?)\$\$/gs, function(match, formula) {
            try {
                return katex.renderToString(formula.trim(), { displayMode: true, throwOnError: false });
            } catch(e) {
                return '<code>' + match + '</code>';
            }
        });
        html = html.replace(/\$(.+?)\$/g, function(match, formula) {
            try {
                return katex.renderToString(formula.trim(), { displayMode: false, throwOnError: false });
            } catch(e) {
                return '<code>' + match + '</code>';
            }
        });
        container.innerHTML = html;
    } catch(e) {
        container.textContent = text;
    }
}

// ===== 加载下一题 =====
async function loadNextProblem() {
    showLoading('加载题目...');
    const bookId = window.location.pathname.split('/').pop();

    try {
        const resp = await fetch('/math/api/next/' + bookId);
        const data = await resp.json();

        if (data.done) {
            hideLoading();
            document.getElementById('problemDisplay').style.display = 'none';
            document.getElementById('answerArea').style.display = 'none';
            document.getElementById('judgeArea').innerHTML =
                '<div style="text-align:center;padding:60px;color:var(--text-secondary);">'
                + '<p style="font-size:1.3rem;">' + (data.message || '🎉 全部完成！') + '</p>'
                + '<a href="/math/" class="btn btn-primary" style="margin-top:16px;">返回题本</a>'
                + '</div>';
            return;
        }

        currentProblem = data.problem;
        currentNodes = data.nodes || [];
        currentMode = data.mode;

        // 渲染题目
        const problemEl = document.getElementById('problemRenderer');
        renderKatex(problemEl, currentProblem.problem_text);

        // 显示作答区
        document.getElementById('problemDisplay').style.display = 'block';
        document.getElementById('answerArea').style.display = 'block';
        document.getElementById('judgeArea').style.display = 'none';
        document.getElementById('discussArea').style.display = 'none';
        document.getElementById('userAnswer').value = '';
        document.getElementById('userAnswer').focus();

        hideLoading();
    } catch (err) {
        console.error('加载失败:', err);
        showLoading('加载失败，请刷新页面');
    }
}

// ===== 提交评判 =====
async function submitAnswer() {
    if (isSubmitting) return;
    const answer = document.getElementById('userAnswer').value.trim();
    if (!answer) {
        alert('请先写出解答');
        return;
    }

    isSubmitting = true;
    document.getElementById('submitBtn').textContent = '评判中...';
    document.getElementById('submitBtn').disabled = true;

    try {
        const resp = await fetch('/math/api/judge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_id: currentProblem.id,
                user_answer: answer,
            }),
        });
        const data = await resp.json();

        document.getElementById('answerArea').style.display = 'none';
        renderJudgeResults(data);
    } catch (err) {
        alert('提交失败，请重试');
    } finally {
        isSubmitting = false;
        document.getElementById('submitBtn').textContent = '提交评判';
        document.getElementById('submitBtn').disabled = false;
    }
}

// ===== 不会 =====
async function dontKnow() {
    if (isSubmitting) return;
    // 直接当作所有节点都 miss
    const fakeResults = currentNodes.map(n => ({
        node_id: n.id,
        hit: false,
        title: n.title,
        description: n.description,
        formula: n.formula || '',
        feedback: '未作答',
        review: { status: 'learning', action: '未作答', stage: 0 },
    }));

    // 提交到后端处理复习状态
    try {
        await fetch('/math/api/judge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_id: currentProblem.id,
                user_answer: '（不会做）',
            }),
        });
    } catch(e) {}

    document.getElementById('answerArea').style.display = 'none';
    renderJudgeResults({ node_results: fakeResults, overall: '点击了"不会"，看看关键节点吧。' });
}

// ===== 渲染评判结果 =====
function renderJudgeResults(data) {
    const area = document.getElementById('judgeArea');
    area.style.display = 'block';

    const results = data.node_results || [];
    const hitCount = results.filter(r => r.hit).length;

    let html = '<div class="judge-result">';

    // 整体评价
    const overallClass = hitCount === results.length ? 'hit' : 'miss';
    html += `<div class="judge-overall judge-node ${overallClass}">
        踩中 ${hitCount}/${results.length} 个关键节点
        ${data.overall ? '<br><span style="font-weight:normal;font-size:0.9rem;">' + data.overall + '</span>' : ''}
    </div>`;

    // 逐节点结果
    results.forEach(r => {
        const cls = r.hit ? 'hit' : 'miss';
        const icon = r.hit ? '✅' : '❌';
        html += `<div class="judge-node ${cls}">
            <span class="node-title">${icon} ${r.title}</span>
            <div class="node-feedback">${r.feedback || ''}</div>`;
        // 未踩中时展示节点内容
        if (!r.hit && r.description) {
            html += `<div style="margin-top:6px;padding:8px;background:rgba(255,255,255,0.6);border-radius:6px;font-size:0.85rem;">
                <strong>参考：</strong>${r.description}
                ${r.formula ? '<br><strong>公式：</strong>' + r.formula : ''}
            </div>`;
        }
        html += '</div>';
    });

    html += '</div>';
    area.innerHTML = html;

    // 展示追问区
    document.getElementById('discussArea').style.display = 'block';
    document.getElementById('discussInput').focus();
}

// ===== 追问讨论 =====
async function sendDiscuss() {
    const input = document.getElementById('discussInput');
    const msg = input.value.trim();
    if (!msg || !currentProblem) return;

    input.value = '';
    document.getElementById('discussBtn').disabled = true;

    // 显示用户消息
    addDiscussMessage('user', msg);

    try {
        const resp = await fetch('/math/api/discuss', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_id: currentProblem.id,
                message: msg,
            }),
        });
        const data = await resp.json();
        if (data.success) {
            // 渲染 AI 回复（含 LaTeX）
            const msgDiv = addDiscussMessage('ai', '');
            renderKatex(msgDiv, data.reply);
        } else {
            addDiscussMessage('ai', '抱歉，出了点问题，请重试。');
        }
    } catch (err) {
        addDiscussMessage('ai', '网络错误，请重试。');
    } finally {
        document.getElementById('discussBtn').disabled = false;
        document.getElementById('discussInput').focus();
    }
}

function addDiscussMessage(role, text) {
    const container = document.getElementById('discussMessages');
    const div = document.createElement('div');
    div.className = 'discuss-msg ' + role;
    div.innerHTML = text;  // 纯文本消息直接显示，AI 消息后面会重新渲染
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

// ===== 下一题 =====
async function nextProblem() {
    // 清除追问会话
    if (currentProblem) {
        try {
            await fetch('/math/api/discuss/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ problem_id: currentProblem.id }),
            });
        } catch(e) {}
    }

    // 重置 UI
    document.getElementById('judgeArea').style.display = 'none';
    document.getElementById('discussArea').style.display = 'none';
    document.getElementById('discussMessages').innerHTML =
        '<div style="text-align:center;color:var(--text-secondary);padding:20px;">对这道题有什么疑问？可以自由追问。</div>';

    loadNextProblem();
}

// ===== UI 辅助 =====
function showLoading(msg) {
    const el = document.getElementById('loadingScreen');
    el.style.display = 'block';
    el.innerHTML = '<p style="color:var(--text-secondary);">' + (msg || '加载中...') + '</p>';
}

function hideLoading() {
    document.getElementById('loadingScreen').style.display = 'none';
}
