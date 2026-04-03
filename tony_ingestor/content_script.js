console.log("🛡️ Tony Ingestor: Content Script Loaded.");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("🛡️ Tony Ingestor: Message Received:", request);
  if (request.action === "capture") {
    try {
      // Look for the specific TONY AI lesson modal or main content
      let content = document.body.innerHTML;
      
      // Heuristic: Find the largest div or the one containing 'Carpopedal'
      const modal = document.querySelector('.modal-content') || document.querySelector('[role="dialog"]');
      if (modal) {
          content = modal.innerHTML;
      }

      const lessonData = {
        title: document.title,
        html: content,
        url: window.location.href,
        timestamp: new Date().toISOString()
      };
      console.log("🛡️ Tony Ingestor: Data Captured.");
      sendResponse({ success: true, data: lessonData });
    } catch (err) {
      console.error("🛡️ Tony Ingestor: Capture Error:", err);
      sendResponse({ success: false, error: err.message });
    }
  }
  return true; // Keep channel open
});
