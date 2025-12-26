/**
 * Review session JavaScript
 * Card review logic, keyboard shortcuts, and rating submission
 */

// Review session initialization
function initReviewSession(config) {
    const { cards, defaultTextSize, celebrationAnimations, csrfToken, practiceMode = false } = config;

    // State
    let currentIndex = 0;
    let showingAnswer = false;
    let answerChecked = false;  // For type-in cards
    let stats = { reviewed: 0, correct: 0, again: 0 };
    let currentTextSize = localStorage.getItem('cardTextSize') || defaultTextSize;

    // DOM elements
    const cardContainer = document.getElementById('card-container');
    const sessionComplete = document.getElementById('session-complete');
    const frontText = document.getElementById('front-text');
    const backText = document.getElementById('back-text');
    const notesText = document.getElementById('notes-text');
    const notesContainer = document.getElementById('notes-container');
    const cardBack = document.getElementById('card-back');
    const showAnswerContainer = document.getElementById('show-answer-container');
    const ratingContainer = document.getElementById('rating-container');
    const showAnswerBtn = document.getElementById('show-answer-btn');
    const checkAnswerContainer = document.getElementById('check-answer-container');
    const checkAnswerBtn = document.getElementById('check-answer-btn');
    const typeinContainer = document.getElementById('typein-container');
    const typeinInput = document.getElementById('typein-input');
    const typeinResult = document.getElementById('typein-result');
    const expectedAnswer = document.getElementById('expected-answer');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressTextDesktop = document.getElementById('progress-text-desktop');

    // Cloze pattern: {{c1::text}} or {{c1::text::hint}}
    const CLOZE_PATTERN = /\{\{c(\d+)::([^:}]+)(?:::([^}]+))?\}\}/g;

    // Cloze rendering functions
    function renderClozeQuestion(text, activeCloze) {
        return text.replace(CLOZE_PATTERN, (match, num, answer, hint) => {
            const clozeNum = parseInt(num);
            if (activeCloze === null || clozeNum === activeCloze) {
                if (hint) {
                    return `<span class="cloze-blank has-hint">${hint}</span>`;
                }
                return '<span class="cloze-blank"></span>';
            }
            return answer;
        });
    }

    function renderClozeAnswer(text, activeCloze) {
        return text.replace(CLOZE_PATTERN, (match, num, answer, hint) => {
            const clozeNum = parseInt(num);
            if (activeCloze === null || clozeNum === activeCloze) {
                return `<span class="cloze-answer">${answer}</span>`;
            }
            return answer;
        });
    }

    function isClozeCard(card) {
        return card.card_type === 'cloze';
    }

    function isTypeinCard(card) {
        return card.card_type === 'typein';
    }

    // Answer comparison for type-in cards
    function normalizeAnswer(text) {
        return text.trim().toLowerCase();
    }

    function compareAnswers(userAnswer, correctAnswer) {
        return normalizeAnswer(userAnswer) === normalizeAnswer(correctAnswer);
    }

    function checkTypeinAnswer() {
        const card = cards[currentIndex];
        const userAnswer = typeinInput.value;
        const correctAnswer = card.back;
        const isCorrect = compareAnswers(userAnswer, correctAnswer);

        typeinResult.classList.remove('hidden', 'correct', 'incorrect');
        if (isCorrect) {
            typeinResult.textContent = '✓ Correct!';
            typeinResult.classList.add('correct');
            expectedAnswer.classList.add('hidden');
        } else {
            typeinResult.textContent = '✗ Incorrect';
            typeinResult.classList.add('incorrect');
            expectedAnswer.textContent = `Expected: ${correctAnswer}`;
            expectedAnswer.classList.remove('hidden');
        }

        typeinInput.disabled = true;
        checkAnswerContainer.classList.add('hidden');
        ratingContainer.classList.remove('hidden');
        answerChecked = true;
        showingAnswer = true;
    }

    // Text size functions
    function setTextSize(size) {
        currentTextSize = size;
        localStorage.setItem('cardTextSize', size);

        const sizes = ['small', 'medium', 'large', 'xlarge', 'xxlarge', 'xxxlarge'];
        document.querySelectorAll('.card-text').forEach(el => {
            sizes.forEach(s => el.classList.remove('size-' + s));
            el.classList.add('size-' + size);
        });

        document.querySelectorAll('.size-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.size === size);
        });
    }

    function showCard(index) {
        const card = cards[index];

        if (isClozeCard(card)) {
            const activeCloze = card.active_cloze;
            frontText.innerHTML = renderClozeQuestion(card.front, activeCloze);
            backText.innerHTML = renderClozeAnswer(card.front, activeCloze);
        } else {
            frontText.textContent = card.front;
            backText.textContent = card.back;
        }

        if (card.notes) {
            notesText.textContent = card.notes;
            notesContainer.classList.remove('hidden');
        } else {
            notesContainer.classList.add('hidden');
        }

        // Handle type-in cards
        if (isTypeinCard(card)) {
            typeinContainer.classList.remove('hidden');
            typeinInput.value = '';
            typeinInput.disabled = false;
            typeinResult.classList.add('hidden');
            expectedAnswer.classList.add('hidden');
            showAnswerContainer.classList.add('hidden');
            checkAnswerContainer.classList.remove('hidden');
            setTimeout(() => typeinInput.focus(), 100);
        } else {
            typeinContainer.classList.add('hidden');
            showAnswerContainer.classList.remove('hidden');
            checkAnswerContainer.classList.add('hidden');
        }

        cardBack.classList.add('hidden');
        ratingContainer.classList.add('hidden');
        showingAnswer = false;
        answerChecked = false;

        updateProgress();
    }

    function showAnswer() {
        cardBack.classList.remove('hidden');
        showAnswerContainer.classList.add('hidden');
        ratingContainer.classList.remove('hidden');
        showingAnswer = true;
    }

    // Achievement display names
    const achievementNames = {
        'first_review': 'First Step',
        'reviews_100': '100 Cards Reviewed',
        'reviews_500': '500 Cards Reviewed',
        'reviews_1000': '1,000 Cards Reviewed',
        'streak_7': '7-Day Streak',
        'streak_30': '30-Day Streak',
        'streak_100': '100-Day Streak'
    };

    async function submitRating(quality) {
        const card = cards[currentIndex];

        // Use different API endpoint for practice mode
        const apiUrl = practiceMode 
            ? `/api/practice/${card.id}/` 
            : `/api/review/${card.id}/`;

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ quality })
            });

            if (!response.ok) throw new Error('Review failed');

            const data = await response.json();

            // Check for achievements (only in regular review mode)
            if (!practiceMode && data.achievements && data.achievements.length > 0 && celebrationAnimations) {
                data.achievements.forEach(key => {
                    const name = achievementNames[key] || key;
                    showToast('success', `Achievement unlocked: ${name}!`);
                    showConfetti('achievement');
                });
            }

            stats.reviewed++;
            if (quality >= 3) {
                stats.correct++;
            }
            if (quality < 3) {
                stats.again++;
            }

            currentIndex++;
            if (currentIndex >= cards.length) {
                showComplete();
            } else {
                showCard(currentIndex);
            }
        } catch (error) {
            console.error('Error submitting review:', error);
            showToast('error', 'Failed to submit review. Please try again.');
        }
    }

    function showComplete() {
        cardContainer.classList.add('hidden');
        sessionComplete.classList.remove('hidden');

        document.getElementById('stat-reviewed').textContent = stats.reviewed;
        document.getElementById('stat-correct').textContent = stats.correct;
        document.getElementById('stat-again').textContent = stats.again;

        progressBar.style.width = '100%';
        progressText.textContent = `${cards.length} / ${cards.length}`;
        progressTextDesktop.textContent = `${cards.length} / ${cards.length}`;

        if (celebrationAnimations && stats.reviewed > 0) {
            showConfetti('session_complete');
        }
    }

    function updateProgress() {
        const progress = (currentIndex / cards.length) * 100;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${currentIndex} / ${cards.length}`;
        progressTextDesktop.textContent = `${currentIndex} / ${cards.length}`;
    }

    function setupEventListeners() {
        showAnswerBtn.addEventListener('click', showAnswer);
        checkAnswerBtn.addEventListener('click', checkTypeinAnswer);

        document.querySelectorAll('.rating-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const quality = parseInt(btn.dataset.quality);
                submitRating(quality);
            });
        });

        document.querySelectorAll('.size-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                setTextSize(btn.dataset.size);
            });
        });

        typeinInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !answerChecked) {
                e.preventDefault();
                checkTypeinAnswer();
            }
        });

        // Keyboard shortcuts
        window.addEventListener('keydown', (e) => {
            if (e.target === typeinInput) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (currentIndex >= cards.length) return;

            const card = cards[currentIndex];

            if ((e.code === 'Space' || e.key === ' ') && !showingAnswer) {
                e.preventDefault();
                if (!isTypeinCard(card)) {
                    showAnswer();
                }
            } else if (showingAnswer) {
                const keyMap = {
                    '1': 0, '2': 2, '3': 4, '4': 5,
                    'Digit1': 0, 'Digit2': 2, 'Digit3': 4, 'Digit4': 5,
                    'Numpad1': 0, 'Numpad2': 2, 'Numpad3': 4, 'Numpad4': 5
                };
                const quality = keyMap[e.key] !== undefined ? keyMap[e.key] : keyMap[e.code];
                if (quality !== undefined) {
                    e.preventDefault();
                    e.stopPropagation();
                    submitRating(quality);
                }
            }
        }, true);
    }

    // Initialize
    if (cards.length === 0) {
        showComplete();
        return;
    }
    setTextSize(currentTextSize);
    showCard(0);
    setupEventListeners();
}
