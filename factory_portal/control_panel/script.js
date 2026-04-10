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

// Inspector Logic
const inspectorPanel = document.getElementById('inspectorPanel');
const inspectJobId = document.getElementById('inspectJobId');
const inspectJson = document.getElementById('inspectJson');
const inspectReasoning = document.getElementById('inspectReasoning');

window.inspectJob = (jobId) => {
    inspectJobId.innerText = `#JOB-${jobId}`;
    inspectorPanel.classList.add('active');
    
    // Simulate Grounded Scene JSON extraction
    const mockData = {
        "99": {
            "mode": "presentation",
            "reasoning": "Topic identified as UPSC History (Arts/Factual). defaulting to Presentation mode to minimize compute while preserving structured text clarity.",
            "scenes": [
                { "layout": "title_card", "data": { "title": "UPSC History" } },
                { "layout": "chaos_chapter", "data": { "title": "The Mughal Empire" } }
            ]
        },
        "102": {
            "mode": "manim",
            "reasoning": "Detected MCQ with Probability logic. Upgrading to MANIM path for interactive visual option elimination and correct answer grounding.",
            "scenes": [
                { "visual_type": "mcq_layout", "visual_data": { "correct": "B" } }
            ]
        },
        "98": {
            "mode": "manim",
            "reasoning": "Medical anatomical topic detected (Bronchopleural Fistula). Manim selected for precise anatomical coordinate mapping and dynamic flow overlays.",
            "scenes": [
                { "visual_type": "image_arrow", "visual_data": { "label": "Leaking Air" } }
            ]
        }
    };
    
    const data = mockData[jobId] || mockData["99"];
    inspectJson.innerText = JSON.stringify({render_mode: data.mode, scenes: data.scenes}, null, 4);
    inspectReasoning.innerText = data.reasoning;
};

window.closeInspector = () => {
    inspectorPanel.classList.remove('active');
};

// Modal Logic
const bulkModal = document.getElementById('bulkModal');
const bulkIngestBtn = document.getElementById('bulkIngestBtn');
const vaultBulkLink = document.getElementById('vaultBulkLink');
const closeModals = document.querySelectorAll('.close-modal');

const openModal = () => bulkModal.classList.add('active');
const closeModal = () => bulkModal.classList.remove('active');

bulkIngestBtn.addEventListener('click', openModal);
vaultBulkLink.addEventListener('click', openModal);
closeModals.forEach(btn => btn.addEventListener('click', closeModal));

// Grounded Telemetry Log Simulation (Actual Code State Names)
const consoleOutput = document.querySelector('.console-output');
const latencyDisplay = document.getElementById('latencyDisplay');

const groundedLogs = [
    { type: 'info', node: 'DIRECTOR', msg: 'parsed_facts: LOCKED. Ground truth MCQ answer identified for JOB-102.' },
    { type: 'warning', node: 'HEALER', msg: 'Manim SyntaxError in scene_04.py: LaTeX escape failed. Repairing...' },
    { type: 'success', node: 'HEALER', msg: 'Scene fixed. Re-injecting into Manim Supervisor.' },
    { type: 'info', node: 'VISION', msg: 'Gemini Imagen 4.0: Conceptual diagram generation started for {topic}.' },
    { type: 'success', node: 'DEPLOY', msg: 'Job #JOB-095: artifact_path verified. S3 Upload successful.' },
    { type: 'info', node: 'ARCHITECT', msg: 'Blueprint validation: checking manim_script_path consistency.' }
];

const addLogLine = (node = null, message = null, type = 'info') => {
    const log = node ? {node, msg: message, type} : groundedLogs[Math.floor(Math.random() * groundedLogs.length)];
    const time = new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit' });
    
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="timestamp">[${time}]</span> <span class="${log.type}">${log.node}:</span> ${log.msg}`;
    
    const cursor = consoleOutput.querySelector('.active');
    consoleOutput.insertBefore(line, cursor);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
    
    // Simulate dynamic latency jitter
    if (!node) {
        const lat = (Math.random() * 0.5 + 0.8).toFixed(1);
        latencyDisplay.innerText = `Claude-4.6 (${lat}s)`;
    }
};

setInterval(addLogLine, 6000);

// Multi-mode Select Logic for Render Path
const renderModeSelect = document.getElementById('renderModeSelect');
const renderModePill = document.getElementById('renderModePill');

if (renderModeSelect) {
    renderModeSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        renderModePill.innerText = e.target.options[e.target.selectedIndex].text;
        
        // Map values to pill classes
        const classMap = {
            'auto': 'mode-auto',
            'manim': 'mode-manim',
            'presentation': 'mode-edu',
            'explainer': 'mode-explainer',
            'user_generated_video': 'mode-ugv'
        };
        
        renderModePill.className = "status-pill " + (classMap[val] || "manual");
        addLogLine("OPERATOR", `Manual State Override: Render Mode set to ${renderModePill.innerText}`, "info");
    });
}

// Toggle Logic for Overrides
document.querySelectorAll('.toggle input').forEach(input => {
    input.addEventListener('change', (e) => {
        const item = e.target.closest('.switch-item');
        const title = item.querySelector('.title').innerText;
        const pill = item.querySelector('.status-pill');
        const checked = e.target.checked;
        
        if (title === "Render Path") {
            pill.innerText = checked ? "MANIM" : "PPT";
            pill.className = "status-pill " + (checked ? "mode-manim" : "mode-edu");
        } else if (title === "Critic Soul") {
            pill.innerText = checked ? "EDU" : "MKT";
            pill.className = "status-pill " + (checked ? "mode-edu" : "manual");
        } else if (title === "Vision Engine") {
            pill.innerText = checked ? "AUTO" : "OFF";
            pill.className = "status-pill " + (checked ? "auto" : "manual");
        }

        addLogLine("OPERATOR", `Manual State Override: ${title} set to ${pill.innerText}`, "info");
    });
});

// Bulk Ingest Simulation
const startBatchBtn = document.getElementById('startBatchBtn');
startBatchBtn.addEventListener('click', () => {
    closeModal();
    addLogLine("SYSTEM", "BATCH_INIT: Initializing ensemble for 40 chapters.", "success");
    addLogLine("ORCHESTRATOR", "Allocation complete: 40 threads reserved in api_bridge.", "info");
    
    setTimeout(() => {
        alert("Batch Production Active. Monitor the matrix for parallel nodes.");
    }, 2000);
});

// System Halt Sequence
const haltBtn = document.querySelector('.btn-danger');
haltBtn.addEventListener('click', () => {
    if (confirm('CRITICAL: SIGTERM ALL NODES? This will kill all active Manim render processes.')) {
        document.body.style.filter = 'grayscale(1) brightness(0.4)';
        document.body.style.pointerEvents = 'none';
        addLogLine("CORE", "SIGTERM RECEIVED. FACTORY EMERGENCY SHUTDOWN COMPLETE.", "warning");
    }
});
