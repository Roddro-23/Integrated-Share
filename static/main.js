(function () {
    const fileListContainer = document.getElementById('fileList');
    const fileCountSpan     = document.getElementById('fileCount');
    const uploadProgress    = document.getElementById('uploadProgress');
    const progressFill      = document.getElementById('progressFill');
    const progressText      = document.getElementById('progressText');
    const clearAllBtn       = document.getElementById('clearAllBtn');
    const fileInput         = document.getElementById('fileInput');
    const dropZone          = document.getElementById('dropZone');
    const dragOverlay       = document.getElementById('dragOverlay');
    const searchInput       = document.getElementById('searchInput');

    const API = window.location.origin;
    let allFiles      = [];
    let currentFilter = 'mine';
    let searchQuery   = '';
    let shareTargetId = null;

    async function apiFetch(url, options = {}) {
        const res = await fetch(url, options);
        if (res.status === 401) { window.location.href = '/login'; return null; }
        return res;
    }

    window.doLogout = async function () {
        try { await fetch(`${API}/api/auth/logout`, { method: 'POST' }); } catch {}
        window.location.href = '/login';
    };

    async function loadUserInfo() {
        try {
            const res = await apiFetch(`${API}/api/auth/me`);
            if (!res) return;
            const user = await res.json();

            const avatar = document.getElementById('userAvatar');
            if (avatar) avatar.textContent = (user.username || '?')[0].toUpperCase();

            const pct      = user.storage_limit > 0
                ? Math.min(100, Math.round((user.storage_used / user.storage_limit) * 100)) : 0;
            const usedStr  = formatSize(user.storage_used);
            const limitStr = formatSize(user.storage_limit);

            const topFill = document.getElementById('storageFill');
            const topText = document.getElementById('storageText');
            const sideFill = document.getElementById('sideStorageFill');
            const sideText = document.getElementById('sideStorageText');

            if (topFill)  topFill.style.width    = pct + '%';
            if (topText)  topText.textContent     = usedStr + ' / ' + limitStr;
            if (sideFill) sideFill.style.width    = pct + '%';
            if (sideText) sideText.textContent    = usedStr + ' of ' + limitStr;

            const adminBtn = document.getElementById('adminLink');
            if (adminBtn && user.is_admin) adminBtn.style.display = 'flex';
        } catch {}
    }

    async function loadFiles() {
        try {
            const res = await apiFetch(`${API}/api/files`);
            if (!res) return;
            allFiles = await res.json();
            renderFiles();
        } catch {
            showToast('Failed to load files', 'error');
        }
    }

    function renderFiles() {
        const filtered = allFiles.filter(f => {
            const matchFilter = currentFilter === 'mine'   ? f.owner === ''
                              : currentFilter === 'shared' ? f.owner !== ''
                              : true;
            const matchSearch = !searchQuery || f.original_name.toLowerCase().includes(searchQuery);
            return matchFilter && matchSearch;
        });

        fileListContainer.innerHTML = '';

        const title = document.getElementById('sectionTitle');
        if (title) title.textContent = currentFilter === 'shared' ? 'Shared with me' : 'My Files';

        if (!filtered.length) {
            showEmpty();
        } else {
            if (dropZone) dropZone.style.display = 'none';
            filtered.forEach(f => fileListContainer.appendChild(makeFileCard(f)));
        }
        updateCount(filtered.length);
    }

    function makeFileCard(f) {
        const name      = f.original_name || 'Unknown';
        const ext       = name.split('.').pop().toLowerCase();
        const typeClass = cardTypeClass(ext);

        const card       = document.createElement('div');
        card.className   = `file-card ${typeClass}`;
        card.dataset.id  = f.id;
        card.innerHTML   = `
            <div class="file-card-header">
                <i class="fas ${fileIcon(name)}"></i>
            </div>
            <div class="file-card-actions">
                <button class="card-btn btn-share" title="Share"><i class="fas fa-share-alt"></i></button>
                <button class="card-btn btn-dl"    title="Download"><i class="fas fa-download"></i></button>
                <button class="card-btn btn-del"   title="Delete"><i class="fas fa-trash"></i></button>
            </div>
            <div class="file-card-body">
                <div class="file-card-name" title="${name}">${name}</div>
                <div class="file-card-meta">${formatSize(f.size)} &middot; ${f.date || ''}</div>
                ${f.owner ? `<div class="file-card-owner"><i class="fas fa-user"></i> ${f.owner}</div>` : ''}
            </div>`;

        card.querySelector('.btn-share').onclick = e => { e.stopPropagation(); openShareModal(f.id, name); };
        card.querySelector('.btn-dl').onclick    = e => { e.stopPropagation(); window.location.href = `${API}/api/download/${f.stored_name}`; };
        card.querySelector('.btn-del').onclick   = e => { e.stopPropagation(); deleteFile(f.id, card); };
        card.onclick = () => window.location.href = `${API}/api/download/${f.stored_name}`;
        return card;
    }

    async function uploadFiles(files) {
        if (!files || !files.length) return;
        const fd = new FormData();
        Array.from(files).forEach(f => fd.append('files', f));

        uploadProgress.style.display = 'block';
        progressFill.style.width     = '10%';
        progressText.textContent     = `Uploading ${files.length} file(s)…`;

        try {
            const res = await apiFetch(`${API}/api/upload`, { method: 'POST', body: fd });
            if (!res) return;
            const data = await res.json();

            if (res.ok && data.success) {
                progressFill.style.width = '100%';
                progressText.textContent = `Done — ${data.files.length} file(s) uploaded.`;
                await loadFiles();
                await loadUserInfo();
                if (data.warning) showToast(data.warning, 'warning');
                setTimeout(() => { uploadProgress.style.display = 'none'; progressFill.style.width = '0%'; }, 2500);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (err) {
            progressText.textContent = 'Upload failed';
            progressFill.style.width = '0%';
            showToast(err.message || 'Upload failed', 'error');
            setTimeout(() => { uploadProgress.style.display = 'none'; }, 3500);
        }
    }

    async function deleteFile(fileId, el) {
        if (!confirm('Delete this file?')) return;
        try {
            const res  = await apiFetch(`${API}/api/delete/${fileId}`, { method: 'DELETE' });
            if (!res) return;
            const data = await res.json();
            if (data.success) {
                el.remove();
                allFiles = allFiles.filter(f => f.id !== fileId);
                updateCount(fileListContainer.querySelectorAll('.file-card').length);
                if (!fileListContainer.querySelector('.file-card')) showEmpty();
                await loadUserInfo();
                showToast('File deleted', 'success');
            } else {
                showToast(data.error || 'Delete failed', 'error');
            }
        } catch {
            showToast('Delete failed', 'error');
        }
    }

    async function clearAll() {
        if (!confirm('Delete ALL your files? This cannot be undone.')) return;
        try {
            const res  = await apiFetch(`${API}/api/clear`, { method: 'POST' });
            if (!res) return;
            const data = await res.json();
            if (data.success) {
                await loadFiles();
                await loadUserInfo();
                showToast('All files cleared', 'success');
            } else {
                showToast(data.error || 'Failed to clear', 'error');
            }
        } catch {
            showToast('Failed to clear files', 'error');
        }
    }

    function openShareModal(fileId, fileName) {
        shareTargetId = fileId;
        const modal    = document.getElementById('shareModal');
        const nameEl   = document.getElementById('shareModalFileName');
        const inputEl  = document.getElementById('shareUsername');
        const feedback = document.getElementById('shareFeedback');
        if (nameEl)   nameEl.textContent = fileName;
        if (inputEl)  inputEl.value      = '';
        if (feedback) { feedback.className = 'modal-feedback'; feedback.textContent = ''; }
        modal.classList.add('open');
    }

    window.closeShareModal = function () {
        document.getElementById('shareModal').classList.remove('open');
        shareTargetId = null;
    };

    window.generateShareLink = async function () {
        if (!shareTargetId) return;
        try {
            const res  = await apiFetch(`${API}/api/share/link/${shareTargetId}`, { method: 'POST' });
            if (!res) return;
            const data = await res.json();
            if (data.success) {
                try {
                    await navigator.clipboard.writeText(data.share_link);
                    modalFeedback('Link copied! Valid for 7 days.', 'success');
                } catch {
                    modalFeedback('Link: ' + data.share_link, 'success');
                }
            } else {
                modalFeedback(data.error || 'Failed to generate link', 'error');
            }
        } catch {
            modalFeedback('Connection error', 'error');
        }
    };

    window.shareToUser = async function () {
        const inputEl  = document.getElementById('shareUsername');
        const username = inputEl ? inputEl.value.trim() : '';
        if (!username)      return modalFeedback('Enter a username', 'error');
        if (!shareTargetId) return;
        try {
            const res = await apiFetch(`${API}/api/share/user/${shareTargetId}`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ username }),
            });
            if (!res) return;
            const data = await res.json();
            if (data.success) {
                modalFeedback(data.message, 'success');
                if (inputEl) inputEl.value = '';
            } else {
                modalFeedback(data.error || 'Failed to share', 'error');
            }
        } catch {
            modalFeedback('Connection error', 'error');
        }
    };

    function modalFeedback(msg, type) {
        const el = document.getElementById('shareFeedback');
        if (!el) return;
        el.textContent = msg;
        el.className   = `modal-feedback ${type}`;
    }

    document.getElementById('shareModal').addEventListener('click', function (e) {
        if (e.target === this) window.closeShareModal();
    });

    function showEmpty() {
        const d = document.createElement('div');
        d.className = 'empty-files';
        d.innerHTML = `
            <i class="fas fa-folder-open"></i>
            <h3>${currentFilter === 'shared' ? 'Nothing shared with you yet' : 'No files here yet'}</h3>
            <p>${currentFilter === 'shared' ? 'Files shared with you will appear here' : 'Upload files using the button on the left or drop them anywhere'}</p>`;
        fileListContainer.appendChild(d);
        if (dropZone && currentFilter === 'mine') dropZone.style.display = '';
    }

    function updateCount(n) {
        if (fileCountSpan) fileCountSpan.textContent = n + (n === 1 ? ' item' : ' items');
    }

    function showToast(msg, type) {
        const colors = { error: '#B31412', success: '#137333', warning: '#874D00' };
        const bgs    = { error: '#FCE8E6', success: '#E6F4EA', warning: '#FEF7E0' };
        const t = document.createElement('div');
        t.style.cssText = `
            position:fixed; bottom:5.5rem; right:1.5rem;
            background:${bgs[type] || '#F8F9FA'};
            color:${colors[type] || '#202124'};
            padding:.75rem 1.1rem; border-radius:.75rem;
            font-size:.85rem; font-weight:500;
            box-shadow:0 4px 16px rgba(0,0,0,.12);
            z-index:2000; max-width:320px;
            border-left:3px solid ${colors[type] || '#9AA0A6'};`;
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 4000);
    }

    function formatSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function fileIcon(name) {
        const ext = name.split('.').pop().toLowerCase();
        if (['jpg','jpeg','png','gif','svg','webp','bmp'].includes(ext))              return 'fa-file-image';
        if (['pdf'].includes(ext))                                                    return 'fa-file-pdf';
        if (['doc','docx','txt','rtf','odt','md'].includes(ext))                      return 'fa-file-lines';
        if (['xls','xlsx','csv'].includes(ext))                                       return 'fa-file-excel';
        if (['ppt','pptx'].includes(ext))                                             return 'fa-file-powerpoint';
        if (['zip','rar','7z','tar','gz','bz2'].includes(ext))                        return 'fa-file-zipper';
        if (['mp3','wav','ogg','flac','aac'].includes(ext))                           return 'fa-file-audio';
        if (['mp4','avi','mov','mkv','webm'].includes(ext))                           return 'fa-file-video';
        if (['c','cpp','h','py','java','js','ts','go','rs','rb','cs',
             'html','css','json','yaml','toml','sh','bash','sql'].includes(ext))      return 'fa-file-code';
        return 'fa-file';
    }

    function cardTypeClass(ext) {
        if (['jpg','jpeg','png','gif','svg','webp','bmp'].includes(ext))              return 'type-image';
        if (['pdf'].includes(ext))                                                    return 'type-pdf';
        if (['doc','docx','txt','rtf','odt','md'].includes(ext))                      return 'type-doc';
        if (['xls','xlsx','csv'].includes(ext))                                       return 'type-data';
        if (['zip','rar','7z','tar','gz','bz2'].includes(ext))                        return 'type-archive';
        if (['mp3','wav','ogg','flac','aac','mp4','avi','mov','mkv','webm'].includes(ext)) return 'type-media';
        return 'type-code';
    }

    // Drag and drop on the whole page
    let dragCount = 0;
    document.addEventListener('dragenter', e => {
        if (e.dataTransfer && e.dataTransfer.types.includes('Files')) {
            e.preventDefault();
            dragCount++;
            if (dragOverlay) dragOverlay.classList.add('active');
        }
    });
    document.addEventListener('dragleave', () => {
        dragCount = Math.max(0, dragCount - 1);
        if (dragCount === 0 && dragOverlay) dragOverlay.classList.remove('active');
    });
    document.addEventListener('dragover', e => e.preventDefault());
    document.addEventListener('drop', e => {
        e.preventDefault();
        dragCount = 0;
        if (dragOverlay) dragOverlay.classList.remove('active');
        if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
    });

    if (dropZone)       dropZone.addEventListener('click', () => fileInput.click());

    const sidebarNewBtn = document.getElementById('sidebarNewBtn');
    if (sidebarNewBtn)  sidebarNewBtn.addEventListener('click', () => fileInput.click());

    if (fileInput) {
        fileInput.addEventListener('change', e => {
            if (e.target.files.length) uploadFiles(e.target.files);
            fileInput.value = '';
        });
    }

    if (clearAllBtn) clearAllBtn.addEventListener('click', clearAll);

    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', e => {
            e.preventDefault();
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            currentFilter = item.dataset.filter;
            renderFiles();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', e => {
            searchQuery = e.target.value.toLowerCase().trim();
            renderFiles();
        });
    }

    loadUserInfo();
    loadFiles();
})();
