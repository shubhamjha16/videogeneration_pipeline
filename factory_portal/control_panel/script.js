// Initialize Lucide Icons
lucide.createIcons();

// Industrial URL Detection: Use current window host for smooth deployment in staging/local
const API_BASE = window.location.origin;

// Application State
let inspectedJobId = null;
let activePollingInterval = null;
let globalJobsStore = {};

// Get Request Headers with optional API key
function getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const apiKey = localStorage.getItem('FACTORY_API_KEY');
    if (apiKey) headers['X-API-Key'] = apiKey;
    return headers;
}

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
    setupTabSwitching();
    setupModals();
    setupDispatcher();
    setupSystemHalt();
    
    // Start Polling
    pollJobs();
    activePollingInterval = setInterval(pollJobs, 2000);
});

// Tab Switching Logic
function setupTabSwitching() {
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

    // Vault chapter ingest link opens dispatcher modal
    document.addEventListener('click', (e) => {
        const link = e.target.closest('#vaultBulkLink');
        if (link) {
            const dispatchModal = document.getElementById('dispatchModal');
            if (dispatchModal) dispatchModal.classList.add('active');
        }
    });
}

// Modal Toggle Logic
function setupModals() {
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
            document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
        });
    });

    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            const key = factoryApiKeyInput.value.trim();
            if (key) {
                localStorage.setItem('FACTORY_API_KEY', key);
            } else {
                localStorage.removeItem('FACTORY_API_KEY');
            }
            settingsModal.classList.remove('active');
            pollJobs(); // Refresh immediately
        });
    }

    // Video Player Modal Close Logic
    const closePlayerModalBtn = document.getElementById('closePlayerModalBtn');
    const videoPlayerModal = document.getElementById('videoPlayerModal');
    const playerModalVideo = document.getElementById('playerModalVideo');

    if (closePlayerModalBtn && videoPlayerModal && playerModalVideo) {
        closePlayerModalBtn.addEventListener('click', () => {
            playerModalVideo.pause();
            playerModalVideo.src = '';
            videoPlayerModal.classList.remove('active');
        });
    }
}

// Ingest Contextfacts / Dispatch Logic
function setupDispatcher() {
    const newMasterclassBtn = document.getElementById('newMasterclassBtn');
    const dispatchModal = document.getElementById('dispatchModal');
    const cancelDispatchBtn = document.getElementById('cancelDispatchBtn');
    const closeDispatchBtn = document.getElementById('closeDispatchBtn');
    const toggleContextBtn = document.getElementById('toggleContextBtn');
    const customLessonContent = document.getElementById('customLessonContent');
    const triggerProductionBtn = document.getElementById('triggerProductionBtn');

    if (newMasterclassBtn && dispatchModal) {
        newMasterclassBtn.addEventListener('click', () => {
            dispatchModal.classList.add('active');
        });
    }

    const hideDispatch = () => {
        dispatchModal.classList.remove('active');
        // Reset fields
        document.getElementById('customTopicInput').value = '';
        customLessonContent.value = '';
        customLessonContent.style.display = 'none';
        toggleContextBtn.innerHTML = '<i data-lucide="plus" style="width: 12px; height: 12px;"></i> Add Context';
        lucide.createIcons();
    };

    if (cancelDispatchBtn) cancelDispatchBtn.addEventListener('click', hideDispatch);
    if (closeDispatchBtn) closeDispatchBtn.addEventListener('click', hideDispatch);

    if (toggleContextBtn && customLessonContent) {
        toggleContextBtn.addEventListener('click', () => {
            if (customLessonContent.style.display === 'none' || !customLessonContent.style.display) {
                customLessonContent.style.display = 'block';
                toggleContextBtn.innerHTML = '<i data-lucide="minus" style="width: 12px; height: 12px;"></i> Hide Context';
            } else {
                customLessonContent.style.display = 'none';
                toggleContextBtn.innerHTML = '<i data-lucide="plus" style="width: 12px; height: 12px;"></i> Add Context';
            }
            lucide.createIcons();
        });
    }

    if (triggerProductionBtn) {
        triggerProductionBtn.addEventListener('click', async () => {
            const topic = document.getElementById('customTopicInput').value.trim();
            let context = customLessonContent.value.trim();
            const renderMode = document.getElementById('dispatchRenderMode').value;
            const withAvatar = document.getElementById('withAvatarCheckbox').checked;
            const useElevenlabs = document.getElementById('useElevenlabsCheckbox').checked;

            if (!topic) {
                alert('Topic is required to trigger a dispatch mission.');
                return;
            }

            // Polymorphic fallback: if no context facts provided, construct standard ground-truth markdown
            if (!context) {
                context = `# ${topic}\n\nGround truth syllabus facts for educational learning. This autonomous render node will compile high-fidelity scenes using ${renderMode.toUpperCase()} mode constraints.`;
            }

            triggerProductionBtn.disabled = true;
            triggerProductionBtn.textContent = 'Spawning Node...';

            try {
                const response = await fetch(`${API_BASE}/render`, {
                    method: 'POST',
                    headers: getHeaders(),
                    body: JSON.stringify({
                        topic: topic,
                        markdown: context,
                        render_mode: renderMode,
                        with_avatar: withAvatar,
                        use_elevenlabs: useElevenlabs
                    })
                });

                if (!response.ok) {
                    const errInfo = await response.json();
                    throw new Error(errInfo.detail || 'Dispatch failed');
                }

                const spawnedJob = await response.json();
                console.log('Successfully spawned rendering node:', spawnedJob);
                
                // Immediately highlight and inspect new job
                inspectedJobId = spawnedJob.job_id;
                hideDispatch();
                pollJobs();
            } catch (err) {
                alert(`Dispatch Error: ${err.message}`);
            } finally {
                triggerProductionBtn.disabled = false;
                triggerProductionBtn.textContent = 'Dispatch Agent Node';
            }
        });
    }
}

