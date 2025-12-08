/**
 * Main application JavaScript
 * Toast notifications, confetti animations, theme toggle, and navigation menus
 */

// Toast notification manager (Alpine.js component)
document.addEventListener('alpine:init', () => {
    Alpine.data('toastManager', () => ({
        toasts: [],
        nextId: 0,

        add(detail) {
            const id = this.nextId++;
            const toast = {
                id,
                type: detail.type || 'info',
                message: detail.message,
                visible: true
            };
            this.toasts.push(toast);

            // Auto-dismiss after 4 seconds
            setTimeout(() => {
                this.remove(id);
            }, 4000);
        },

        remove(id) {
            const toast = this.toasts.find(t => t.id === id);
            if (toast) {
                toast.visible = false;
                // Remove from array after transition
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 200);
            }
        }
    }));
});

// Global showToast function for use anywhere in JavaScript
function showToast(type, message) {
    window.dispatchEvent(new CustomEvent('show-toast', {
        detail: { type, message }
    }));
}

// Global showConfetti function for celebration animations
function showConfetti(type = 'basic') {
    if (typeof confetti !== 'function') return;

    if (type === 'session_complete') {
        // Burst from both sides for session completion
        const count = 200;
        const defaults = { origin: { y: 0.7 }, disableForReducedMotion: true };

        function fire(particleRatio, opts) {
            confetti({
                ...defaults,
                ...opts,
                particleCount: Math.floor(count * particleRatio)
            });
        }

        fire(0.25, { spread: 26, startVelocity: 55, origin: { x: 0.2 } });
        fire(0.2, { spread: 60, origin: { x: 0.2 } });
        fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8, origin: { x: 0.2 } });
        fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2, origin: { x: 0.2 } });
        fire(0.1, { spread: 120, startVelocity: 45, origin: { x: 0.2 } });

        fire(0.25, { spread: 26, startVelocity: 55, origin: { x: 0.8 } });
        fire(0.2, { spread: 60, origin: { x: 0.8 } });
        fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8, origin: { x: 0.8 } });
        fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2, origin: { x: 0.8 } });
        fire(0.1, { spread: 120, startVelocity: 45, origin: { x: 0.8 } });
    } else if (type === 'achievement') {
        // Star-shaped confetti for achievements
        const defaults = {
            spread: 360,
            ticks: 100,
            gravity: 0,
            decay: 0.94,
            startVelocity: 30,
            colors: ['#FFD700', '#FFA500', '#FF6347', '#87CEEB', '#98FB98'],
            disableForReducedMotion: true
        };

        function shoot() {
            confetti({
                ...defaults,
                particleCount: 40,
                scalar: 1.2,
                shapes: ['star']
            });
            confetti({
                ...defaults,
                particleCount: 20,
                scalar: 0.75,
                shapes: ['circle']
            });
        }

        setTimeout(shoot, 0);
        setTimeout(shoot, 100);
        setTimeout(shoot, 200);
    } else {
        // Basic confetti burst
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
            disableForReducedMotion: true
        });
    }
}

// Theme toggle functionality
(function() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
    const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
    const mobileThemeToggleBtn = document.getElementById('mobile-theme-toggle');
    const mobileThemeToggleDarkIcon = document.getElementById('mobile-theme-toggle-dark-icon');
    const mobileThemeToggleLightIcon = document.getElementById('mobile-theme-toggle-light-icon');

    function updateThemeIcons() {
        const isDark = document.documentElement.classList.contains('dark');
        // Desktop icons
        if (themeToggleLightIcon && themeToggleDarkIcon) {
            if (isDark) {
                themeToggleLightIcon.classList.remove('hidden');
                themeToggleDarkIcon.classList.add('hidden');
            } else {
                themeToggleDarkIcon.classList.remove('hidden');
                themeToggleLightIcon.classList.add('hidden');
            }
        }
        // Mobile icons
        if (mobileThemeToggleLightIcon && mobileThemeToggleDarkIcon) {
            if (isDark) {
                mobileThemeToggleLightIcon.classList.remove('hidden');
                mobileThemeToggleDarkIcon.classList.add('hidden');
            } else {
                mobileThemeToggleDarkIcon.classList.remove('hidden');
                mobileThemeToggleLightIcon.classList.add('hidden');
            }
        }
    }

    // Make setTheme available globally for settings page
    window.setTheme = function(theme, csrfToken) {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
        updateThemeIcons();

        // Sync to database if CSRF token provided
        if (csrfToken) {
            fetch('/api/theme/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ theme: theme })
            }).catch(() => {});  // Silently fail if not logged in or offline
        }
    };

    // Initialize icons
    updateThemeIcons();

    // Desktop theme toggle handler
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            const isDark = document.documentElement.classList.contains('dark');
            const newTheme = isDark ? 'light' : 'dark';
            // Get CSRF token from the page
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                              document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            window.setTheme(newTheme, csrfToken);
        });
    }

    // Mobile theme toggle handler
    if (mobileThemeToggleBtn) {
        mobileThemeToggleBtn.addEventListener('click', function() {
            const isDark = document.documentElement.classList.contains('dark');
            const newTheme = isDark ? 'light' : 'dark';
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                              document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            window.setTheme(newTheme, csrfToken);
        });
    }

    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileMenuIconOpen = document.getElementById('mobile-menu-icon-open');
    const mobileMenuIconClose = document.getElementById('mobile-menu-icon-close');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
            mobileMenuIconOpen.classList.toggle('hidden');
            mobileMenuIconClose.classList.toggle('hidden');
        });
    }

    // User menu toggle
    const userMenuButton = document.getElementById('user-menu-button');
    const userMenu = document.getElementById('user-menu');

    if (userMenuButton && userMenu) {
        userMenuButton.addEventListener('click', function(e) {
            e.stopPropagation();
            userMenu.classList.toggle('hidden');
        });

        document.addEventListener('click', function() {
            userMenu.classList.add('hidden');
        });
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            updateThemeIcons();
        }
    });
})();
