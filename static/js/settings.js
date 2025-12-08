/**
 * Settings page JavaScript
 * Theme preview and custom days visibility toggle
 */

(function() {
    // Sync theme setting changes to localStorage immediately
    const themeSelect = document.getElementById('id_theme');
    if (themeSelect) {
        themeSelect.addEventListener('change', function(e) {
            const theme = e.target.value;
            if (theme === 'system') {
                localStorage.removeItem('theme');
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (prefersDark) {
                    document.documentElement.classList.add('dark');
                } else {
                    document.documentElement.classList.remove('dark');
                }
            } else {
                localStorage.setItem('theme', theme);
                if (theme === 'dark') {
                    document.documentElement.classList.add('dark');
                } else {
                    document.documentElement.classList.remove('dark');
                }
            }
        });
    }

    // Toggle custom days visibility based on frequency selection
    const frequencySelect = document.getElementById('id_frequency');
    const customDaysSection = document.getElementById('custom-days-section');

    function updateCustomDaysVisibility() {
        if (frequencySelect && customDaysSection) {
            if (frequencySelect.value === 'custom') {
                customDaysSection.classList.remove('hidden');
            } else {
                customDaysSection.classList.add('hidden');
            }
        }
    }

    // Set initial state
    updateCustomDaysVisibility();

    // Listen for changes
    if (frequencySelect) {
        frequencySelect.addEventListener('change', updateCustomDaysVisibility);
    }
})();
