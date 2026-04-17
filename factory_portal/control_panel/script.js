// Initialize Lucide Icons
lucide.createIcons();

// Tab Switching Logic
const navBtns = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === (tabId + 'Tab')) {
                content.classList.add('active');
            }
        });
    });
});

// Tony Match Masterclass Box Logic
const masterclassHero = document.getElementById('masterclassHero');

// Industrial URL Detection: Priority 1: Current Origin, Priority 2: localhost fallback
const API_BASE = window.location.origin;

let lastRenderedStatus = null;
let activeJobId = null;

async function deleteJob(jobId) {
    if (!confirm('Delete this masterclass?')) return;
    try {
        const headers = { 'Content-Type': 'application/json' };
        const apiKey = localStorage.getItem('FACTORY_API_KEY');
        if (apiKey) headers['X-API-Key'] = apiKey;
        
        await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE', headers });
        pollJobs(); // Refresh vault
    } catch (err) {
        console.error('Delete failed:', err);
    }
}

async function pollJobs() {
    try {
        const headers = {};
        const apiKey = localStorage.getItem('FACTORY_API_KEY');
        if (apiKey) headers['X-API-Key'] = apiKey;
        
        const response = await fetch(`${API_BASE}/jobs`, { headers });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        const jobs = await response.json();
        
        const jobList = Object.values(jobs);
        if (jobList.length === 0) return renderEmpty();

        // Always pick the most recently updated job
        const latestJob = jobList.sort((a, b) => 
            new Date(b.updated_at) - new Date(a.updated_at)
        )[0];

        // Re-render if job ID changed OR status changed
        const jobChanged = activeJobId !== latestJob.job_id;
        const statusChanged = lastRenderedStatus !== latestJob.status;

        activeJobId = latestJob.job_id;

        if (latestJob.status === "completed") {
            if (jobChanged || statusChanged) {
                lastRenderedStatus = "completed";
                renderPlayer(latestJob);
            }
        } else {
            // Always update building state
            lastRenderedStatus = "building";
            renderBuilding(latestJob);
        }

        updateTelemetry(latestJob);
        updateVault(jobs);
        
    } catch (err) {
        console.error("Dashboard Polling Error:", err);
        masterclassHero.innerHTML = `
            <div class="empty-state">
                <i data-lucide="alert-triangle" style="color: #ff4444"></i>
                <h3 style="color: #ff4444">Connection Error</h3>
                <p>Lost contact with Factory Backend. Retrying...</p>
            </div>
        `;
        lucide.createIcons();
    }
}

function renderEmpty() {
    masterclassHero.innerHTML = `
        <div class="empty-state">
            <i data-lucide="video"></i>
            <h3>Ready for Production</h3>
            <p>Waiting for a click from Tony AI to start generating your masterclass.</p>
        </div>
    `;
    lucide.createIcons();
    lastRenderedStatus = "empty";
}

