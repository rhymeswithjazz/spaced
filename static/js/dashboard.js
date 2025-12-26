/**
 * Dashboard JavaScript
 * Statistics tab navigation and next review countdown
 */

(function() {
    // Tab navigation
    const tabs = document.querySelectorAll('.stats-tab');
    const contents = document.querySelectorAll('.stats-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Update tab styles
            tabs.forEach(t => {
                t.classList.remove('active', 'border-primary-500', 'text-primary-600', 'dark:text-primary-400');
                t.classList.add('border-transparent', 'text-gray-500', 'dark:text-gray-400');
            });
            tab.classList.add('active', 'border-primary-500', 'text-primary-600', 'dark:text-primary-400');
            tab.classList.remove('border-transparent', 'text-gray-500', 'dark:text-gray-400');

            // Show corresponding content
            const targetId = 'tab-' + tab.dataset.tab;
            contents.forEach(content => {
                content.classList.toggle('hidden', content.id !== targetId);
            });
        });
    });

    // Next review countdown
    const countdownEl = document.getElementById('next-review-countdown');
    if (countdownEl) {
        const nextReview = new Date(countdownEl.dataset.nextReview);
        
        function updateCountdown() {
            const now = new Date();
            const diff = nextReview - now;
            
            if (diff <= 0) {
                countdownEl.textContent = 'Cards due now!';
                countdownEl.classList.add('text-yellow-600', 'dark:text-yellow-400', 'font-medium');
                return;
            }
            
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            
            if (hours > 24) {
                const days = Math.floor(hours / 24);
                countdownEl.textContent = `Next review in ${days} day${days > 1 ? 's' : ''}`;
            } else if (hours > 0) {
                countdownEl.textContent = `Next review in ${hours}h ${minutes}m`;
            } else {
                countdownEl.textContent = `Next review in ${minutes}m`;
            }
        }
        
        updateCountdown();
        setInterval(updateCountdown, 60000); // Update every minute
    }
})();
