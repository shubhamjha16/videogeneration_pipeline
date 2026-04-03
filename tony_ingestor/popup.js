document.getElementById('captureBtn').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const status = document.getElementById('status');
  
  status.textContent = "Capturing Lesson...";
  
  chrome.tabs.sendMessage(tab.id, { action: "capture" }, async (response) => {
    if (chrome.runtime.lastError) {
      console.error("🛡️ Pull Error:", chrome.runtime.lastError);
      status.textContent = "❌ Error: Please REFRESH the TONY AI page first.";
      return;
    }
    
    if (response && response.success) {
      status.textContent = "🚀 Sending to Factory...";
      
      try {
          const apiResponse = await fetch('http://localhost:8000/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              topic: response.data.title.split(':')[0].trim(),
              html: response.data.html
            })
          });
          
          const { job_id } = await apiResponse.json();
          pollStatus(job_id);
      } catch (err) {
          status.textContent = "❌ Connection Failed (Is API running?)";
      }
    } else {
      status.textContent = "❌ Capture Failed. Try Manual Paste below.";
      document.getElementById('manualArea').style.display = 'block';
    }
  });
});

document.getElementById('manualBtn').addEventListener('click', async () => {
    const input = document.getElementById('manualInput').value;
    const status = document.getElementById('status');
    if (!input) return;
    
    status.textContent = "🚀 Sending Manual Data...";
    try {
        const apiResponse = await fetch('http://localhost:8000/render', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic: "ManualEntry_" + Date.now(),
            html: input
          })
        });
        const { job_id } = await apiResponse.json();
        pollStatus(job_id);
    } catch (err) {
        status.textContent = "❌ API Connection Failed.";
    }
});

function pollStatus(job_id) {
    const status = document.getElementById('status');
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`http://localhost:8000/status/${job_id}`);
            const data = await res.json();
            
            if (data.status === "completed") {
                clearInterval(interval);
                status.innerHTML = `✅ Ready! <a href="${data.video_url}" target="_blank" style="color:#ffcc00">Download Video</a>`;
            } else if (data.status === "failed") {
                clearInterval(interval);
                status.textContent = `❌ Failed: ${data.error}`;
            } else {
                status.textContent = `🎬 Rendering... (${data.status})`;
            }
        } catch (err) {
            clearInterval(interval);
            status.textContent = "❌ Lost connection to factory.";
        }
    }, 3000);
}
