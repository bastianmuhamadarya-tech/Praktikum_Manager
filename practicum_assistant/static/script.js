/* =========================================================
   script.js - fungsi bersama untuk semua halaman
   ========================================================= */

// State bersama
let coursesData = [];
let activeCourseId = null;

// Nama halaman aktif ("tracker" atau "tools"), diisi dari <body data-page="...">
const PAGE = document.body.dataset.page || '';


/* ---------- Helper umum ---------- */

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/* ---------- Modal kustom (pengganti prompt/confirm/alert) ---------- */

function showModal(opts) {
    return new Promise(resolve => {
        const modal = document.getElementById('app-modal');
        const input = document.getElementById('modal-input');
        const okBtn = document.getElementById('modal-ok');
        const cancelBtn = document.getElementById('modal-cancel');

        document.getElementById('modal-title').innerText = opts.title || '';
        document.getElementById('modal-message').innerText = opts.message || '';
        input.classList.toggle('hidden', !opts.withInput);
        input.value = opts.defaultValue || '';
        okBtn.innerText = opts.okText || 'OK';
        okBtn.className = 'px-4 py-2 text-sm font-semibold text-white rounded-xl ' +
            (opts.danger ? 'bg-rose-600 hover:bg-rose-700' : 'bg-brand-600 hover:bg-brand-700');
        cancelBtn.classList.toggle('hidden', !!opts.hideCancel);

        function close(result) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            okBtn.onclick = null;
            cancelBtn.onclick = null;
            input.onkeydown = null;
            resolve(result);
        }

        okBtn.onclick = () => close(opts.withInput ? input.value : true);
        cancelBtn.onclick = () => close(opts.withInput ? null : false);
        input.onkeydown = (e) => {
            if (e.key === 'Enter') okBtn.click();
            if (e.key === 'Escape') cancelBtn.click();
        };

        modal.classList.remove('hidden');
        modal.classList.add('flex');
        if (opts.withInput) setTimeout(() => { input.focus(); input.select(); }, 50);
    });
}

function showAlert(title, message) {
    return showModal({ title, message, hideCancel: true });
}

/* ---------- Komunikasi dengan server Flask ---------- */

async function api(method, url, body) {
    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: body !== undefined ? JSON.stringify(body) : undefined
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            await showAlert('Terjadi Kesalahan', data.error || 'Permintaan ke server gagal.');
            return null;
        }
        return data;
    } catch (e) {
        await showAlert('Server Tidak Terjangkau', 'Pastikan app.py masih berjalan di terminal.');
        return null;
    }
}

/* ---------- Sidebar & tema ---------- */

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('-translate-x-full');
    document.getElementById('sidebar-overlay').classList.toggle('hidden');
}

function closeSidebarOnMobile() {
    if (window.innerWidth < 768) {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar.classList.contains('-translate-x-full')) toggleSidebar();
    }
}

function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle('dark');
    try { localStorage.setItem('theme', isDark ? 'dark' : 'light'); } catch (e) {}
}

function highlightActiveNav() {
    if (PAGE !== 'tools') return;
    const tab = new URLSearchParams(location.search).get('tab') === 'appendix' ? 'appendix' : 'calculator';
    const el = document.getElementById('nav-' + tab);
    if (el) {
        el.classList.add('bg-brand-50', 'text-brand-600', 'dark:bg-slate-700/50', 'dark:text-brand-400');
    }
}

/* ---------- Data mata kuliah ---------- */

function calculateCourseProgress(course) {
    let total = 0;
    let done = 0;
    if (!course || !course.modules) return 0;

    course.modules.forEach(mod => {
        (mod.tasks || []).forEach(task => {
            total++;
            if (task.done) done++;
        });
    });

    return total === 0 ? 0 : Math.round((done / total) * 100);
}

function pickInitialCourse() {
    const fromUrl = parseInt(new URLSearchParams(location.search).get('course'), 10);
    if (coursesData.some(c => c.id === fromUrl)) return fromUrl;
    return coursesData.length ? coursesData[0].id : null;
}

// Dipanggil setiap kali server mengirim data terbaru
function setData(data) {
    coursesData = data.courses || [];
    if (!coursesData.some(c => c.id === activeCourseId)) {
        activeCourseId = pickInitialCourse();
    }
    renderSidebarCourses();
    if (typeof onDataChanged === 'function') onDataChanged();
}

function openCourse(courseId) {
    if (PAGE === 'tracker' && typeof selectCourse === 'function') {
        selectCourse(courseId);
    } else {
        location.href = '/?course=' + courseId;
    }
}

function renderSidebarCourses() {
    const container = document.getElementById('courses-list');
    if (!container) return;
    container.innerHTML = '';

    coursesData.forEach(course => {
        const isSelected = activeCourseId === course.id;
        const btn = document.createElement('button');
        btn.onclick = () => openCourse(course.id);
        btn.className = 'w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ' + (
            isSelected
                ? 'bg-brand-50 text-brand-600 dark:bg-slate-700/50 dark:text-brand-400 font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/50'
        );

        btn.innerHTML = `
            <span class="flex items-center gap-3 truncate">
                <i class="fa-solid ${escapeHtml(course.icon || 'fa-book')} ${escapeHtml(course.color || 'text-purple-500')}"></i>
                ${escapeHtml(course.name)}
            </span>
            <span class="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 px-2 py-0.5 rounded-full font-bold ml-2">${calculateCourseProgress(course)}%</span>
        `;
        container.appendChild(btn);
    });
}

async function promptAddCourse() {
    const name = await showModal({
        title: 'Tambah Mata Kuliah Praktikum',
        message: 'Masukkan nama mata kuliah praktikum baru:',
        withInput: true,
        okText: 'Tambah'
    });
    if (!name || !name.trim()) return;

    const data = await api('POST', '/api/courses', { name: name.trim() });
    if (!data) return;

    activeCourseId = data.created_id;
    setData(data);
    if (PAGE !== 'tracker') openCourse(data.created_id);
    else closeSidebarOnMobile();
}

async function resetAllData() {
    const ok = await showModal({
        title: 'Reset Semua Progress',
        message: 'Apakah kamu yakin ingin mereset semua data dan progres praktikum ke awal? Lampiran yang tersimpan di browser juga ikut terhapus.',
        okText: 'Reset',
        danger: true
    });
    if (!ok) return;

    const data = await api('POST', '/api/reset');
    if (!data) return;

    try { localStorage.removeItem('lab_manager_appendix'); } catch (e) {}
    location.href = '/';
}

/* ---------- Mulai ---------- */

document.addEventListener('DOMContentLoaded', async () => {
    highlightActiveNav();
    const data = await api('GET', '/api/courses');
    if (data) setData(data);
});
