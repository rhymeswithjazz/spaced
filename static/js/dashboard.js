/**
 * Dashboard JavaScript
 * Statistics tab navigation
 */

(function() {
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
})();