// Unified SIGTERM Sequence
function setupSystemHalt() {
    const haltBtn = document.querySelector('.btn-danger');
    if (haltBtn) {
        haltBtn.addEventListener('click', async () => {
            if (confirm('CRITICAL: Halting system processes will cancel all active render pipeline jobs. Are you sure?')) {
                // Find all active and queued jobs to cancel
                const activeJobs = Object.values(globalJobsStore).filter(j => j.status === 'processing' || j.status === 'queued');
                if (activeJobs.length === 0) {
                    alert('No active jobs to halt.');
                    return;
                }
                
                let successCount = 0;
                for (const job of activeJobs) {
                    try {
                        const res = await fetch(`${API_BASE}/cancel/${job.job_id}`, {
                            method: 'POST',
                            headers: getHeaders()
                        });
                        if (res.ok) successCount++;
                    } catch (e) {
                        console.error(`Failed to cancel job ${job.job_id}`, e);
                    }
                }
                
                alert(`System Halt Completed: Terminated ${successCount}/${activeJobs.length} active nodes.`);
                pollJobs();
            }
        });
    }
}

// Master Core Pipeline Polling
async function pollJobs() {
    try {
        const response = await fetch(`${API_BASE}/jobs`, { headers: getHeaders() });
        if (!response.ok) throw new Error(`Status ${response.status}`);
        const jobs = await response.json();
        
        globalJobsStore = jobs;
        populatePipelineGrid(jobs);
        updateVault(jobs);
        updateTelemetryFeed(jobs);
        
        // Dynamic Inspector Sync
        if (inspectedJobId && jobs[inspectedJobId]) {
            syncInspector(jobs[inspectedJobId]);
        }
    } catch (err) {
        console.error("Cockpit Polling Error:", err);
        // Show status badge as offline
        const statusBadge = document.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.style.color = 'var(--danger)';
            statusBadge.innerHTML = '<span class="pulse" style="background: var(--danger); box-shadow: 0 0 10px var(--danger);"></span> Factory Offline';
        }
    }
}

