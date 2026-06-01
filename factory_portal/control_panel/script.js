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
    setupStudioWorkspace();
    
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

// Local Storyboard Storage
let currentStoryboard = [];

// Setup Storyboard Studio Workspace
function setupStudioWorkspace() {
    const studioDraftBtn = document.getElementById('studioDraftBtn');
    const studioCompileBtn = document.getElementById('studioCompileBtn');
    const studioAddSlideBtn = document.getElementById('studioAddSlideBtn');
    
    if (studioDraftBtn) {
        studioDraftBtn.addEventListener('click', async () => {
            const topic = document.getElementById('studioTopicInput').value.trim();
            const content = document.getElementById('studioContentInput').value.trim();
            const subject = document.getElementById('studioSubjectSelect').value;
            const renderMode = document.getElementById('studioStrategySelect').value;
            const withAvatar = document.getElementById('studioWithAvatar').checked;
            const useElevenlabs = document.getElementById('studioUseElevenlabs').checked;
            
            if (!topic) {
                alert('Please enter a lesson topic.');
                return;
            }
            if (!content) {
                alert('Please enter some curriculum content / facts.');
                return;
            }
            
            studioDraftBtn.disabled = true;
            studioDraftBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> Drafting Blueprint...';
            lucide.createIcons();
            
            try {
                const response = await fetch(`${API_BASE}/storyboard/draft`, {
                    method: 'POST',
                    headers: getHeaders(),
                    body: JSON.stringify({
                        topic: topic,
                        markdown: content,
                        render_mode: renderMode,
                        with_avatar: withAvatar,
                        use_elevenlabs: useElevenlabs,
                        avatar_type: withAvatar ? "tony_cartoon" : null
                    })
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Failed to draft storyboard.');
                }
                
                const draft = await response.json();
                currentStoryboard = draft.scenes || [];
                
                renderStoryboardWorkspace(currentStoryboard);
                
                // Show slide counts and footer
                document.getElementById('studioIdleState').style.display = 'none';
                document.getElementById('studioSlidesDeck').style.display = 'flex';
                document.getElementById('studioDispatchFooter').style.display = 'flex';
                document.getElementById('studioSlideCount').style.display = 'inline-block';
                document.getElementById('studioAddSlideBtn').style.display = 'flex';
                
                // Update stats
                document.getElementById('studioSlideCount').textContent = `${currentStoryboard.length} slides`;
                updateEstCosts();
            } catch (e) {
                alert(`Drafting Error: ${e.message}`);
            } finally {
                studioDraftBtn.disabled = false;
                studioDraftBtn.innerHTML = '<i data-lucide="sparkles"></i> Draft Storyboard Outline';
                lucide.createIcons();
            }
        });
    }
    
    if (studioAddSlideBtn) {
        studioAddSlideBtn.addEventListener('click', () => {
            // Push a default blank concept bullet slide
            currentStoryboard.push({
                visual_type: "concept_bullets",
                tony_pose: "explaining",
                visual_data: {
                    title: "New Concept",
                    bullets: ["Key learning point 1"]
                },
                narration_text: "Let's explore this next concept in detail. We will analyze the core facts and properties here."
            });
            renderStoryboardWorkspace(currentStoryboard);
            updateEstCosts();
            
            // Scroll to bottom of deck
            const deck = document.getElementById('studioSlidesDeck');
            setTimeout(() => deck.scrollTop = deck.scrollHeight, 100);
        });
    }
    
    if (studioCompileBtn) {
        studioCompileBtn.addEventListener('click', async () => {
            const topic = document.getElementById('studioTopicInput').value.trim();
            const content = document.getElementById('studioContentInput').value.trim();
            const renderMode = document.getElementById('studioStrategySelect').value;
            const withAvatar = document.getElementById('studioWithAvatar').checked;
            const useElevenlabs = document.getElementById('studioUseElevenlabs').checked;
            
            if (currentStoryboard.length === 0) {
                alert('No storyboard scenes exist to compile.');
                return;
            }
            
            studioCompileBtn.disabled = true;
            studioCompileBtn.innerHTML = '<i data-lucide="loader" class="spin"></i> Launching Production...';
            lucide.createIcons();
            
            try {
                const response = await fetch(`${API_BASE}/render`, {
                    method: 'POST',
                    headers: getHeaders(),
                    body: JSON.stringify({
                        topic: topic,
                        markdown: content,
                        render_mode: renderMode,
                        with_avatar: withAvatar,
                        use_elevenlabs: useElevenlabs,
                        avatar_type: withAvatar ? "tony_cartoon" : null,
                        storyboard: currentStoryboard
                    })
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'HD Render dispatch failed.');
                }
                
                alert('Success! Custom video compilation job dispatched successfully.');
                
                // Reset studio fields
                document.getElementById('studioTopicInput').value = '';
                document.getElementById('studioContentInput').value = '';
                currentStoryboard = [];
                
                // Reset Studio view back to idle
                document.getElementById('studioSlidesDeck').style.display = 'none';
                document.getElementById('studioSlidesDeck').innerHTML = '';
                document.getElementById('studioDispatchFooter').style.display = 'none';
                document.getElementById('studioSlideCount').style.display = 'none';
                document.getElementById('studioAddSlideBtn').style.display = 'none';
                document.getElementById('studioIdleState').style.display = 'flex';
                
                // Redirect to Mission Control tab
                const missionBtn = document.querySelector('[data-tab="mission"]');
                if (missionBtn) missionBtn.click();
                pollJobs(); // Refresh grid immediately
            } catch (e) {
                alert(`Render Error: ${e.message}`);
            } finally {
                studioCompileBtn.disabled = false;
                studioCompileBtn.innerHTML = '<i data-lucide="play-circle"></i> Compile HD Video Masterclass';
                lucide.createIcons();
            }
        });
    }
}

// Render the scrollable editor workspace cards
function renderStoryboardWorkspace(scenes) {
    const deck = document.getElementById('studioSlidesDeck');
    if (!deck) return;
    
    deck.innerHTML = '';
    
    scenes.forEach((scene, index) => {
        const card = document.createElement('div');
        card.className = 'studio-slide-card glass';
        card.setAttribute('data-index', index);
        
        const title = scene.visual_data.title || scene.visual_data.heading || "Slide Title";
        const bulletsText = scene.visual_data.bullets ? scene.visual_data.bullets.join('\n') : '';
        const objectsText = scene.visual_data.objects ? scene.visual_data.objects.join(', ') : '';
        const narration = scene.narration_text || '';
        
        // Match visual icon based on slide type
        let mockIcon = 'presentation';
        let mockLabel = 'Slide Layout';
        let mockDesc = 'Whiteboard card layout';
        
        const type = scene.visual_type;
        if (type === 'title_card') {
            mockIcon = 'file-text';
            mockLabel = 'Title Slide';
            mockDesc = 'Introduction title card';
        } else if (type.includes('formula')) {
            mockIcon = 'binary';
            mockLabel = 'Math Derivation';
            mockDesc = 'LaTeX safe Manim equations';
        } else if (type.includes('mcq') || type === 'answer_reveal' || type === 'cross_out' || type === 'option_highlight') {
            mockIcon = 'help-circle';
            mockLabel = 'MCQ Sequence';
            mockDesc = 'Atomic MCQ layout card';
        } else if (type === 'annotated_image') {
            mockIcon = 'image';
            mockLabel = 'Concept Diagram';
            mockDesc = 'Splitted label illustration';
        } else if (type === 'b_roll_clip' || type === 'generative_video') {
            mockIcon = 'clapperboard';
            mockLabel = 'Cinematic Video';
            mockDesc = 'Dynamic generative B-roll';
        } else if (type === 'counting_metaphor') {
            mockIcon = 'layers';
            mockLabel = 'Metaphor Counting';
            mockDesc = 'Animated stylized counting';
        }
        
        const poses = [
            { id: 'desk_happy', label: 'Happy (desk)' },
            { id: 'standing_point_up', label: 'Point Up' },
            { id: 'thinking', label: 'Thinking' },
            { id: 'confused', label: 'Confused' },
            { id: 'explaining', label: 'Explaining' },
            { id: 'idea', label: 'Eureka Idea' },
            { id: 'reading', label: 'Reading Case' },
            { id: 'excited', label: 'Excited Accent' },
            { id: 'victory', label: 'Triumphant Victory' }
        ];
        
        const poseOptions = poses.map(p => {
            const sel = (scene.tony_pose === p.id) ? 'selected' : '';
            return `<option value="${p.id}" ${sel}>${p.label}</option>`;
        }).join('');
        
        card.innerHTML = `
            <div class="slide-card-header">
                <span class="slide-num-badge">SLIDE ${index + 1}</span>
                <div class="slide-card-actions">
                    <span class="status-pill manual">${scene.visual_type.toUpperCase().replace('_', ' ')}</span>
                    <button class="btn-card-danger" onclick="deleteStudioSlide(${index})">Delete</button>
                </div>
            </div>
            
            <div class="slide-visual-editor">
                <!-- Left aspect-ratio 16:9 widescreen mockup -->
                <div class="slide-mockup-left">
                    <i data-lucide="${mockIcon}" class="mockup-icon"></i>
                    <span class="mockup-label">${mockLabel}</span>
                    <p class="mockup-desc">${mockDesc}</p>
                    <span class="tony-mock-pose" id="pose-preview-${index}">${scene.tony_pose || 'desk_happy'}</span>
                </div>
                
                <!-- Right slide details form -->
                <div class="slide-mockup-right">
                    <div class="slide-input-group">
                        <label>Slide Title / Heading</label>
                        <input type="text" class="input-slide-title" value="${escapeHtml(title)}" oninput="updateSlideData(${index}, 'title', this.value)">
                    </div>
                    
                    <div class="slide-input-group">
                        <label>Bullet Points (One per line)</label>
                        <textarea class="textarea-slide-bullets" placeholder="Point 1&#10;Point 2...">${escapeHtml(bulletsText)}</textarea>
                    </div>
                    
                    <div class="editor-pose-doodles">
                        <div class="slide-input-group">
                            <label>Tutor Pose Gesture</label>
                            <select class="glass selector" style="width: 100%; padding: 4px;" onchange="updateSlidePose(${index}, this.value)">
                                <option value="" ${!scene.tony_pose ? 'selected' : ''}>None (Disabled)</option>
                                ${poseOptions}
                            </select>
                        </div>
                        <div class="slide-input-group">
                            <label>Doodles / Objects to Draw</label>
                            <input type="text" class="input-slide-title" value="${escapeHtml(objectsText)}" placeholder="e.g. atoms, heart, chart..." oninput="updateSlideDoodles(${index}, this.value)">
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Bottom narration script editor -->
            <div class="slide-narration-editor">
                <label>Narration / spoken Voiceover Script</label>
                <textarea class="textarea-narration-script" oninput="updateSlideNarration(${index}, this.value)">${escapeHtml(narration)}</textarea>
            </div>
        `;
        
        // Listen to bullets textarea specifically
        const bulletsArea = card.querySelector('.textarea-slide-bullets');
        bulletsArea.addEventListener('input', () => {
            const bullets = bulletsArea.value.split('\n').map(b => b.trim()).filter(b => b.length > 0);
            scene.visual_data.bullets = bullets;
            updateEstCosts();
        });
        
        deck.appendChild(card);
    });
    
    // Update stats count in headers
    document.getElementById('studioSlideCount').textContent = `${scenes.length} slides`;
    lucide.createIcons();
}

// Global functions for inline mutations
window.deleteStudioSlide = function(index) {
    currentStoryboard.splice(index, 1);
    renderStoryboardWorkspace(currentStoryboard);
    updateEstCosts();
};

window.updateSlideData = function(index, field, value) {
    if (currentStoryboard[index] && currentStoryboard[index].visual_data) {
        currentStoryboard[index].visual_data[field] = value;
    }
};

window.updateSlidePose = function(index, value) {
    if (currentStoryboard[index]) {
        currentStoryboard[index].tony_pose = value || null;
        const preview = document.getElementById(`pose-preview-${index}`);
        if (preview) preview.textContent = value || 'disabled';
    }
};

window.updateSlideDoodles = function(index, value) {
    if (currentStoryboard[index] && currentStoryboard[index].visual_data) {
        currentStoryboard[index].visual_data.objects = value.split(',').map(o => o.trim()).filter(o => o.length > 0);
    }
};

window.updateSlideNarration = function(index, value) {
    if (currentStoryboard[index]) {
        currentStoryboard[index].narration_text = value;
        updateEstCosts();
    }
};

// Calculate cost estimations live based on narration word counts
function updateEstCosts() {
    let charCount = 0;
    currentStoryboard.forEach(s => {
        charCount += (s.narration_text || '').length;
    });
    
    // Estimates: LLM draft ($0.10) + ElevenLabs ($0.03 per 1k chars) + DALL-E ($0.04 per slide)
    const voiceCost = charCount * 0.00003;
    const assetsCost = currentStoryboard.length * 0.04;
    const est = 0.10 + voiceCost + assetsCost;
    
    const costText = document.getElementById('studioEstCost');
    if (costText) costText.textContent = `$${est.toFixed(2)}`;
    
    const timeText = document.getElementById('studioEstTime');
    if (timeText) {
        const buildTime = currentStoryboard.length * 20; // 20s average per slide
        timeText.textContent = `~${buildTime}s`;
    }
}

// Escape HTML utility
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
