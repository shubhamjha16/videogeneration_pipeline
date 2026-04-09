// Initialize Lucide Icons
lucide.createIcons();

// Tab Switching Logic
const navBtns = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        
        // Update Buttons
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update Content
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === (tabId + 'Tab')) {
                content.classList.add('active');
            }
        });
    });
});

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

// Radio Group Logic
document.querySelectorAll('.radio').forEach(radio => {
    radio.addEventListener('click', () => {
        radio.parentElement.querySelectorAll('.radio').forEach(r => r.classList.remove('active'));
        radio.classList.add('active');
    });
});

// Grounded Telemetry Log Simulation (Real LangGraph Nodes)
const consoleOutput = document.querySelector('.console-output');
const logs = [
    { type: 'info', node: 'DIRECTOR', msg: 'Successfully locked ground-truth MCQ answer for JOB-102. (Option B)' },
    { type: 'warning', node: 'CRITIC', msg: 'REJECTED PPT Plan for UPSC History. Feedback: "Narration too generic, needs more specific dates."' },
    { type: 'info', node: 'VISION', msg: 'Gemini Imagen 3.0 generating diagram for Job-101 (Subject: Forensic Anatomy).' },
    { type: 'success', node: 'ARCHITECT', msg: 'Manim architectural blueprint validated. Transitioning to Supervisor node.' },
    { type: 'info', node: 'HEALER', msg: 'Standing by. Supervisor monitoring Manim stdout for Job-098...' },
    { type: 'warning', node: 'SUPERVISOR', msg: 'Render Attempt 1/3 failed. Manim syntax error detected in EaseToLearnScene.py.' },
    { type: 'info', node: 'HEALER', msg: 'HealerAgent engaged. Fixing syntax error in Manim class definition.' },
    { type: 'success', node: 'DEPLOY', msg: 'Job #JOB-095 successfully uploaded to S3 Bucket [easetolearn-video-factory].' }
];

const addLogLine = (node = null, message = null, type = 'info') => {
    const log = node ? {node, msg: message, type} : logs[Math.floor(Math.random() * logs.length)];
    const time = new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit' });
    
    const line = document.createElement('div');
    line.className = 'log-line';
    line.innerHTML = `<span class="timestamp">[${time}]</span> <span class="${log.type}">${log.node}:</span> ${log.msg}`;
    
    const cursor = consoleOutput.querySelector('.active');
    consoleOutput.insertBefore(line, cursor);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
    
    if (consoleOutput.children.length > 50) {
        consoleOutput.removeChild(consoleOutput.children[0]);
    }
};

// Start occasional random logs
setInterval(addLogLine, 8000);

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

        addLogLine("OPERATOR", `Override manually engaged for ${title}. Mode: ${pill.innerText}`, "info");
    });
});

// Bulk Ingest Simulation
const startBatchBtn = document.getElementById('startBatchBtn');
startBatchBtn.addEventListener('click', () => {
    closeModal();
    addLogLine("SYSTEM", "INITIALIZING BATCH RENDER: Curriculum 'Mathematics Masterclass' chapters 1-40.", "success");
    addLogLine("ORCHESTRATOR", "Spawning 40 parallel graph instances...", "info");
    
    // Simulate log flood
    for (let i = 1; i <= 5; i++) {
        setTimeout(() => {
            addLogLine("DIRECTOR", `Batch Item #${i}: HTML Parsing complete. MCQ Ground-truth locked.`, "info");
        }, i * 500);
    }

    setTimeout(() => {
        alert("Batch production initialized. 40 jobs have been queued in the background.");
    }, 3000);
});

// System Halt Sequence
const haltBtn = document.querySelector('.btn-danger');
haltBtn.addEventListener('click', () => {
    if (confirm('CRITICAL: Trigger Global System Halt? All active processes will be terminated.')) {
        document.body.style.filter = 'grayscale(1) sepia(0.5) brightness(0.5)';
        document.body.style.pointerEvents = 'none';
        addLogLine("CRITICAL", "FACTORY TERMINATED. ALL NODES HALTED BY OPERATOR.", "warning");
        setTimeout(() => alert('Factory Offline. Restart required via SSH.'), 1000);
    }
});