// Group and populate the 6 pipeline columns
function populatePipelineGrid(jobs) {
    const columns = {
        ingestion: document.getElementById('column-ingestion'),
        synthesis: document.getElementById('column-synthesis'),
        orchestration: document.getElementById('column-orchestration'),
        production: document.getElementById('column-production'),
        qc: document.getElementById('column-qc'),
        deployment: document.getElementById('column-deployment')
    };

    const counts = { ingestion: 0, synthesis: 0, orchestration: 0, production: 0, qc: 0, deployment: 0 };
    
    // Clear previous render
    Object.values(columns).forEach(col => {
        if (col) col.innerHTML = '';
    });

    const jobList = Object.values(jobs).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    if (jobList.length === 0) {
        Object.keys(columns).forEach(key => {
            if (columns[key]) {
                columns[key].innerHTML = '<div class="empty-state" style="padding: 1rem;"><span style="font-size:0.7rem; color:var(--text-muted);">Idle</span></div>';
            }
        });
        updateCounts(counts);
        return;
    }

    jobList.forEach(job => {
        const colKey = classifyJobColumn(job);
        if (!columns[colKey]) return;

        counts[colKey]++;

        const card = createJobCard(job);
        columns[colKey].appendChild(card);
    });

    updateCounts(counts);
    lucide.createIcons();
}

// Smart classification from langgraph node updates to human-observable columns
function classifyJobColumn(job) {
    if (job.status === 'completed') return 'deployment';
    if (job.status === 'queued') return 'ingestion';
    
    // Evaluate node by current_step or last logs node field
    let step = '';
    if (job.current_step) {
        step = job.current_step.toLowerCase();
    } else if (job.logs && job.logs.length > 0) {
        const lastLog = job.logs[job.logs.length - 1];
        if (lastLog && lastLog.node) {
            step = lastLog.node.toLowerCase();
        }
    }

    if (!step) {
        return job.status === 'failed' ? 'production' : 'ingestion';
    }

    if (step.includes('research') || step.includes('vision') || step.includes('system') || step.includes('initializing')) {
        return 'ingestion';
    }
    if (step.includes('director') || step.includes('architect') || step.includes('supervisor') || step.includes('ppt_planner')) {
        return 'synthesis';
    }
    if (step.includes('ambient') || step.includes('ppt_critic') || step.includes('explainer') || step.includes('notes') || step.includes('healer') || step.includes('critic')) {
        return 'orchestration';
    }
    if (step.includes('ppt_renderer') || step.includes('ppt_tts') || step.includes('ppt_video') || step.includes('explainer_slides') || step.includes('heygen') || step.includes('render') || step.includes('generator')) {
        return 'production';
    }
    if (step.includes('subtitle') || step.includes('fusion') || step.includes('qc') || step.includes('validator') || step.includes('testing')) {
        return 'qc';
    }
    if (step.includes('deploy')) {
        return 'deployment';
    }

    return 'production'; // Fallback
}

// Update UI Column Count headers
function updateCounts(counts) {
    Object.keys(counts).forEach(key => {
        const countSpan = document.getElementById(`count-${key}`);
        if (countSpan) countSpan.textContent = counts[key];
    });

    const statusBadge = document.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.style.color = 'var(--success)';
        statusBadge.innerHTML = '<span class="pulse"></span> Factory Operational';
    }
}

