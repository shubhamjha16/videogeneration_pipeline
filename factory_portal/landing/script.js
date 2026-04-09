// Initialize Lucide Icons
lucide.createIcons();

// Smooth scrolling for Anchor Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// Simple Stat Animation on Scroll
const animateStats = () => {
    const stats = document.querySelectorAll('.stat-value');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const finalValue = parseFloat(target.innerText);
                let current = 0;
                const duration = 2000; // 2 seconds
                const increment = finalValue / (duration / 16); // 60fps

                const updateCount = () => {
                    current += increment;
                    if (current < finalValue) {
                        target.innerText = current.toFixed(current % 1 === 0 ? 0 : 1) + (target.innerText.includes('%') || target.innerText.includes('k') ? target.innerText.slice(-1) : '');
                        requestAnimationFrame(updateCount);
                    } else {
                        target.innerText = entry.target.dataset.originalValue || target.innerText;
                    }
                };
                
                // Store original value for suffix restoration
                if (!target.dataset.originalValue) {
                    target.dataset.originalValue = target.innerText;
                }
                
                updateCount();
                observer.unobserve(target);
            }
        });
    }, { threshold: 0.5 });

    stats.forEach(stat => observer.observe(stat));
};

// Intersection Observer for feature cards fade-in
const animateCards = () => {
    const cards = document.querySelectorAll('.feature-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.6s cubic-bezier(0.22, 1, 0.36, 1)';
        observer.observe(card);
    });
};

document.addEventListener('DOMContentLoaded', () => {
    animateStats();
    animateCards();
});
