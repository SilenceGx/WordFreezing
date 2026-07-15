/**
 * WordFreezing - 全局 JavaScript
 */

// ===== 通用工具 =====

/** 格式化日期为 YYYY-MM-DD */
function formatDate(date) {
    return date.toISOString().slice(0, 10);
}

/** 获取当前日期 */
function today() {
    return formatDate(new Date());
}

/** 显示 toast 消息 */
function showToast(message, type) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== 防抖 =====
function debounce(fn, delay = 300) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// ===== AJAX 助手 =====
async function apiFetch(url, options = {}) {
    try {
        const resp = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });
        return await resp.json();
    } catch (err) {
        console.error('API Error:', err);
        return { success: false, message: '网络错误' };
    }
}

// ===== 页面加载完成后 =====
document.addEventListener('DOMContentLoaded', function () {
    // 自动聚焦输入框
    const autoFocus = document.querySelector('[autofocus]');
    if (autoFocus) autoFocus.focus();

    // 添加 Toast 样式
    const style = document.createElement('style');
    style.textContent = `
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: var(--text);
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 0.9rem;
            z-index: 999;
            opacity: 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
    `;
    document.head.appendChild(style);
});