// Create a beautiful premium card for a rendering process
function createJobCard(job) {
    const card = document.createElement('div');
    card.className = `job-card glass ${job.status}-state`;
    card.setAttribute('data-id', job.job_id);

    if (inspectedJobId === job.job_id) {
        card.classList.add('active-inspect');
    }
    if (job.status === 'processing') {
        card.classList.add('processing-state');
    }

    // Dynamic Self-Healing observability: alert user if healer node was ever engaged
    const hasHealer = job.logs && job.logs.some(l => l.node && l.node.toLowerCase() === 'healer');
    if (hasHealer && job.status === 'processing') {
        card.classList.add('healer-engaged');
    }

    const mode = (job.render_mode || 'auto').toUpperCase();
    const truncatedTopic = job.topic.length > 26 ? job.topic.substring(0, 24) + '...' : job.topic;
    
    // Get last log statement or step
    let lastMsg = 'Queued in processing deck.';
    if (job.status === 'completed') {
        lastMsg = 'Render mission finalized.';
    } else if (job.status === 'failed') {
        lastMsg = job.error ? job.error.split('] ').pop() : 'Pipeline execution crashed.';
    } else if (job.logs && job.logs.length > 0) {
        const activeLogs = job.logs.filter(l => l.msg);
        if (activeLogs.length > 0) {
            lastMsg = activeLogs[activeLogs.length - 1].msg;
        }
    }
    if (lastMsg.length > 50) lastMsg = lastMsg.substring(0, 48) + '...';

    // Status Indicator Style
    let statusIcon = 'loader';
    let statusStyle = 'color: var(--primary); animation: spin 2s linear infinite;';
    if (job.status === 'completed') {
        statusIcon = 'check-circle';
        statusStyle = 'color: var(--success);';
    } else if (job.status === 'failed') {
        statusIcon = 'alert-octagon';
        statusStyle = 'color: var(--danger);';
    } else if (job.status === 'queued') {
        statusIcon = 'clock';
        statusStyle = 'color: var(--text-muted);';
    }

    // Progress bar variants
    let barClass = '';
    if (job.status === 'completed') barClass = 'success-bar';
    if (job.status === 'failed') barClass = 'failed-bar';

    // Formulate Overrides Actions (Human-in-the-Loop)
    let overrideActionsHtml = '';
    if (job.status === 'processing' || job.status === 'queued') {
        overrideActionsHtml = `
            <button class="btn-card-action halt" onclick="event.stopPropagation(); cancelJob('${job.job_id}')" title="Kill Pipeline Process">
                Cancel
            </button>
        `;
    } else if (job.status === 'failed') {
        overrideActionsHtml = `
            <div style="display: flex; gap: 4px;">
                <button class="btn-card-action retry" onclick="event.stopPropagation(); retryJob('${job.job_id}')" title="Re-queue Run">
                    Retry
                </button>
                <button class="btn-card-action halt" onclick="event.stopPropagation(); deleteJob('${job.job_id}')" title="Purge job">
                    Delete
                </button>
            </div>
        `;
    } else if (job.status === 'completed') {
        overrideActionsHtml = `
            <div style="display: flex; gap: 4px;">
                <button class="btn-card-action retry" onclick="event.stopPropagation(); previewVideo('${job.job_id}')" title="Stream Output">
                    Preview
                </button>
            </div>
        `;
    }

    card.innerHTML = `
        <div class="job-header">
            <span class="job-id">#${job.job_id}</span>
            <span class="status-pill mode-${job.render_mode || 'auto'}">${mode}</span>
        </div>
        <div class="job-title">${truncatedTopic}</div>
        
        <div class="progress-container">
            <div class="progress-bar ${barClass}" style="width: ${job.progress || 10}%;"></div>
        </div>
        
        <div class="job-step-desc">
            <i data-lucide="${statusIcon}" style="width:12px; height:12px; vertical-align:middle; margin-right:4px; ${statusStyle}"></i>
            <span>${lastMsg}</span>
        </div>

        ${hasHealer && job.status === 'processing' ? `
            <div class="healer-alert">
                <i data-lucide="shield-alert" style="width:12px; height:12px;"></i> Healer Active: Adjusting Coordinates
            </div>
        ` : ''}

        <div class="job-footer">
            <span>Progress: ${job.progress || 0}%</span>
            ${overrideActionsHtml}
        </div>
    `;

    // Event Bindings
    card.addEventListener('click', () => {
        document.querySelectorAll('.job-card').forEach(c => c.classList.remove('active-inspect'));
        card.classList.add('active-inspect');
        inspectedJobId = job.job_id;
        openInspector(job);
    });

    card.addEventListener('dblclick', () => {
        if (job.status === 'completed') {
            previewVideo(job.job_id);
        }
    });

    return card;
}

