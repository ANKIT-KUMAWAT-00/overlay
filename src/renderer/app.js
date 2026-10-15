// Elements
const targetNameEl = document.getElementById('targetName');
const statusMessageEl = document.getElementById('statusMessage');
const statusSpinnerEl = document.getElementById('statusSpinner');
const questionInput = document.getElementById('questionInput');
const captureSourceBadge = document.getElementById('captureSourceBadge');
const formatBadge = document.getElementById('formatBadge');
const answerCodeBlock = document.getElementById('answerCodeBlock');
const btnInsert = document.getElementById('btnInsert');
const btnCopy = document.getElementById('btnCopy');
const btnCancel = document.getElementById('btnCancel');
const btnRunQuery = document.getElementById('btnRunQuery');
const btnSettings = document.getElementById('btnSettings');
const btnClose = document.getElementById('btnClose');
// Stepper elements
const stepCapture = document.getElementById('stepCapture');
const stepGenerate = document.getElementById('stepGenerate');
const stepValidate = document.getElementById('stepValidate');
const stepReady = document.getElementById('stepReady');
const stepDeliver = document.getElementById('stepDeliver');
// Settings Modal
const settingsModal = document.getElementById('settingsModal');
const btnCloseSettings = document.getElementById('btnCloseSettings');
const btnSaveSettings = document.getElementById('btnSaveSettings');
const apiKeyInput = document.getElementById('apiKeyInput');
const btnToggleKey = document.getElementById('btnToggleKey');
const modelSelect = document.getElementById('modelSelect');
const activationShortcutInput = document.getElementById('activationShortcutInput');
const insertionShortcutInput = document.getElementById('insertionShortcutInput');
const privacyModeCheck = document.getElementById('privacyModeCheck');
const permScreen = document.getElementById('permScreen');
const permAccess = document.getElementById('permAccess');
let currentAnswer = '';
let selectedMethod = 'selected_text';
// Initialize
async function init() {
    setupEventListeners();
    if (window.assistantApi) {
        window.assistantApi.onStateChange((context) => {
            renderState(context);
        });
        const state = await window.assistantApi.getState();
        renderState(state);
        loadSettings();
    }
}
function updateStepper(state) {
    const steps = [
        { el: stepCapture, states: ['CAPTURING', 'CAPTURE_RECOVERY'] },
        { el: stepGenerate, states: ['GENERATING', 'GENERATION_RECOVERY'] },
        { el: stepValidate, states: ['VALIDATING'] },
        { el: stepReady, states: ['READY'] },
        { el: stepDeliver, states: ['DELIVERING', 'DELIVERY_RECOVERY', 'COMPLETED'] },
    ];
    const stateOrder = [
        'IDLE',
        'ACTIVATING',
        'CAPTURING',
        'CAPTURE_RECOVERY',
        'GENERATING',
        'GENERATION_RECOVERY',
        'VALIDATING',
        'READY',
        'DELIVERING',
        'DELIVERY_RECOVERY',
        'COMPLETED',
    ];
    const currentIndex = stateOrder.indexOf(state);
    steps.forEach((step, idx) => {
        step.el.classList.remove('active', 'done');
        if (step.states.includes(state)) {
            step.el.classList.add('active');
        }
        else if (currentIndex > (idx + 1) * 2) {
            step.el.classList.add('done');
        }
    });
}
function renderState(context) {
    if (!context)
        return;
    // 1. Target Application
    if (context.targetApp) {
        targetNameEl.textContent = `${context.targetApp.appName} (${context.targetApp.category})`;
    }
    else {
        targetNameEl.textContent = 'Active Desktop';
    }
    // 2. Stepper & Status
    updateStepper(context.state);
    const isBusy = [
        'ACTIVATING',
        'CAPTURING',
        'CAPTURE_RECOVERY',
        'GENERATING',
        'GENERATION_RECOVERY',
        'VALIDATING',
        'DELIVERING',
    ].includes(context.state);
    if (isBusy) {
        statusSpinnerEl.classList.add('spinning');
    }
    else {
        statusSpinnerEl.classList.remove('spinning');
    }
    const latestHistory = context.history?.[context.history.length - 1];
    statusMessageEl.textContent = latestHistory?.message || `State: ${context.state}`;
    // 3. Question
    if (context.questionText !== undefined) {
        questionInput.value = context.questionText;
    }
    if (context.capturedVia) {
        captureSourceBadge.textContent = `Source: ${context.capturedVia}`;
    }
    // 4. Answer
    const answer = context.validatedAnswer || context.generatedAnswer || '';
    currentAnswer = answer;
    if (answer) {
        answerCodeBlock.textContent = answer;
        btnInsert.disabled = false;
        btnCopy.disabled = false;
    }
    else if (context.state === 'GENERATING') {
        answerCodeBlock.textContent = 'Gemini AI is analyzing and composing response...';
        btnInsert.disabled = true;
        btnCopy.disabled = true;
    }
    else if (context.state === 'CAPTURING') {
        answerCodeBlock.textContent = 'Reading active screen context...';
        btnInsert.disabled = true;
        btnCopy.disabled = true;
    }
    else {
        answerCodeBlock.textContent = 'Waiting for question or trigger...';
        btnInsert.disabled = true;
        btnCopy.disabled = true;
    }
    // 5. Format badge
    if (context.questionFormat) {
        formatBadge.textContent = `Format: ${context.questionFormat.toUpperCase()}`;
    }
}
function setupEventListeners() {
    // Capture Pills
    document.querySelectorAll('.pill-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pill-btn').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');
            selectedMethod = btn.getAttribute('data-method') || 'selected_text';
        });
    });
    // Query Run
    btnRunQuery.addEventListener('click', async () => {
        const text = questionInput.value.trim();
        if (text) {
            await window.assistantApi.submitManualQuestion(text);
        }
    });
    // Actions
    btnInsert.addEventListener('click', async () => {
        await window.assistantApi.deliverAnswer();
    });
    btnCopy.addEventListener('click', async () => {
        if (currentAnswer) {
            await window.assistantApi.copyAnswer(currentAnswer);
            const originalText = statusMessageEl.textContent;
            statusMessageEl.textContent = 'Answer copied to clipboard!';
            setTimeout(() => {
                statusMessageEl.textContent = originalText;
            }, 2000);
        }
    });
    btnCancel.addEventListener('click', async () => {
        await window.assistantApi.cancelTask();
    });
    btnClose.addEventListener('click', () => {
        window.assistantApi.hideWindow();
    });
    // Settings
    btnSettings.addEventListener('click', async () => {
        settingsModal.classList.remove('hidden');
        loadSettings();
    });
    btnCloseSettings.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });
    btnToggleKey.addEventListener('click', () => {
        if (apiKeyInput.type === 'password') {
            apiKeyInput.type = 'text';
            btnToggleKey.textContent = 'Hide';
        }
        else {
            apiKeyInput.type = 'password';
            btnToggleKey.textContent = 'Show';
        }
    });
    btnSaveSettings.addEventListener('click', async () => {
        await window.assistantApi.updateSettings({
            geminiApiKey: apiKeyInput.value.trim(),
            modelName: modelSelect.value,
            activationShortcut: activationShortcutInput.value.trim(),
            insertionShortcut: insertionShortcutInput.value.trim(),
            privacyMode: privacyModeCheck.checked,
        });
        settingsModal.classList.add('hidden');
        statusMessageEl.textContent = 'Settings updated successfully.';
    });
    // Keyboard navigation
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!settingsModal.classList.contains('hidden')) {
                settingsModal.classList.add('hidden');
            }
            else {
                window.assistantApi.hideWindow();
            }
        }
        else if (e.altKey && e.key === 'Enter') {
            if (!btnInsert.disabled) {
                btnInsert.click();
            }
        }
    });
}
async function loadSettings() {
    if (!window.assistantApi)
        return;
    const settings = await window.assistantApi.getSettings();
    if (settings) {
        if (settings.geminiApiKey)
            apiKeyInput.value = settings.geminiApiKey;
        if (settings.modelName)
            modelSelect.value = settings.modelName;
        if (settings.activationShortcut)
            activationShortcutInput.value = settings.activationShortcut;
        if (settings.insertionShortcut)
            insertionShortcutInput.value = settings.insertionShortcut;
        privacyModeCheck.checked = Boolean(settings.privacyMode);
    }
    const perms = await window.assistantApi.checkPermissions();
    if (perms) {
        permScreen.textContent = `Screen Recording: ${perms.screenRecording ? 'Granted' : 'Needed'}`;
        permScreen.style.color = perms.screenRecording ? 'var(--success)' : 'var(--warning)';
        permAccess.textContent = `Accessibility: ${perms.accessibility ? 'Granted' : 'Needed'}`;
        permAccess.style.color = perms.accessibility ? 'var(--success)' : 'var(--warning)';
    }
}
// Start
window.addEventListener('DOMContentLoaded', init);
export {};
