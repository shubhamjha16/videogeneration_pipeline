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

async function pollJobs() {
    try {
        const headers = {};
        const apiKey = localStorage.getItem('FACTORY_API_KEY');
        if (apiKey) headers['X-API-Key'] = apiKey;
        
        const response = await fetch(`${API_BASE}/jobs`, { headers });
        if (response.status === 403) {
            console.error("Dashboard Polling Error: 403 Forbidden. Set localStorage.setItem('FACTORY_API_KEY', 'your_key') in console.");
            return;
        }
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        const jobs = await response.json();
        
        // Find the most interesting job (either building or just finished)
        const jobIds = Object.keys(jobs).sort((a,b) => b - a);
        if (jobIds.length === 0) return renderEmpty();

        const latestJob = jobs[jobIds[0]];
        activeJobId = jobIds[0];

        if (latestJob.status === "completed") {
            renderPlayer(latestJob);
        } else {
            renderBuilding(latestJob);
        }

        // Also update the telemetry console
        updateTelemetry(latestJob);
        
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
    if (lastRenderedStatus === "building" && activeJobId === job.job_id) {
        // Just update reasoning text to avoid flicker
        const rBox = document.querySelector('.building-reasoning');
        if (rBox && job.logs && job.logs.length > 0) {
            rBox.innerText = job.logs[job.logs.length - 1].msg;
        }
        return;
    }
    lastRenderedStatus = "building";

    const lastLog = job.logs && job.logs.length > 0 ? job.logs[job.logs.length - 1] : {node: "INGESTION", msg: "Initialized."};
    
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
                ${job.topic.toUpperCase()}
            </div>
        </div>
        <div class="hero-body">
            <h2 class="building-title">Building: ${job.topic}</h2>
            <div class="building-reasoning">
                ${lastLog.msg}
            </div>
            <div class="progress-belt">
                <div class="progress-stats">
                    <span>${lastLog.node}</span>
                    <span>Processing...</span>
                </div>
                <div class="progress-container" style="margin-bottom: 0;">
                    <div class="progress-bar" style="width: 70%; animation: pulse 2s infinite;"></div>
                </div>
            </div>
        </div>
    `;
    lucide.createIcons();
}

function renderPlayer(job) {
    if (lastRenderedStatus === "completed") return; 
    lastRenderedStatus = "completed";

    masterclassHero.innerHTML = `
        <div class="hero-header">
            <div class="avatar-group">
                <img src="https://ui-avatars.com/api/?name=Tony+AI&background=3B82F6&color=fff" alt="Tony AI">
                <div>
                    <span style="display: block; font-weight: 700; font-size: 0.9rem;">Tony AI Teacher</span>
                    <span style="font-size: 0.7rem; color: var(--text-muted);">${job.topic} | MC Done</span>
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
                    <h3 style="font-size: 1.1rem; font-weight: 700;">${job.topic}</h3>
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