// Cancel Action Endpoint
async function cancelJob(jobId) {
    if (!confirm(`Halt run on node #${jobId}?`)) return;
    try {
        const response = await fetch(`${API_BASE}/cancel/${jobId}`, {
            method: 'POST',
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Could not halt rendering thread');
        pollJobs();
    } catch (e) {
        alert(e.message);
    }
}

// Retry Action Endpoint
async function retryJob(jobId) {
    try {
        const response = await fetch(`${API_BASE}/retry/${jobId}`, {
            method: 'POST',
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Could not re-queue job');
        pollJobs();
    } catch (e) {
        alert(e.message);
    }
}

// Delete Action Endpoint
async function deleteJob(jobId) {
    if (!confirm(`Permanently purge job #${jobId} from factory registers?`)) return;
    try {
        const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Delete operation failed');
        if (inspectedJobId === jobId) closeInspector();
        pollJobs();
    } catch (e) {
        alert(e.message);
    }
}

// Slide-out and Sync Inspector
function openInspector(job) {
    const inspectorPanel = document.getElementById('inspectorPanel');
    if (inspectorPanel) {
        inspectorPanel.classList.add('active');
        syncInspector(job);
    }
}

function closeInspector() {
    const inspectorPanel = document.getElementById('inspectorPanel');
    if (inspectorPanel) {
        inspectorPanel.classList.remove('active');
        inspectedJobId = null;
        document.querySelectorAll('.job-card').forEach(c => c.classList.remove('active-inspect'));
    }
}

// Sync values into the Node Inspector
function syncInspector(job) {
    document.getElementById('inspectJobId').textContent = `#${job.job_id}`;
    
    // 1. Dynamic Decision Basis Extraction
    const inspectReasoning = document.getElementById('inspectReasoning');
    let reasoning = "";
    if (job.logs && job.logs.length > 0) {
        // Look for director or logic updates
        const directorLogs = job.logs.filter(l => l.node && (l.node.toUpperCase() === 'DIRECTOR' || l.node.toUpperCase() === 'SUPERVISOR'));
        if (directorLogs.length > 0) {
            reasoning = directorLogs.map(l => l.msg).join('\n');
        }
    }
    if (!reasoning) {
        reasoning = `Autonomous profiles triggered. Path optimized for render constraints in ${job.render_mode || 'auto'} path. Engaged ElevenLabs HD TTS: ${job.use_elevenlabs ? 'YES' : 'NO'}. Realism Avatar: ${job.with_avatar ? 'ENGAGED' : 'DISABLED'}.`;
    }
    inspectReasoning.textContent = reasoning;

    // 2. Director's Blueprint scenes preview
    const inspectJson = document.getElementById('inspectJson');
    const blueprint = {
        render_mode: job.render_mode || 'auto',
        use_elevenlabs: job.use_elevenlabs || false,
        with_avatar: job.with_avatar || false,
        created_at: job.created_at,
        updated_at: job.updated_at,
        metrics: job.metrics || {}
    };
    inspectJson.textContent = JSON.stringify(blueprint, null, 4);

    // 3. State Audit Logs List
    const auditList = document.querySelector('.audit-list');
    if (auditList) {
        auditList.innerHTML = '';
        if (job.logs && job.logs.length > 0) {
            job.logs.forEach(log => {
                const li = document.createElement('li');
                const time = log.timestamp ? log.timestamp.split('T')[1].substring(0, 5) : new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit' });
                
                li.className = log.type === 'error' ? 'audit-error' : (log.node ? 'audit-node' : '');
                li.innerHTML = `<strong>[${time}] ${log.node || 'SYSTEM'}:</strong> ${log.msg}`;
                auditList.appendChild(li);
            });
        } else {
            auditList.innerHTML = '<li>No state telemetry recorded.</li>';
        }
    }
}

// Live Video Player overlay launcher
function previewVideo(jobId) {
    const job = globalJobsStore[jobId];
    if (!job || !job.video_url) return;

    const videoPlayerModal = document.getElementById('videoPlayerModal');
    const playerModalTitle = document.getElementById('playerModalTitle');
    const playerModalVideo = document.getElementById('playerModalVideo');
    const playerModalMeta = document.getElementById('playerModalMeta');
    const playerModalDownloadBtn = document.getElementById('playerModalDownloadBtn');

    if (videoPlayerModal && playerModalVideo) {
        playerModalTitle.textContent = job.topic;
        playerModalVideo.src = job.video_url;
        playerModalVideo.load();
        
        const mode = (job.render_mode || 'auto').toUpperCase();
        const duration = job.metrics && job.metrics.total_duration_sec ? `${job.metrics.total_duration_sec}s` : 'N/A';
        playerModalMeta.textContent = `Rendering Strategy: ${mode} | Factory Build Speed: ${duration}`;
        
        if (playerModalDownloadBtn) {
            playerModalDownloadBtn.onclick = () => window.open(job.video_url, '_blank');
        }

        videoPlayerModal.classList.add('active');
    }
}

// Live Console Reasoning updates at footer
function updateTelemetryFeed(jobs) {
    const consoleOutput = document.querySelector('.console-output');
    if (!consoleOutput) return;

    // Collect recent logs across ALL active/historical jobs, sorted by updated time
    let allLogs = [];
    Object.values(jobs).forEach(job => {
        if (job.logs) {
            job.logs.forEach(log => {
                allLogs.push({
                    job_id: job.job_id,
                    topic: job.topic,
                    ...log,
                    // Parse custom timestamp if exists, or approximate
                    sortTime: job.updated_at
                });
            });
        }
    });

    if (allLogs.length === 0) return;

    // Show only the last 20 events chronologically
    allLogs.sort((a, b) => new Date(a.sortTime) - new Date(b.sortTime));
    const recentLogs = allLogs.slice(-15);

    consoleOutput.innerHTML = '';
    recentLogs.forEach(log => {
        const time = new Date(log.sortTime).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const logLine = document.createElement('div');
        
        let typeClass = log.type || 'info';
        const nodeName = (log.node || '').toUpperCase();
        if (nodeName.includes('RESEARCH')) typeClass += ' research';
        if (nodeName.includes('KNOWLEDGE')) typeClass += ' knowledge';

        logLine.className = `log-line ${typeClass}`;
        logLine.innerHTML = `
            <span class="timestamp">[${time}]</span> 
            <span class="node-label info">#${log.job_id} [${log.node || 'SYSTEM'}]:</span> 
            <span>${log.msg}</span>
        `;
        consoleOutput.appendChild(logLine);
    });

    // Add trailing glowing cursor
    const cursor = document.createElement('div');
    cursor.className = 'log-line';
    cursor.innerHTML = '<span class="cursor">></span> _';
    consoleOutput.appendChild(cursor);

    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// Update Curriculum Vault Catalog
function updateVault(jobs) {
    const vaultGrid = document.querySelector('.vault-grid');
    if (!vaultGrid) return;

    const completed = Object.values(jobs)
        .filter(j => j.status === 'completed')
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    const cardsHtml = completed.map(job => {
        const thumbUrl = job.thumbnail_url || '';
        const thumbStyle = thumbUrl 
            ? `background: url('${thumbUrl}') center/cover no-repeat`
            : `background: linear-gradient(135deg, #1E293B, #0F172A)`;

        const mode = (job.render_mode || 'auto').toUpperCase();
        const date = new Date(job.created_at).toLocaleDateString();

        return `
            <div class="vault-card glass" data-id="${job.job_id}">
                <div class="thumbnail" style="${thumbStyle};">
                    <div class="overlay" onclick="previewVideo('${job.job_id}')"><i data-lucide="play-circle"></i></div>
                    <span class="duration">${mode}</span>
                </div>
                <div class="card-body">
                    <h4>${job.topic}</h4>
                    <span class="meta">${date}</span>
                    <div class="card-actions">
                        <button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.7rem;" onclick="window.open('${job.video_url}', '_blank')">
                            <i data-lucide="download" style="width:12px; height:12px;"></i> Download
                        </button>
                        <button class="btn btn-danger" style="padding: 4px 8px; font-size: 0.7rem; background: rgba(239,68,68,0.1); border-color: rgba(239,68,68,0.2);" onclick="deleteJob('${job.job_id}')">
                            <i data-lucide="trash-2" style="width:12px; height:12px;"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    const emptyIngestCard = `
        <div class="vault-card glass empty" id="vaultBulkLink">
            <div class="add-prompt">
                <i data-lucide="plus-circle"></i>
                <p style="font-size:0.8rem; font-weight:700;">Ingest New Curriculum</p>
                <span style="font-size:0.65rem; color:var(--text-muted); display:block; margin-top:2px;">Trigger AI generation nodes</span>
            </div>
        </div>
    `;

    vaultGrid.innerHTML = cardsHtml + emptyIngestCard;
    lucide.createIcons();

    // Update stats count in headers
    const completedStat = document.querySelector('.vault-stats .stat:first-child');
    if (completedStat) {
        completedStat.innerHTML = `<i data-lucide="video" style="width:14px; height:14px; vertical-align:middle; margin-right:4px;"></i> ${completed.length} Masterclasses`;
    }
}