function renderBuilding(job) {
    // Always re-render
    const lastLog = job.logs && job.logs.length > 0 
        ? job.logs[job.logs.length - 1] 
        : {node: "INITIALIZING", msg: "Job queued."};
    
    masterclassHero.innerHTML = `
        <div class="hero-header">
            <div class="avatar-group">
                <img src="https://ui-avatars.com/api/?name=Tony+AI&background=3B82F6&color=fff" alt="Tony AI">
                <div>
                    <span style="display: block; font-weight: 700; font-size: 0.9rem;">Tony AI Teacher</span>
                    <span style="font-size: 0.7rem; color: var(--text-muted);">Industrial Video Generation Active</span>
                </div>
            </div>
            <div style="background: rgba(59, 130, 246, 0.1); color: var(--primary); padding: 4px 12px; border-radius: 8px; font-weight: 800; font-size: 0.7rem;">
                ${(job.topic || 'Unknown').toUpperCase()}
            </div>
        </div>
        <div class="hero-body">
            <h2 class="building-title">Building: ${job.topic || 'Unknown'}</h2>
            <div class="building-reasoning">${lastLog.msg}</div>
            <div class="progress-belt">
                <div class="progress-stats">
                    <span>${lastLog.node || 'PROCESSING'}</span>
                    <span>Processing...</span>
                </div>
                <div class="progress-container" style="margin-bottom: 0;">
                    <div class="progress-bar" style="width: ${job.progress || 10}%; transition: width 0.5s ease;"></div>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

function renderPlayer(job) {
    lastRenderedStatus = "completed";

    masterclassHero.innerHTML = `
        <div class="hero-header">
            <div class="avatar-group">
                <img src="https://ui-avatars.com/api/?name=Tony+AI&background=3B82F6&color=fff" alt="Tony AI">
                <div>
                    <span style="display: block; font-weight: 700; font-size: 0.9rem;">Tony AI Teacher</span>
                    <span style="font-size: 0.7rem; color: var(--text-muted);">${job.topic || 'Unknown'} | MC Done</span>
                </div>
            </div>
            <div style="background: rgba(16, 185, 129, 0.1); color: var(--success); padding: 4px 12px; border-radius: 8px; font-weight: 800; font-size: 0.7rem;">
                COMPLETED
            </div>
        </div>
        <div class="hero-body">
            <div class="hero-player-container">
                <video controls autoplay>
                    <source src="${job.video_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
            <div style="margin-top: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="font-size: 1.1rem; font-weight: 700;">${job.topic || 'Unknown'}</h3>
                    <p style="font-size: 0.8rem; color: var(--text-muted);">Video Masterclass generated successfully.</p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-primary" onclick="window.open('${job.video_url}', '_blank')">
                        <i data-lucide="download"></i> Download
                    </button>
                    <button class="btn btn-secondary" onclick="location.reload()" style="background: #F1F5F9; border: 1px solid #E2E8F0; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 600;">
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

const consoleOutput = document.querySelector('.console-output');
function updateTelemetry(job) {
    if (!job.logs) return;
    
    // Simple log deduplication and scrolling
    const lastLogs = job.logs.slice(-5);
    lastLogs.forEach(log => {
        const time = new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit' });
        const logId = `log-${job.job_id}-${log.node}-${log.msg.substring(0,10)}`;
        if (document.getElementById(logId)) return;

        const line = document.createElement('div');
        line.id = logId;
        line.className = 'log-line';
        line.innerHTML = `<span class="timestamp">[${time}]</span> <span class="${log.type}">${log.node}:</span> ${log.msg}`;
        
        consoleOutput.appendChild(line);
    });
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function updateVault(jobs) {
    const vaultGrid = document.querySelector('.vault-grid');
    if (!vaultGrid) return;

    // Get only completed jobs, sorted newest first
    const completed = Object.values(jobs)
        .filter(j => j.status === 'completed')
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    // Build cards HTML
    const colors = [
        'linear-gradient(135deg, #3B82F6, #1E40AF)',
        'linear-gradient(135deg, #EF4444, #991B1B)',
        'linear-gradient(135deg, #10B981, #065F46)',
        'linear-gradient(135deg, #8B5CF6, #5B21B6)',
        'linear-gradient(135deg, #F59E0B, #92400E)',
    ];

    const cards = completed.map((job, i) => {
        const color = colors[i % colors.length];
        const mode = (job.render_mode || 'auto').toUpperCase();
        const date = new Date(job.created_at).toLocaleDateString();
        const videoUrl = job.video_url || '';

        return `
        <div class="vault-card glass">
            <div class="thumbnail" style="background: ${color};">
                <div class="overlay"><i data-lucide="play-circle"></i></div>
                <span class="duration">${mode}</span>
            </div>
            <div class="card-body">
                <h4>${job.topic || 'Unknown'}</h4>
                <span class="meta">${date}</span>
                <div class="card-actions">
                    ${videoUrl ? `<button class="btn btn-primary" onclick="window.open('${videoUrl}', '_blank')">
                        <i data-lucide="download"></i> Download
                    </button>` : ''}
                    <button class="btn btn-secondary" onclick="deleteJob('${job.job_id}')" style="background: rgba(239,68,68,0.1); color: #EF4444; border: 1px solid #EF4444;">
                        <i data-lucide="trash-2"></i>
                    </button>
                </div>
            </div>
        </div>`;
    }).join('');

    // Add the "add new" card at the end
    const addCard = `
        <div class="vault-card glass empty" id="vaultBulkLink">
            <div class="add-prompt">
                <i data-lucide="plus-circle"></i>
                <p>Ingest New Curriculum Chapter</p>
            </div>
        </div>`;

    vaultGrid.innerHTML = cards + addCard;
    lucide.createIcons();

    // Update stats
    const statVideos = document.querySelector('.vault-stats .stat:first-child');
    if (statVideos) statVideos.innerHTML = `<i data-lucide="video"></i> ${completed.length} Masterclasses`;
    lucide.createIcons();
}

// Start Polling
setInterval(pollJobs, 2000);
pollJobs();

// Settings Modal Logic
const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const factoryApiKeyInput = document.getElementById('factoryApiKeyInput');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const closeButtons = document.querySelectorAll('.close-modal');

if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
        settingsModal.classList.add('active');
        factoryApiKeyInput.value = localStorage.getItem('FACTORY_API_KEY') || '';
    });
}

closeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        settingsModal.classList.remove('active');
        const bulkModal = document.getElementById('bulkModal');
        if (bulkModal) bulkModal.classList.remove('active');
    });
});

if (saveSettingsBtn) {
    saveSettingsBtn.addEventListener('click', () => {
        const key = factoryApiKeyInput.value.trim();
        if (key) {
            localStorage.setItem('FACTORY_API_KEY', key);
            settingsModal.classList.remove('active');
            pollJobs(); // Re-trigger poll with new key
        } else {
            alert('Please enter a valid API key.');
        }
    });
}

// Bulk Ingest Modal Logic
const bulkIngestBtn = document.getElementById('bulkIngestBtn');
const bulkModal = document.getElementById('bulkModal');
if (bulkIngestBtn) {
    bulkIngestBtn.addEventListener('click', () => {
        bulkModal.classList.add('active');
    });
}

// System Halt Sequence
const haltBtn = document.querySelector('.btn-danger');
if (haltBtn) {
    haltBtn.addEventListener('click', () => {
        if (confirm('CRITICAL: SIGTERM ALL NODES? This will kill all active render processes.')) {
            document.body.style.filter = 'grayscale(1) brightness(0.4)';
            document.body.style.pointerEvents = 'none';
        }
    });
}
