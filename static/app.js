// viz Experts chatbot - Frontend Logic

// State management
let token = sessionStorage.getItem("auth_token") || null;
let userName = sessionStorage.getItem("user_name") || null;

let activeSessionId =
    sessionStorage.getItem("active_session_id")
        ? parseInt(sessionStorage.getItem("active_session_id"))
        : null;
let recognition = null;
let selectedFile = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordingSeconds = 0;
let confirmationAction = null;
const tableStates = {};

const ROWS_PER_PAGE = 10;
// Stores the result of the latest live API-key test.
// null = not tested in this session
// true = latest test succeeded
// false = latest test failed
let liveTestStatus = {
    groq: null,
    gemini: null
};

// Base API endpoints
const API_URL = "";

// Initialize App
document.addEventListener("DOMContentLoaded", () => {
    checkAuthAndRoute();
    
    // Bind Enter key on chat textarea to submit
    const textarea = document.getElementById("chatInputField");
    textarea.addEventListener("input", function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});

// ==============================================================================
// ROUTING & VIEW CONTROLLER
// ==============================================================================

function switchView(viewName) {
    const views = ["login", "signup", "config", "chat"];
    views.forEach(v => {
        const el = document.getElementById(`${v}View`);
        if (v === viewName) {
            el.classList.remove("hidden");
        } else {
            el.classList.add("hidden");
        }
    });

    // Hide settings modal just in case
    closeSettingsModal();
}

async function checkAuthAndRoute() {

    if (!token) {
        switchView("login");
        return;
    }

    try {

        const configResponse = await fetch(
            `${API_URL}/config`,
            {
                headers: {
                    "Authorization":
                        `Bearer ${token}`
                }
            }
        );

        if (configResponse.status === 401) {
            handleLogout(false);
            return;
        }

        const configStatus =
            await configResponse.json();

        const zohoStatus =
            await loadZohoStatus();

        const combinedStatus = {
            ...configStatus,

            zoho_configured:
                !!zohoStatus.connected,

            configured:
                !!zohoStatus.connected &&
                (
                    !!configStatus.groq_configured ||
                    !!configStatus.gemini_configured
                )
        };

        updateConnectionStatusBadges(
            combinedStatus
        );

        // Handle OAuth callback result.
        const params =
            new URLSearchParams(
                window.location.search
            );

        if (
            params.get("zoho_connected") === "true"
        ) {

            const successEl =
                document.getElementById(
                    "configSuccess"
                );

            if (successEl) {

                successEl.innerText =
                    "Zoho CRM connected successfully.";

                successEl.classList.remove(
                    "hidden"
                );
            }

            // Clean URL.
            window.history.replaceState(
                {},
                document.title,
                window.location.pathname
            );

            await loadZohoStatus();
        }

        if (params.get("zoho_error")) {

            const error =
                params.get("zoho_error");

            const errorEl =
                document.getElementById(
                    "configError"
                );

            if (errorEl) {

                errorEl.innerText =
                    decodeURIComponent(error);

                errorEl.classList.remove(
                    "hidden"
                );
            }

            window.history.replaceState(
                {},
                document.title,
                window.location.pathname
            );
        }

        if (!combinedStatus.configured) {

            switchView("config");

            await loadConfigFields();
            await loadZohoStatus();

        } else {

            switchView("chat");

            loadChatHistory();
        }

    } catch (err) {

        console.error(
            "Routing error:",
            err
        );

        switchView("login");
    }
}

function updateConnectionStatusBadges(status) {
    const topZoho = document.getElementById("topZohoIndicator");
    const topGroq = document.getElementById("topGroqIndicator");
    const topGemini = document.getElementById("topGeminiIndicator");
    const bottomDot = document.getElementById("bottomStatusDot");
    const bottomLabel = document.getElementById("bottomStatusLabel");
 
    const zohoBadge = document.getElementById("zohoStatusBadge");
    const groqBadge = document.getElementById("groqStatusBadge");
    const geminiBadge = document.getElementById("geminiStatusBadge");
 
    const isZoho = !!status.zoho_configured;

    const isGroq =
        liveTestStatus.groq !== null
            ? liveTestStatus.groq
            : !!status.groq_configured;

    const isGemini =
        liveTestStatus.gemini !== null
            ? liveTestStatus.gemini
            : !!status.gemini_configured;
 
    // Top Indicators
    if (topZoho) topZoho.className = `w-2 h-2 rounded-full ${isZoho ? "bg-green-500" : "bg-error"}`;
    if (topGroq) topGroq.className = `w-2 h-2 rounded-full ${isGroq ? "bg-green-500" : "bg-error"}`;
    if (topGemini) topGemini.className = `w-2 h-2 rounded-full ${isGemini ? "bg-green-500" : "bg-error"}`;
 
    // Bottom Indicator - Connected if Zoho is configured and at least one LLM is configured
    const isConnected = isZoho && (isGroq || isGemini);
    if (bottomDot) bottomDot.className = `w-1.5 h-1.5 ${isConnected ? "bg-green-500" : "bg-error"} rounded-full`;
    if (bottomLabel) {
        if (isConnected) {
            bottomLabel.innerText = "System Connected";
        } else {
            bottomLabel.innerText = "Configuration Needed";
        }
    }
 
    // Config view badges
    if (zohoBadge) {
        if (isZoho) {
            zohoBadge.className = "status-indicator status-connected";
            zohoBadge.innerText = "CONNECTED";
        } else {
            zohoBadge.className = "status-indicator status-disconnected";
            zohoBadge.innerText = "DISCONNECTED";
        }
    }
 
    if (groqBadge) {
        if (isGroq) {
            groqBadge.className = "status-indicator status-connected";
            groqBadge.innerText = "CONNECTED";
        } else {
            groqBadge.className = "status-indicator status-disconnected";
            groqBadge.innerText = "DISCONNECTED";
        }
    }

    if (geminiBadge) {
        if (isGemini) {
            geminiBadge.className = "status-indicator status-connected";
            geminiBadge.innerText = "CONNECTED";
        } else {
            geminiBadge.className = "status-indicator status-disconnected";
            geminiBadge.innerText = "DISCONNECTED";
        }
    }
}

// ==============================================================================
// PROFESSIONAL NOTIFICATION SYSTEM
// ==============================================================================

function showToast(type, title, message, duration = 4000) {
    const container = document.getElementById("toastContainer");

    if (!container) {
        return;
    }

    const icons = {
        success: "check_circle",
        error: "error",
        warning: "warning",
        info: "info"
    };

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    toast.innerHTML = `
        <div class="toast-icon">
            <span class="material-symbols-outlined">
                ${icons[type] || icons.info}
            </span>
        </div>

        <div class="toast-content">
            <div class="toast-title"></div>
            <div class="toast-message"></div>
        </div>

        <button type="button" class="toast-close" aria-label="Close notification">
            <span class="material-symbols-outlined">close</span>
        </button>

        <div class="toast-progress"></div>
    `;

    toast.querySelector(".toast-title").textContent = title || "";
    toast.querySelector(".toast-message").textContent = message || "";

    toast.style.setProperty("--toast-duration", `${duration}ms`);

    const closeToast = () => {
        if (!toast.isConnected) {
            return;
        }

        toast.classList.add("toast-removing");

        setTimeout(() => {
            toast.remove();
        }, 300);
    };

    toast.querySelector(".toast-close").addEventListener("click", closeToast);

    container.appendChild(toast);

    setTimeout(closeToast, duration);

    return toast;
}

// ==============================================================================
// AUTHENTICATION FLOW
// ==============================================================================

// Login Form Submit
// Login Form Submit
document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const emailInput = document.getElementById("loginEmail");
    const passwordInput = document.getElementById("loginPassword");

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    const emailError = document.getElementById("loginEmailError");
    const passwordError = document.getElementById("loginPasswordError");

    const btn = document.getElementById("loginBtn");

    // Clear previous validation errors
    emailError.textContent = "";
    passwordError.textContent = "";

    emailError.classList.add("hidden");
    passwordError.classList.add("hidden");

    emailInput.classList.remove("border-error", "focus:border-error");
    passwordInput.classList.remove("border-error", "focus:border-error");

    const origHtml = btn.innerHTML;

    btn.innerHTML = `
        <span class="material-symbols-outlined animate-spin text-sm">
            sync
        </span>
        Logging in...
    `;

    btn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email,
                password
            })
        });

        const data = await response.json();

        // Authentication failed
        if (!response.ok || data.success === false) {

            if (data.field === "email") {

                emailError.textContent =
                    data.message || "Invalid email address.";

                emailError.classList.remove("hidden");

                emailInput.classList.add(
                    "border-error",
                    "focus:border-error"
                );

                emailInput.focus();

            } else if (data.field === "password") {

                passwordError.textContent =
                    data.message || "Invalid password.";

                passwordError.classList.remove("hidden");

                passwordInput.classList.add(
                    "border-error",
                    "focus:border-error"
                );

                passwordInput.focus();

            } else {

                emailError.textContent =
                    data.message || "Unable to sign in.";

                emailError.classList.remove("hidden");
            }

            return;
        }

        // Successful login
        token = data.token;
        userName = data.full_name;

        sessionStorage.setItem("auth_token", token);
        sessionStorage.setItem("user_name", userName);

        btn.innerHTML = `
            <span class="material-symbols-outlined text-sm">
                check_circle
            </span>
            Success
        `;

        btn.classList.add("bg-green-600");

        setTimeout(() => {
            btn.innerHTML = origHtml;
            btn.classList.remove("bg-green-600");
            btn.disabled = false;

            checkAuthAndRoute();
        }, 700);

    } catch (err) {

        console.error("Login error:", err);

        emailError.textContent =
            "Unable to connect to the server. Please try again.";

        emailError.classList.remove("hidden");

    } finally {

        if (!token) {
            btn.innerHTML = origHtml;
            btn.disabled = false;
        }
    }
});

// Signup Form Submit
// Signup Form Submit
document.getElementById("signupForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const fullName =
        document.getElementById("signupName").value.trim();

    const emailInput =
        document.getElementById("signupEmail");

    const passwordInput =
        document.getElementById("signupPassword");

    const confirmPasswordInput =
        document.getElementById("signupConfirmPassword");

    const email =
        emailInput.value.trim();

    const password =
        passwordInput.value;

    const confirmPassword =
        confirmPasswordInput.value;

    const errEl =
        document.getElementById("signupError");

    const emailError =
        document.getElementById("signupEmailError");

    const btn =
        document.getElementById("signupBtn");

    // Clear previous errors
    errEl.innerText = "";
    errEl.classList.add("hidden");

    emailError.innerText = "";
    emailError.classList.add("hidden");

    emailInput.classList.remove(
        "border-error",
        "focus:border-error"
    );

    passwordInput.classList.remove(
        "border-error",
        "focus:border-error"
    );

    confirmPasswordInput.classList.remove(
        "border-error",
        "focus:border-error"
    );

    // Password confirmation validation
    if (password !== confirmPassword) {

        confirmPasswordInput.classList.add(
            "border-error",
            "focus:border-error"
        );

        errEl.innerText =
            "Passwords do not match.";

        errEl.classList.remove("hidden");

        confirmPasswordInput.focus();

        return;
    }

    const originalHtml =
        btn.innerHTML;

    btn.disabled = true;

    btn.innerHTML = `
        <span class="material-symbols-outlined animate-spin text-sm">
            sync
        </span>
        Creating Account...
    `;

    try {

        const response =
            await fetch(`${API_URL}/auth/signup`, {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    full_name: fullName,
                    email,
                    password
                })
            });

        const data =
            await response.json();

        // --------------------------------------------------
        // DUPLICATE EMAIL / SIGNUP ERROR
        // --------------------------------------------------

        if (!response.ok || data.success === false) {

            if (data.field === "email") {

                emailError.innerText =
                    data.message ||
                    "This email address already exists.";

                emailError.classList.remove(
                    "hidden"
                );

                emailInput.classList.add(
                    "border-error",
                    "focus:border-error"
                );

                emailInput.focus();

            } else {

                errEl.innerText =
                    data.message ||
                    data.detail ||
                    "Unable to create your account.";

                errEl.classList.remove(
                    "hidden"
                );
            }

            return;
        }

        // --------------------------------------------------
        // SUCCESS
        // --------------------------------------------------

        token =
            data.token;

        userName =
            data.full_name;

        sessionStorage.setItem(
            "auth_token",
            token
        );

        sessionStorage.setItem(
            "user_name",
            userName
        );

        btn.innerHTML = `
            <span class="material-symbols-outlined">
                check_circle
            </span>
            Account Created
        `;

        btn.classList.add(
            "bg-green-600"
        );

        // Show proper success popup
        showSignupSuccessPopup(
            data.message ||
            "Your account has been created successfully."
        );

    } catch (err) {

        console.error(
            "Signup error:",
            err
        );

        errEl.innerText =
            "Unable to connect to the server. Please try again.";

        errEl.classList.remove(
            "hidden"
        );

    } finally {

        if (
            !document
                .getElementById("signupSuccessModal")
                ?.classList.contains("hidden")
        ) {
            return;
        }

        btn.innerHTML =
            originalHtml;

        btn.classList.remove(
            "bg-green-600"
        );

        btn.disabled =
            false;
    }
});

// Forgot Password Flow
async function handleForgotPassword() {
    const email = prompt("Please enter your registered email address:");
    if (!email) return;

    try {
        const response = await fetch(`${API_URL}/auth/forgot-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        });
        const data = await response.json();
        showToast(
            "success",
            "Password recovery",
            data.message || "Password recovery request processed successfully."
        );
    } catch (err) {
        showToast(
            "error",
            "Request failed",
            "Unable to process password recovery. Please try again."
        );
    }
}

// Password Visibility toggle
function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === "password") {
        input.type = "text";
        icon.innerText = "visibility_off";
    } else {
        input.type = "password";
        icon.innerText = "visibility";
    }
}

// ==============================================================================
// SIGNUP SUCCESS POPUP
// ==============================================================================

function showSignupSuccessPopup(message) {

    const modal =
        document.getElementById("signupSuccessModal");

    const messageEl =
        document.getElementById("signupSuccessMessage");

    if (!modal) {
        return;
    }

    if (messageEl) {
        messageEl.innerText =
            message ||
            "Your account has been created successfully.";
    }

    modal.classList.remove("hidden");
}


function closeSignupSuccessPopup() {

    const modal =
        document.getElementById("signupSuccessModal");

    if (modal) {
        modal.classList.add("hidden");
    }

    checkAuthAndRoute();
}

function handleLogout(requireConfirmation = true) {

    if (requireConfirmation) {

        showConfirmationPopup({
            title: "Sign out",
            message: "Are you sure you want to sign out?",
            confirmText: "Sign out",
            icon: "logout",
            action: () => performLogout()
        });

        return;
    }

    performLogout();
}

function performLogout() {

    token = null;
    userName = null;
    activeSessionId = null;

    sessionStorage.removeItem("auth_token");
    sessionStorage.removeItem("user_name");
    sessionStorage.removeItem("active_session_id");

    switchView("login");
}

// ==============================================================================
// CONFIRMATION POPUP
// ==============================================================================

function showConfirmationPopup({
    title = "Confirm Action",
    message = "Are you sure?",
    confirmText = "Confirm",
    icon = "help",
    action
}) {
    const modal =
        document.getElementById("confirmationModal");

    const titleEl =
        document.getElementById("confirmationTitle");

    const messageEl =
        document.getElementById("confirmationMessage");

    const confirmBtn =
        document.getElementById("confirmationConfirmBtn");

    const iconEl =
        document.getElementById("confirmationIcon");

    if (!modal || !titleEl || !messageEl || !confirmBtn) {
        return;
    }

    titleEl.innerText = title;
    messageEl.innerText = message;
    confirmBtn.innerText = confirmText;

    if (iconEl) {
        iconEl.innerText = icon;
    }

    confirmationAction = action;

    modal.classList.remove("hidden");
}

function closeConfirmationPopup() {
    const modal =
        document.getElementById("confirmationModal");

    if (modal) {
        modal.classList.add("hidden");
    }

    confirmationAction = null;
}

function confirmPopupAction() {
    const action = confirmationAction;

    closeConfirmationPopup();

    if (typeof action === "function") {
        action();
    }
}

// ==============================================================================
// ZOHO OAUTH CONNECTION
// ==============================================================================

async function connectZohoCRM() {

    const clientId =
        document.getElementById("configZohoClientId").value.trim();

    const clientSecret =
        document.getElementById("configZohoClientSecret").value.trim();

    const btn =
        document.getElementById("connectZohoBtn");

    const errEl =
        document.getElementById("configError");

    const succEl =
        document.getElementById("configSuccess");

    errEl.classList.add("hidden");
    succEl.classList.add("hidden");

    if (!clientId) {
        errEl.innerText =
            "Please enter your Zoho Client ID.";

        errEl.classList.remove("hidden");
        return;
    }

    if (!clientSecret) {
        errEl.innerText =
            "Please enter your Zoho Client Secret.";

        errEl.classList.remove("hidden");
        return;
    }

    const originalText = btn.innerHTML;

    btn.disabled = true;

    btn.innerHTML = `
        <span class="material-symbols-outlined animate-spin">
            progress_activity
        </span>
        <span>Connecting...</span>
    `;

    try {

        const response = await fetch(
            `${API_URL}/auth/zoho/connect`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },

                body: JSON.stringify({
                    client_id: clientId,
                    client_secret: clientSecret
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Unable to start Zoho authorization."
            );
        }

        if (!data.authorization_url) {
            throw new Error(
                "Zoho authorization URL was not returned."
            );
        }

        // Redirect employee to Zoho.
        window.location.href =
            data.authorization_url;

    } catch (err) {

        console.error(
            "Zoho OAuth connection error:",
            err
        );

        errEl.innerText =
            err.message ||
            "Unable to connect Zoho CRM.";

        errEl.classList.remove("hidden");

        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function loadZohoStatus() {

    try {

        const response = await fetch(
            `${API_URL}/auth/zoho/status`,
            {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            return {
                connected: false
            };
        }

        const status =
            await response.json();

        updateZohoOAuthStatus(status);

        return status;

    } catch (err) {

        console.error(
            "Zoho status error:",
            err
        );

        return {
            connected: false
        };
    }
}
function updateZohoOAuthStatus(status) {

    const badge =
        document.getElementById(
            "zohoStatusBadge"
        );

    const button =
        document.getElementById(
            "connectZohoBtn"
        );

    if (!badge) {
        return;
    }

    if (status.connected) {

        badge.className =
            "status-indicator status-connected";

        badge.innerText =
            "CONNECTED";

        if (button) {

            button.innerHTML = `
                <span class="material-symbols-outlined">
                    check_circle
                </span>
                <span>Zoho CRM Connected</span>
            `;

        }

    } else {

        badge.className =
            "status-indicator status-disconnected";

        badge.innerText =
            "NOT CONNECTED";

        if (button) {

            button.innerHTML = `
                <span class="material-symbols-outlined">
                    link
                </span>
                <span>Connect Zoho CRM</span>
            `;

        }
    }
}
// ==============================================================================
// CONFIGURATION PAGE FLOW
// ==============================================================================

async function loadConfigFields() {

    try {

        const response = await fetch(
            `${API_URL}/config`,
            {
                headers: {
                    "Authorization":
                        `Bearer ${token}`
                }
            }
        );

        const status =
            await response.json();

        document.getElementById(
            "configGroqKey"
        ).placeholder =
            status.groq_masked || "No key configured";

        document.getElementById(
            "configGeminiKey"
        ).placeholder =
            status.gemini_masked || "No key configured";

        await loadZohoStatus();

    } catch (err) {

        console.error(
            "Error loading config status:",
            err
        );
    }
}

// Test Zoho/Groq/Gemini Connection
async function testConnection(type) {
    const groqKey = document.getElementById("configGroqKey").value;
    const geminiKey = document.getElementById("configGeminiKey").value;
    
    let btnId = "testZohoBtn";
    if (type === "groq") btnId = "testGroqBtn";
    else if (type === "gemini") btnId = "testGeminiBtn";
    const btn = document.getElementById(btnId);
    
    const errEl = document.getElementById("configError");
    const succEl = document.getElementById("configSuccess");
    
    errEl.classList.add("hidden");
    succEl.classList.add("hidden");
    
    const originalText = btn.innerText;
    btn.innerText = `Testing Connection...`;
    btn.disabled = true;

    try {
        let response, body;
        if (type === "groq") {
            body = { groq_api_key: groqKey || undefined };
            response = await fetch(`${API_URL}/config/test-groq`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(body)
            });
        } else {
            body = { gemini_api_key: geminiKey || undefined };
            response = await fetch(`${API_URL}/config/test-gemini`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify(body)
            });
        }

        const data = await response.json();

        if (!response.ok) {
            // Remember that the latest live test failed.
            liveTestStatus[type] = false;

            throw new Error(
                data.detail || "Connection validation failed."
            );
        }

        // Remember that the latest live test succeeded.
        liveTestStatus[type] = true;

        succEl.innerText = data.message;
        succEl.classList.remove("hidden");

        // Get current saved configuration.
        const configResp = await fetch(`${API_URL}/config`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const currentStatus = await configResp.json();

        // Get actual Zoho OAuth status separately.
        const zohoStatus = await loadZohoStatus();

        currentStatus.zoho_configured =
            !!zohoStatus.connected;

        updateConnectionStatusBadges(currentStatus);

    } catch (err) {
        errEl.innerText = err.message;
        errEl.classList.remove("hidden");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

// Config Save Submit
document.getElementById("configForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const groq_api_key =
        document.getElementById("configGroqKey").value;

    const gemini_api_key =
        document.getElementById("configGeminiKey").value;
    
    const errEl = document.getElementById("configError");
    const succEl = document.getElementById("configSuccess");
    
    errEl.classList.add("hidden");
    succEl.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/config/save`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                groq_api_key,
                gemini_api_key
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to save configuration.");
        }

        succEl.innerText = "Configuration saved successfully!";
        succEl.classList.remove("hidden");
        
        // Reload badges
        const configResp = await fetch(`${API_URL}/config`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const currentStatus = await configResp.json();
        updateConnectionStatusBadges(currentStatus);

        setTimeout(() => {
            switchView("chat");
            loadChatHistory();
        }, 1000);

    } catch (err) {
        errEl.innerText = err.message;
        errEl.classList.remove("hidden");
    }
});

function continueToChat() {
    switchView("chat");
    loadChatHistory();
}

// ==============================================================================
// CHAT OPERATION & HISTORY
// ==============================================================================

async function loadChatHistory() {
    try {
        const response = await fetch(`${API_URL}/sessions`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const sessions = await response.json();
        
        const historyList = document.getElementById("chatHistoryList");
        historyList.innerHTML = "";

        if (sessions.length === 0) {

            activeSessionId = null;

            document.getElementById("chatMessageList").innerHTML = "";

            document.getElementById("welcomePanel")
                .classList.remove("hidden");

            return;
        }

        sessions.forEach(session => {
            const item = document.createElement("div");
            item.className = "flex items-center justify-between group px-3 py-2.5 rounded-lg transition-colors cursor-pointer text-on-surface-variant hover:bg-surface-container-highest";
            item.setAttribute("data-session-id", session.id);
            
            // Set active color
            if (activeSessionId === session.id) {
                item.classList.add("text-primary", "font-bold", "bg-secondary-container");
                item.classList.remove("text-on-surface-variant");
            }

            item.innerHTML = `
                <div class="flex items-center gap-3 overflow-hidden flex-1" onclick="selectChatSession(${session.id})">
                    <span class="material-symbols-outlined text-[18px]">chat_bubble</span>
                    <span class="text-sm truncate pr-2">${session.title}</span>
                </div>
                <button class="text-on-surface-variant/40 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-0.5" onclick="deleteSession(${session.id}, event)">
                    <span class="material-symbols-outlined text-[16px]">delete</span>
                </button>
            `;

            historyList.appendChild(item);
        });

        // Set default selection if none active
        if (activeSessionId) {
            await selectChatSession(activeSessionId);
        }

        // Refresh connection badges
        const configResp = await fetch(`${API_URL}/config`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        const currentStatus = await configResp.json();

        const zohoStatus = await loadZohoStatus();

        currentStatus.zoho_configured =
            !!zohoStatus.connected;

        updateConnectionStatusBadges(currentStatus);

    } catch (err) {
        console.error("Failed to load chat history:", err);
    }
}

async function selectChatSession(sessionId) {
    activeSessionId = sessionId;
    sessionStorage.setItem("active_session_id", sessionId);
    
    // Highlight sidebar item
    document.querySelectorAll("#chatHistoryList > div").forEach(el => {
        if (parseInt(el.getAttribute("data-session-id")) === sessionId) {
            el.classList.add("text-primary", "font-bold", "bg-secondary-container");
            el.classList.remove("text-on-surface-variant");
        } else {
            el.classList.remove("text-primary", "font-bold", "bg-secondary-container");
            el.classList.add("text-on-surface-variant");
        }
    });

    // Clear Welcome panel and message areas
    document.getElementById("welcomePanel").classList.add("hidden");
    const messageList = document.getElementById("chatMessageList");
    messageList.innerHTML = "";

    try {
        const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!response.ok) {
            console.error("Session not found");
            if (response.status === 404) {
                await loadChatHistory();
            }
            return;
        }

        const data = await response.json();

        if (!data || !Array.isArray(data.messages)) {
            console.error("Invalid session response", data);
            return;
        }
        
        if (data.messages.length === 0) {
            // Show welcome instructions if session is empty
            document.getElementById("welcomePanel").classList.remove("hidden");
        } else {
            data.messages.forEach(msg => {

                if (msg.role === "user") {

                    appendMessageBubble(
                        "user",
                        msg.message
                    );

                }

                else if (msg.role === "assistant") {

                    if (msg.response_json) {

                        try {

                            const parsed = JSON.parse(msg.response_json);

                            if (typeof parsed === "string") {

                                appendAssistantResponse({
                                    response: parsed
                                });

                            } else {

                                appendAssistantResponse(parsed);

                            }

                        } catch {

                            appendAssistantResponse({
                                response: msg.message
                            });

                        }

                    } else {

                        appendAssistantResponse({
                            response: msg.message
                        });

                    }

                }

            });
        }
        
        scrollChatToBottom();
    } catch (err) {
        console.error("Error loading chat session:", err);
    }
}

async function startNewChat() {

    activeSessionId = null;
    sessionStorage.removeItem("active_session_id");

    document.getElementById("chatMessageList").innerHTML = "";

    document.getElementById("welcomePanel")
        .classList.remove("hidden");

    document.getElementById("chatInputField").value = "";
    document.getElementById("chatInputField").style.height = "auto";

    document.getElementById("chatInputField").focus();

    document.querySelectorAll("#chatHistoryList > div")
        .forEach(item => {
            item.classList.remove(
                "text-primary",
                "font-bold",
                "bg-secondary-container"
            );
            item.classList.add("text-on-surface-variant");
        });

    clearFileAttachment();
    document.getElementById("chatForm").reset();

    const input = document.getElementById("chatInputField");
    input.value = "";
    input.style.height = "auto";
    input.focus();
}

async function deleteSession(sessionId, event) {
    event.stopPropagation(); // prevent selecting the deleted session
    
    if (!confirm("Are you sure you want to delete this chat session?")) return;

    try {
        const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });
        
        if (response.ok) {
            if (activeSessionId === sessionId) {
                sessionStorage.removeItem("active_session_id");
                activeSessionId = null;
            }
            loadChatHistory();
        }
    } catch (err) {
        console.error("Failed to delete chat session:", err);
    }
}

// ==============================================================================
// PROMPT CHIPS & SPEECH & FILE ATTACHMENTS
// ==============================================================================

function fillSuggestedPrompt(text) {
    const input = document.getElementById("chatInputField");
    input.value = text;
    input.dispatchEvent(new Event("input")); // trigger auto-expand
    input.focus();
}
function submitSuggestedPrompt(text) {
    fillSuggestedPrompt(text);

    const chatForm = document.getElementById("chatForm");

    if (chatForm) {
        chatForm.requestSubmit();
    }
}

// Microphone Speech Recognition
// Microphone Speech Recording & Whisper Transcription Flow
function toggleMicrophone() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    const micBtn = document.getElementById("micBtn");
    const micIcon = document.getElementById("micIcon");
    
    audioChunks = [];
    recordingSeconds = 0;
    
    // Check MediaDevices compatibility
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Your browser does not support audio recording. Please use a modern browser like Chrome, Edge, or Safari.");
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            // Stop stream tracks to release microphone hardware
            stream.getTracks().forEach(track => track.stop());
            
            if (audioChunks.length === 0) {
                alert("Recording failed: no audio chunks recorded.");
                resetMicButtonState();
                return;
            }
            
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            if (audioBlob.size === 0) {
                alert("Recording is empty.");
                resetMicButtonState();
                return;
            }
            
            // Send the audio file to the backend
            await sendAudioToBackend(audioBlob);
        };
        
        mediaRecorder.start();
        isRecording = true;
        
        // UI Updates: turn red, change icon to stop
        micBtn.classList.add("mic-recording");
        micIcon.innerText = "stop";
        micBtn.title = "Stop Recording";
        
        showRecordingTimer();
        
    } catch (err) {
        console.error("Microphone access error:", err);
        alert("Microphone permission denied or unavailable. Please enable mic access in your browser settings to dictate.");
        resetMicButtonState();
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        resetMicButtonState();
        hideRecordingTimer();
    }
}

function resetMicButtonState() {
    const micBtn = document.getElementById("micBtn");
    const micIcon = document.getElementById("micIcon");
    if (micBtn && micIcon) {
        micBtn.classList.remove("mic-recording");
        micIcon.innerText = "mic";
        micBtn.title = "Voice Input";
    }
    isRecording = false;
}

function showRecordingTimer() {
    const overlay = document.getElementById("recordingTimerOverlay");
    const textarea = document.getElementById("chatInputField");
    const timerValue = document.getElementById("recordingTimerValue");
    const attachBtn = document.getElementById("attachBtn");
    const micBtn = document.getElementById("micBtn");
    const sendBtn = document.getElementById("sendBtn");
    
    if (overlay && textarea) {
        textarea.classList.add("hidden");
        overlay.classList.remove("hidden");
    }
    
    if (attachBtn) {
        attachBtn.disabled = true;
        attachBtn.classList.add("opacity-50", "pointer-events-none");
    }
    if (micBtn) {
        micBtn.classList.add("hidden");
    }
    if (sendBtn) {
        sendBtn.classList.add("hidden");
    }
    
    recordingSeconds = 0;
    if (timerValue) {
        timerValue.innerText = "00:00";
    }
    
    recordingInterval = setInterval(() => {
        recordingSeconds++;
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, "0");
        const secs = String(recordingSeconds % 60).padStart(2, "0");
        if (timerValue) {
            timerValue.innerText = `${mins}:${secs}`;
        }
    }, 1000);
}

function hideRecordingTimer() {
    const overlay = document.getElementById("recordingTimerOverlay");
    const textarea = document.getElementById("chatInputField");
    const attachBtn = document.getElementById("attachBtn");
    const micBtn = document.getElementById("micBtn");
    const sendBtn = document.getElementById("sendBtn");
    
    if (recordingInterval) {
        clearInterval(recordingInterval);
        recordingInterval = null;
    }
    
    if (overlay && textarea) {
        overlay.classList.add("hidden");
        textarea.classList.remove("hidden");
        textarea.focus();
    }
    
    if (attachBtn) {
        attachBtn.disabled = false;
        attachBtn.classList.remove("opacity-50", "pointer-events-none");
    }
    if (micBtn) {
        micBtn.classList.remove("hidden");
    }
    if (sendBtn) {
        sendBtn.classList.remove("hidden");
    }
}

async function sendAudioToBackend(audioBlob) {
    const micBtn = document.getElementById("micBtn");
    const micIcon = document.getElementById("micIcon");
    const inputField = document.getElementById("chatInputField");
    const sendBtn = document.getElementById("sendBtn");
    const attachBtn = document.getElementById("attachBtn");
    
    // Set mic button to spin loading state
    if (micIcon && micBtn) {
        micIcon.innerText = "sync";
        micBtn.classList.add("animate-spin");
        micBtn.disabled = true;
    }
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.classList.add("opacity-50", "pointer-events-none");
    }
    if (attachBtn) {
        attachBtn.disabled = true;
        attachBtn.classList.add("opacity-50", "pointer-events-none");
    }
    
    const formData = new FormData();
    // Groq Whisper supports WebM uploads directly
    formData.append("file", audioBlob, "recording.webm");
    
    try {
        const response = await fetch(`${API_URL}/transcribe`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Transcription service failed.");
        }
        
        if (data.text) {
            // Insert transcription directly into input field for review
            const existingValue = inputField.value.trim();
            inputField.value = existingValue ? `${existingValue} ${data.text}` : data.text;
            inputField.dispatchEvent(new Event("input")); // expand textarea size
            inputField.focus();
        } else {
            alert("No text transcribed from the audio.");
        }
    } catch (err) {
        console.error("Transcription error:", err);
        alert(`Transcription Failed: ${err.message}`);
    } finally {
        // Reset mic state
        if (micIcon && micBtn) {
            micIcon.innerText = "mic";
            micBtn.classList.remove("animate-spin");
            micBtn.disabled = false;
        }
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.classList.remove("opacity-50", "pointer-events-none");
        }
        if (attachBtn) {
            attachBtn.disabled = false;
            attachBtn.classList.remove("opacity-50", "pointer-events-none");
        }
    }
}

// File Attachment handling
function handleFileChange(event) {
    const file = event.target.files[0];
    if (!file) return;

    selectedFile = file;

    const preview = document.getElementById("fileUploadPreview");
    const nameLabel = document.getElementById("fileNameLabel");
    const sizeLabel = document.getElementById("fileSizeLabel");
    const fileIcon = document.getElementById("fileIcon");

    nameLabel.innerText = file.name;
    sizeLabel.innerText = `${(file.size / 1024).toFixed(1)} KB`;

    // Map extensions to icons
    const ext = file.name.split(".").pop().toLowerCase();
    if (["png", "jpg", "jpeg", "webp", "gif"].includes(ext)) {
        fileIcon.innerText = "image";
    } else if (["xlsx", "xls"].includes(ext)) {
        fileIcon.innerText = "table_chart";
    } else if (ext === "csv") {
        fileIcon.innerText = "csv";
    } else if (ext === "pdf") {
        fileIcon.innerText = "picture_as_pdf";
    } else {
        fileIcon.innerText = "description";
    }

    preview.classList.remove("hidden");
}

function clearFileAttachment() {
    selectedFile = null;
    document.getElementById("fileInput").value = "";
    document.getElementById("fileUploadPreview").classList.add("hidden");
}

// ==============================================================================
// CHAT SUBMISSION & SSE STREAMING FLOW
// ==============================================================================

function handleTextareaKeydown(event) {
    // Submit on Enter without shift key
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        document.getElementById("chatForm").requestSubmit();
    }
}

function disableChatControls() {
    const sendBtn = document.getElementById("sendBtn");
    const attachBtn = document.getElementById("attachBtn");
    const micBtn = document.getElementById("micBtn");
    const inputField = document.getElementById("chatInputField");
    
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.classList.add("opacity-50", "pointer-events-none");
    }
    if (attachBtn) {
        attachBtn.disabled = true;
        attachBtn.classList.add("opacity-50", "pointer-events-none");
    }
    if (micBtn) {
        micBtn.disabled = true;
        micBtn.classList.add("opacity-50", "pointer-events-none");
    }
    if (inputField) {
        inputField.disabled = true;
    }
}

function enableChatControls() {
    const sendBtn = document.getElementById("sendBtn");
    const attachBtn = document.getElementById("attachBtn");
    const micBtn = document.getElementById("micBtn");
    const inputField = document.getElementById("chatInputField");
    
    if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.classList.remove("opacity-50", "pointer-events-none");
    }
    if (attachBtn) {
        attachBtn.disabled = false;
        attachBtn.classList.remove("opacity-50", "pointer-events-none");
    }
    if (micBtn) {
        micBtn.disabled = false;
        micBtn.classList.remove("opacity-50", "pointer-events-none");
    }
    if (inputField) {
        inputField.disabled = false;
        inputField.focus();
    }
}

async function handleChatSubmit(event) {
    event.preventDefault();
    
    const input = document.getElementById("chatInputField");
    const prompt = input.value.trim().replace(/\n{3,}/g, "\n\n");
    
    if (!prompt && !selectedFile) return;

    // Create a session only when sending the first message
if (!activeSessionId) {

    const sessionResponse = await fetch(`${API_URL}/sessions/new`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (!sessionResponse.ok) {
        throw new Error("Unable to create chat session.");
    }

    const sessionData = await sessionResponse.json();

    activeSessionId = sessionData.session_id;
}

    // Reset UI state
    input.value = "";
    input.style.height = "auto";
    document.getElementById("welcomePanel").classList.add("hidden");

    // Form attachment prefix for bubble rendering
    let fileBubblePrefix = "";
    if (selectedFile) {
        fileBubblePrefix = `📎 [File Attached: ${selectedFile.name}]\n\n`;
    }

    // 1. Display User Message Bubble
    appendMessageBubble("user", `${fileBubblePrefix}${prompt}`);
    scrollChatToBottom();

    // 2. Display typing animation bubble
    const typingBubbleId = appendTypingIndicator();
    scrollChatToBottom();

    // Prepare Multipart Form Data
    const formData = new FormData();
    formData.append("session_id", activeSessionId);
    formData.append("prompt", prompt);
    if (selectedFile) {
        formData.append("file", selectedFile);
    }

    // Clear file attachment inputs
    clearFileAttachment();
    disableChatControls();

    let assistantBubbleId = null;
    let assistantResponseBuffer = "";

    try {
        // Call /chat with auth token and streaming body
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Chat generation failed.");
        }

        const typingEl = document.getElementById(typingBubbleId);
        if (typingEl) typingEl.remove();
        console.log("CHAT RESPONSE =", data);
        assistantBubbleId = appendAssistantResponse(data);

        scrollChatToBottom();

        await loadChatHistory();
        await selectChatSession(activeSessionId);

    } catch (err) {
        console.error("Submission error:", err);
        if (!assistantBubbleId) {
            const typingEl = document.getElementById(typingBubbleId);
            if (typingEl) typingEl.remove();
            assistantBubbleId = appendMessageBubble("assistant", "");
        }
        updateMessageBubbleContent(assistantBubbleId, `[System Error]: ${err.message}`, true);
        scrollChatToBottom();
    } finally {
        const typingEl = document.getElementById(typingBubbleId);
        if (typingEl) typingEl.remove();
        enableChatControls();
    }
}

// ==============================================================================
// DOM BUBBLE GENERATION AND RENDERING
// ==============================================================================

function scrollChatToBottom() {
    const area = document.getElementById("chatMessagesArea");
    area.scrollTop = area.scrollHeight;
}

function appendMessageBubble(role, message) {
    const list = document.getElementById("chatMessageList");
    const bubbleId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const wrapper = document.createElement("div");
    wrapper.className = `flex w-full ${role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`;
    wrapper.id = bubbleId;

    if (role === 'user') {
        wrapper.innerHTML = `
            <div class="relative max-w-[80%] bubble-user px-4 py-3 pr-9 flex flex-col group transition-all">
                <div class="text-sm leading-relaxed whitespace-pre-wrap" id="${bubbleId}-content">${message}</div>
                <div class="absolute right-2 bottom-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <button class="w-6 h-6 rounded-full flex items-center justify-center bg-white/15 hover:bg-white/25 text-white/90 hover:text-white cursor-pointer shadow-sm" onclick="copyBubbleText('${bubbleId}')" title="Copy Message">
                        <span class="material-symbols-outlined text-[13px]">content_copy</span>
                    </button>
                </div>
            </div>
        `;
        // Save the raw text to a custom property for copy action
        wrapper.setAttribute("data-raw-message", message);
    } else {
        const rawContent = message;
        // Parse markdown immediately for static items, else keep placeholder
        const parsedHtml = parseMarkdown(message);

        wrapper.innerHTML = `
            <div class="relative max-w-[90%] md:max-w-[80%] bubble-assistant px-4 py-3 pr-16 flex flex-col group transition-all">
                <div class="markdown-content text-sm text-on-surface leading-relaxed" id="${bubbleId}-content">
                    ${parsedHtml || "..."}
                </div>
                <div class="absolute right-2 bottom-2.5 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <button class="w-6 h-6 rounded-full flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-on-surface-variant hover:text-primary cursor-pointer shadow-sm" onclick="copyBubbleText('${bubbleId}')" title="Copy Message">
                        <span class="material-symbols-outlined text-[13px]">content_copy</span>
                    </button>
                    <button class="w-6 h-6 rounded-full flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-on-surface-variant hover:text-primary cursor-pointer shadow-sm" onclick="regenerateBubble('${bubbleId}')" title="Regenerate answer">
                        <span class="material-symbols-outlined text-[13px]">cached</span>
                    </button>
                </div>
            </div>
        `;
        
        // Save the raw text to a custom property for copy/regenerate actions
        wrapper.setAttribute("data-raw-message", rawContent);
    }

    list.appendChild(wrapper);
    return bubbleId;
}

function appendAssistantResponse(response) {
    const payload = response.response || response;

    const list = document.getElementById("chatMessageList");

    const bubbleId = `assistant-${Date.now()}`;

    const wrapper = document.createElement("div");

    wrapper.className =
        "flex w-full justify-start animate-fade-in";

    wrapper.id = bubbleId;

    let html = "";
    //--------------------------------------------------
    // GENERAL CHAT
    //--------------------------------------------------

    if (typeof response.response === "string") {

        html += `
        <div class="leading-7 text-sm">
            ${parseMarkdown(response.response)}
        </div>
        `;

    }

    //--------------------------------------------------
    // SUMMARY
    //--------------------------------------------------

    if (typeof payload.summary === "string") {

        html += `
        <div class="mb-5">

            <h3 class="font-bold text-primary mb-2">
                Summary
            </h3>

            <div class="text-sm leading-7">
                ${parseMarkdown(
                    typeof payload.summary === "string"
                        ? payload.summary
                        : JSON.stringify(payload.summary, null, 2)
                )}
            </div>

        </div>
        `;
    }

    //--------------------------------------------------
    // KPI CARDS
    //--------------------------------------------------

    if (payload.kpis) {

        html += `<div class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-5">`;

        Object.entries(payload.kpis).forEach(([key, value]) => {

            if (
                key === "module" ||
                typeof value === "object"
            ) return;

            const label = key
                .replace(/_/g, " ")
                .replace(/\b\w/g, c => c.toUpperCase());

            let displayValue = value;

            if (typeof value === "number") {

                // Currency values
                if (
                    key === "average_deal" ||
                    key === "pipeline_value" ||
                    key === "total_revenue"
                ) {

                    displayValue = "₹" + new Intl.NumberFormat("en-IN", {
                        minimumFractionDigits: key === "average_deal" ? 2 : 0,
                        maximumFractionDigits: key === "average_deal" ? 2 : 0
                    }).format(value);

                }

                // Percentage
                else if (key === "conversion_rate") {

                    displayValue = value.toFixed(2) + "%";

                }

                // Counts
                else {

                    displayValue = Math.round(value);

                }
            }

            // --------------------------
            // Dynamic font size
            // --------------------------
            const length = String(displayValue).length;

            let valueClass = "text-2xl";

            if (length > 10)
                valueClass = "text-xl";

            if (length > 14)
                valueClass = "text-lg";

            if (length > 18)
                valueClass = "text-base";

            if (length > 24)
                valueClass = "text-sm";

            html += `
            <div class="
                bg-white
                border
                rounded-xl
                p-4
                shadow-sm
                flex
                flex-col
                justify-between
                min-h-[110px]
                overflow-hidden
            ">

                <div class="text-xs text-gray-500 uppercase">
                    ${label}
                </div>

                <div
                    class="font-bold text-primary mt-2 whitespace-nowrap text-ellipsis overflow-hidden"
                    style="font-size: clamp(16px, 1.2vw, 28px);"
                    title="${displayValue}"
                >
                    ${displayValue}
                </div>

            </div>
            `;

        });

        html += `</div>`;
    }

    //--------------------------------------------------
    // TABLE
    //--------------------------------------------------

    if (payload.table) {

        const tableId = `table-${Date.now()}-${Math.random().toString(36).slice(2)}`;

        tableStates[tableId] = {
            columns: payload.table.columns,
            rows: payload.table.rows,
            page: 1
        };

        html += `
            <div id="${tableId}">
                ${renderCurrentTablePage(tableId)}
            </div>
        `;
    }

    //--------------------------------------------------
    // CHART
    //--------------------------------------------------

    if (payload.chart) {

        html += renderJSONVisualization(payload.chart);

    }

    else if (payload.type === "dashboard") {

        html += renderJSONVisualization(payload);

    }

    //--------------------------------------------------
    // SUGGESTIONS
    //--------------------------------------------------

    if (
        payload.suggestions &&
        payload.suggestions.length
    ) {

        html += `
        <div class="mt-5">

        <div class="text-xs font-bold uppercase mb-3">
            Follow-up Suggestions
        </div>

        <div class="flex flex-wrap gap-2">
        `;

        payload.suggestions.forEach(item => {

            html += `
            <button
                onclick="fillSuggestedPrompt('${item.replace(/'/g, "\\'")}')"
                class="px-3 py-2 rounded-full bg-primary/10 hover:bg-primary/20 text-primary text-sm">
                ${item}
            </button>
            `;

        });

        html += `
        </div>
        </div>
        `;
    }

    wrapper.innerHTML = `

        <div class="relative max-w-[90%] bubble-assistant px-4 py-3">

            ${html}

        </div>

    `;

    list.appendChild(wrapper);

    return bubbleId;

}

function updateMessageBubbleContent(bubbleId, newText, finalizeMarkdown = false) {
    const el = document.getElementById(`${bubbleId}-content`);
    const wrapper = document.getElementById(bubbleId);
    if (!el) return;

    if (finalizeMarkdown) {
        el.style.whiteSpace = ""; // Reset pre-wrap to prevent excessive spacing from HTML newlines
        el.innerHTML = parseMarkdown(newText);
        if (wrapper) wrapper.setAttribute("data-raw-message", newText);
    } else {
        // Streaming partial chunks - display plain text dynamically extracted from text_response field if JSON
        el.innerText = getStreamingDisplayText(newText);
        el.style.whiteSpace = "pre-wrap";
    }
}

function appendTypingIndicator() {
    const list = document.getElementById("chatMessageList");
    const bubbleId = `typing-${Date.now()}`;

    const wrapper = document.createElement("div");
    wrapper.className = `flex w-full justify-start animate-fade-in`;
    wrapper.id = bubbleId;
    wrapper.innerHTML = `
        <div class="bubble-assistant px-3 py-2 flex flex-col gap-1.5 justify-start min-w-[200px]">
            <div class="flex items-center gap-2">
                <div class="typing-dots scale-75 origin-left">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
                <span class="text-xs text-on-surface-variant/70 font-semibold" id="${bubbleId}-status">Preparing...</span>
            </div>
        </div>
    `;

    list.appendChild(wrapper);
    return bubbleId;
}

function updateTypingIndicatorStatus(bubbleId, text) {
    const el = document.getElementById(`${bubbleId}-status`);
    if (el) {
        el.innerText = text;
    }
}

function copyBubbleText(bubbleId) {
    const wrapper = document.getElementById(bubbleId);
    if (!wrapper) return;
    const rawText = wrapper.getAttribute("data-raw-message") || "";
    
    navigator.clipboard.writeText(rawText).then(() => {
        // Sleek checkmark feedback without alert box
        const btn = wrapper.querySelector("button[title='Copy Message']");
        if (btn) {
            const icon = btn.querySelector(".material-symbols-outlined");
            if (icon) {
                const oldIcon = icon.innerText;
                icon.innerText = "check";
                btn.classList.add("text-green-500");
                setTimeout(() => {
                    icon.innerText = oldIcon;
                    btn.classList.remove("text-green-500");
                }, 2000);
            }
        }
    }).catch(err => {
        console.error("Clipboard copy failed:", err);
    });
}

function copyTableToClipboard(tableContainerId) {
    const container = document.getElementById(tableContainerId);
    if (!container) return;
    const table = container.querySelector("table");
    if (!table) return;

    let text = "";
    const rows = Array.from(table.querySelectorAll("tr"));
    rows.forEach((row, rIndex) => {
        const cells = Array.from(row.querySelectorAll("th, td"));
        const cellTexts = cells.map(cell => cell.innerText.trim());
        text += cellTexts.join("\t") + (rIndex < rows.length - 1 ? "\n" : "");
    });

    navigator.clipboard.writeText(text).then(() => {
        const btn = container.querySelector(".copy-table-btn");
        if (btn) {
            const label = btn.querySelector(".btn-label");
            const icon = btn.querySelector(".material-symbols-outlined");
            if (label && icon) {
                const oldLabel = label.innerText;
                const oldIcon = icon.innerText;
                label.innerText = "Copied!";
                icon.innerText = "check";
                btn.classList.add("bg-green-500", "text-white", "border-green-500");
                btn.classList.remove("bg-white", "text-primary", "border-outline-variant");
                setTimeout(() => {
                    label.innerText = oldLabel;
                    icon.innerText = oldIcon;
                    btn.classList.remove("bg-green-500", "text-white", "border-green-500");
                    btn.classList.add("bg-white", "text-primary", "border-outline-variant");
                }, 2000);
            }
        }
    }).catch(err => {
        console.error("Failed to copy table:", err);
    });
}

function regenerateBubble(bubbleId) {
    const list = document.getElementById("chatMessageList");
    const bubbles = Array.from(list.children);
    const targetIdx = bubbles.findIndex(b => b.id === bubbleId);
    
    if (targetIdx === -1) return;

    let userPrompt = "";
    for (let i = targetIdx - 1; i >= 0; i--) {
        const b = bubbles[i];
        if (b.querySelector(".bubble-user")) {
            userPrompt = b.getAttribute("data-raw-message") || "";
            // Clean file attachment prefix if present
            userPrompt = userPrompt.replace(/📎 \[File Attached:[^\]]+\]\n\n/g, "").trim();
            break;
        }
    }

    if (!userPrompt) return;

    // Fill prompt box and resubmit
    fillSuggestedPrompt(userPrompt);
    document.getElementById("chatForm").requestSubmit();
}

// ==============================================================================
// SETTINGS MODAL INTERACTIONS
// ==============================================================================

async function openSettingsModal() {
    const modal = document.getElementById("settingsModal");
    const errEl = document.getElementById("settingsError");
    const succEl = document.getElementById("settingsSuccess");

    errEl.classList.add("hidden");
    succEl.classList.add("hidden");
    
    // Clear passwords inputs
    document.getElementById("settingsOldPassword").value = "";
    document.getElementById("settingsNewPassword").value = "";
    
    // Retrieve masked keys for settings view
    try {
        const response = await fetch(`${API_URL}/config`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const status = await response.json();
        const zohoStatus = await loadZohoStatus();

        const settingsZohoStatus =
            document.getElementById("settingsZohoStatus");

        const settingsZohoReconnectBtn =
            document.getElementById("settingsZohoReconnectBtn");

        if (settingsZohoStatus) {
            if (zohoStatus.connected) {
                settingsZohoStatus.className =
                    "status-indicator status-connected";
                settingsZohoStatus.innerText = "CONNECTED";
            } else {
                settingsZohoStatus.className =
                    "status-indicator status-disconnected";
                settingsZohoStatus.innerText = "NOT CONNECTED";
            }
        }

        if (settingsZohoReconnectBtn) {
            settingsZohoReconnectBtn.innerText =
                zohoStatus.connected ? "Reconnect" : "Connect";
        }
        
        const zohoKeyInput =
            document.getElementById("settingsZohoKey");

        const groqKeyInput =
            document.getElementById("settingsGroqKey");

        const geminiKeyInput =
            document.getElementById("settingsGeminiKey");

        if (zohoKeyInput) {
            zohoKeyInput.placeholder =
                status.zoho_masked || "No key configured";
        }

        if (groqKeyInput) {
            groqKeyInput.placeholder =
                status.groq_masked || "No key configured";
        }

        if (geminiKeyInput) {
            geminiKeyInput.placeholder =
                status.gemini_masked || "No key configured";
        }
    } catch (err) {
        console.error("Failed to load settings key states:", err);
    }

    modal.classList.remove("hidden");
}

async function reconnectZohoFromSettings() {

    const zohoStatus =
        await loadZohoStatus();

    if (zohoStatus.connected) {

        showConfirmationPopup({
            title: "Reconnect Zoho CRM",
            message: "Your Zoho CRM connection is already active. Do you want to reconnect it?",
            confirmText: "Reconnect",
            icon: "sync",
            action: () => {
                switchView("config");
            }
        });

        return;
    }

    switchView("config");
}

function closeSettingsModal() {
    document.getElementById("settingsModal").classList.add("hidden");
}

async function saveSettingsKeys(event) {
    event.preventDefault();
    const groq_api_key =
        document.getElementById("settingsGroqKey").value;

    const gemini_api_key =
        document.getElementById("settingsGeminiKey").value;
    
    const errEl = document.getElementById("settingsError");
    const succEl = document.getElementById("settingsSuccess");
    
    errEl.classList.add("hidden");
    succEl.classList.add("hidden");

    if (!groq_api_key && !gemini_api_key) {
        errEl.innerText = "Please enter at least one key to update.";
        errEl.classList.remove("hidden");
        return;
    }

    try {
        const body = {};

        if (groq_api_key) {
            body.groq_api_key = groq_api_key;
        }

        if (gemini_api_key) {
            body.gemini_api_key = gemini_api_key;
        }

        const response = await fetch(`${API_URL}/config/save`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Failed to save keys.");
        }

        succEl.innerText = "API keys updated successfully!";
        succEl.classList.remove("hidden");

        // Clear values
        document.getElementById("settingsZohoKey").value = "";
        document.getElementById("settingsGroqKey").value = "";
        document.getElementById("settingsGeminiKey").value = "";

        // Reload top indicators
        liveTestStatus.groq = null;
        liveTestStatus.gemini = null;
        const configResp = await fetch(`${API_URL}/config`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const status = await configResp.json();

        const zohoStatus = await loadZohoStatus();

        status.zoho_configured =
            !!zohoStatus.connected;

        updateConnectionStatusBadges(status);

    } catch (err) {
        errEl.innerText = err.message;
        errEl.classList.remove("hidden");
    }
}

async function saveSettingsPassword(event) {
    event.preventDefault();
    const old_password = document.getElementById("settingsOldPassword").value;
    const new_password = document.getElementById("settingsNewPassword").value;

    const errEl = document.getElementById("settingsError");
    const succEl = document.getElementById("settingsSuccess");
    
    errEl.classList.add("hidden");
    succEl.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/settings/change-password`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ old_password, new_password })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Failed to update password.");
        }

        succEl.innerText = "Password changed successfully!";
        succEl.classList.remove("hidden");

        document.getElementById("settingsOldPassword").value = "";
        document.getElementById("settingsNewPassword").value = "";

    } catch (err) {
        errEl.innerText = err.message;
        errEl.classList.remove("hidden");
    }
}

async function deleteEntireChatHistory() {
    if (!confirm("WARNING: This will permanently delete all chat sessions and messages for your account. Continue?")) {
        return;
    }

    const errEl = document.getElementById("settingsError");
    const succEl = document.getElementById("settingsSuccess");
    
    errEl.classList.add("hidden");
    succEl.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/sessions`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error("Failed to clear chat history.");
        }

        succEl.innerText = "All chat history cleared successfully!";
        succEl.classList.remove("hidden");

        // Reload everything
        activeSessionId = null;
        closeSettingsModal();
        loadChatHistory();

    } catch (err) {
        errEl.innerText = err.message;
        errEl.classList.remove("hidden");
    }
}

// ==============================================================================
// VANILLA MARKDOWN PARSER UTILS
// ==============================================================================

function stripMarkdownJson(text) {
    if (!text) return "";
    let clean = text.trim();
    // Remove leading ```json or ```
    clean = clean.replace(/^```json\s*/i, "");
    clean = clean.replace(/^```\s*/i, "");
    // Remove trailing ```
    clean = clean.replace(/\s*```$/i, "");
    return clean.trim();
}

function getStreamingDisplayText(text) {
    if (!text) return "";
    let clean = text.trim();
    
    // If it starts with a JSON object brace
    if (clean.startsWith("{")) {
        // Try to find the content of "text_response" using regex (dotAll equivalent to support newlines)
        const match = clean.match(/"text_response"\s*:\s*"((?:[^"\\]|\\(?:.|\n))*)/);
        if (match) {
            try {
                let parsedStr = match[1];
                parsedStr = parsedStr
                    .replace(/\\"/g, '"')
                    .replace(/\\n/g, '\n')
                    .replace(/\\t/g, '\t')
                    .replace(/\\\\/g, '\\');
                return parsedStr;
            } catch (e) {
                return "Analyzing CRM data...";
            }
        }
        return "Generating analytics report...";
    }
    
    // If the LLM output is plain text followed by a JSON block or visualizations array,
    // let's hide the raw JSON/bracket part of the stream to keep it clean!
    const braceIdx = clean.indexOf("{");
    const bracketIdx = clean.indexOf("[");
    const jsonStartIdx = (braceIdx !== -1 && bracketIdx !== -1) ? Math.min(braceIdx, bracketIdx) : (braceIdx !== -1 ? braceIdx : bracketIdx);
    
    if (jsonStartIdx !== -1) {
        return clean.substring(0, jsonStartIdx).trim();
    }
    
    return text;
}

function renderUnifiedResponse(json) {
    let html = "";
    
    // Fallback: If it's a JSON block but doesn't have text_response, let's build text_response from other keys!
    let text = json.text_response || "";
    if (!text) {
        if (json.summary) {
            text += `### Summary\n${json.summary}\n\n`;
        }
        if (json.insights) {
            text += `### Insights\n${json.insights}\n\n`;
        }
        if (json.recommendations) {
            text += `### Recommended Actions\n${json.recommendations}\n\n`;
        }
        if (json.message) {
            text += `${json.message}\n\n`;
        }
    }
    
    // 1. Render conversational text response first (using markdown parser)
    if (text) {
        html += `<div class="conversational-summary mb-4">${parseMarkdownTextOnly(text)}</div>`;
    }
    
    // 2. Render all visualizations sequentially
    if (json.visualizations && Array.isArray(json.visualizations)) {
        json.visualizations.forEach(vis => {
            html += renderJSONVisualization(vis);
        });
    } else if (json.visualization_type) {
        // Fallback for legacy format
        html += renderJSONVisualization(json);
    }
    
    return html;
}

function sanitizeJsonString(rawJson) {
    if (!rawJson) return "";
    let insideQuote = false;
    let escapeActive = false;
    let result = [];
    
    for (let i = 0; i < rawJson.length; i++) {
        let char = rawJson[i];
        
        if (char === '"' && !escapeActive) {
            insideQuote = !insideQuote;
            result.push(char);
        } else if (char === '\\' && insideQuote) {
            escapeActive = !escapeActive;
            result.push(char);
        } else {
            escapeActive = false;
            if (insideQuote) {
                if (char === '\n') {
                    result.push('\\n');
                } else if (char === '\r') {
                    result.push('\\r');
                } else if (char === '\t') {
                    result.push('\\t');
                } else {
                    result.push(char);
                }
            } else {
                result.push(char);
            }
        }
    }
    return result.join("");
}

function extractJsonBlockSimple(text) {
    if (!text) return null;
    let stripped = text.trim();
    const firstBrace = stripped.indexOf("{");
    const lastBrace = stripped.lastIndexOf("}");
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
        const candidate = stripped.substring(firstBrace, lastBrace + 1);
        try {
            return JSON.parse(candidate);
        } catch (e) {
            try {
                return JSON.parse(sanitizeJsonString(candidate));
            } catch (e2) {}
        }
    }
    return null;
}

function tryParseAndUnnest(jsonStr) {
    try {
        const json = JSON.parse(jsonStr);
        if (json && typeof json === "object") {
            // Unnest if double-wrapped
            if (json.text_response && typeof json.text_response === "string") {
                const innerTrimmed = json.text_response.trim();
                const innerJson = extractJsonBlockSimple(innerTrimmed);
                if (innerJson && typeof innerJson === "object" && (innerJson.text_response || innerJson.visualizations)) {
                    return innerJson;
                }
            }
            return json;
        }
    } catch (e) {}
    return null;
}

function extractJsonBlock(text) {
    if (!text) return null;
    let cleaned = text.trim();
    
    // 1. Try standard JSON parse on full text first
    let json = tryParseAndUnnest(cleaned);
    if (json) return json;
    
    // 2. Try stripping markdown blocks first
    let stripped = stripMarkdownJson(cleaned);
    json = tryParseAndUnnest(stripped);
    if (json) return json;
    
    // 3. Find outermost curly braces {...}
    const firstBrace = stripped.indexOf("{");
    const lastBrace = stripped.lastIndexOf("}");
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
        const candidate = stripped.substring(firstBrace, lastBrace + 1);
        json = tryParseAndUnnest(candidate);
        if (json) return json;
        
        const sanitized = sanitizeJsonString(candidate);
        json = tryParseAndUnnest(sanitized);
        if (json) return json;
    }
    
    // 4. Find outermost brackets [...] representing a raw visualizations list
    const firstBracket = stripped.indexOf("[");
    const lastBracket = stripped.lastIndexOf("]");
    if (firstBracket !== -1 && lastBracket !== -1 && lastBracket > firstBracket) {
        const candidate = stripped.substring(firstBracket, lastBracket + 1);
        
        const parseRobustTextResponse = (raw) => {
            const match = raw.match(/"text_response"\s*:\s*"((?:[^"\\]|\\(?:.|\n))*)/);
            if (match) {
                try {
                    return match[1]
                        .replace(/\\"/g, '"')
                        .replace(/\\n/g, '\n')
                        .replace(/\\t/g, '\t')
                        .replace(/\\\\/g, '\\');
                } catch (e) {}
            }
            let rawText = raw.substring(0, firstBracket).trim();
            if (rawText.startsWith("{")) {
                const simpleMatch = rawText.match(/"text_response"\s*:\s*"([^"]*)"/);
                if (simpleMatch) return simpleMatch[1];
                return "Here are the retrieved Zoho CRM records:";
            }
            return rawText;
        };

        try {
            const parsed = JSON.parse(candidate);
            if (Array.isArray(parsed)) {
                return {
                    intent_detected: "crm_query",
                    text_response: parseRobustTextResponse(stripped),
                    visualizations: parsed
                };
            }
        } catch (e) {}
        
        try {
            const sanitized = sanitizeJsonString(candidate);
            const parsed = JSON.parse(sanitized);
            if (Array.isArray(parsed)) {
                return {
                    intent_detected: "crm_query",
                    text_response: parseRobustTextResponse(stripped),
                    visualizations: parsed
                };
            }
        } catch (e) {}
    }
    
    // 5. Fallback: Robust regex-based extraction to prevent ever displaying raw JSON!
    if (stripped.includes("intent_detected") || stripped.includes("text_response")) {
        let intent = "general_chat";
        let text_response = "";
        let visualizations = [];
        
        const intentMatch = stripped.match(/"intent_detected"\s*:\s*"([^"]*)"/);
        if (intentMatch) {
            intent = intentMatch[1];
        }
        
        const textMatch = stripped.match(/"text_response"\s*:\s*"((?:[^"\\]|\\.)*)/);
        if (textMatch) {
            try {
                text_response = textMatch[1]
                    .replace(/\\"/g, '"')
                    .replace(/\\n/g, '\n')
                    .replace(/\\t/g, '\t')
                    .replace(/\\\\/g, '\\');
            } catch (e) {
                text_response = textMatch[1];
            }
        }
        
        const visMatch = stripped.match(/"visualizations"\s*:\s*(\[[\s\S]*\])/);
        if (visMatch) {
            try {
                visualizations = JSON.parse(visMatch[1]);
            } catch (e) {
                try {
                    const sanitizedVis = sanitizeJsonString(visMatch[1]);
                    visualizations = JSON.parse(sanitizedVis);
                } catch (e2) {}
            }
        }
        
        return {
            intent_detected: intent,
            text_response: text_response,
            visualizations: visualizations
        };
    }
    
    return null;
}

function parseMarkdown(text) {
    if (!text) return "";
    
    const json = extractJsonBlock(text);
    if (json) {
        const rendered = renderUnifiedResponse(json);
        if (rendered) return rendered;
        
        // If it was parsed as JSON, but renderUnifiedResponse returned nothing,
        // let's show a formatted bold-key fallback instead of raw JSON!
        let fallbackText = "";
        for (let key in json) {
            if (key !== "intent_detected" && key !== "visualizations" && typeof json[key] === "string") {
                fallbackText += `**${key.charAt(0).toUpperCase() + key.slice(1)}**: ${json[key]}\n\n`;
            }
        }
        if (fallbackText) return parseMarkdownTextOnly(fallbackText);
        return "CRM data loaded successfully.";
    }
    
    // If it looks like a raw JSON response (starts with { and has intent_detected / text_response / summary / insights / recommendations)
    // but extractJsonBlock failed, let's extract the key values using a fallback regex anyway
    // so we never display raw JSON!
    let cleaned = text.trim();
    if (cleaned.startsWith("{") && (cleaned.includes("intent_detected") || cleaned.includes("text_response") || cleaned.includes("summary") || cleaned.includes("insights") || cleaned.includes("recommendations"))) {
        // Try to match text_response, summary, insights, or recommendations
        const matchKeys = ["text_response", "summary", "insights", "recommendations", "message"];
        let extractedText = "";
        for (let key of matchKeys) {
            const regex = new RegExp(`"${key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"`);
            const match = cleaned.match(regex);
            if (match) {
                try {
                    let val = match[1]
                        .replace(/\\"/g, '"')
                        .replace(/\\n/g, '\n')
                        .replace(/\\t/g, '\t')
                        .replace(/\\\\/g, '\\');
                    extractedText += `### ${key.charAt(0).toUpperCase() + key.slice(1)}\n${val}\n\n`;
                } catch (e) {
                    extractedText += `### ${key.charAt(0).toUpperCase() + key.slice(1)}\n${match[1]}\n\n`;
                }
            }
        }
        if (extractedText) return parseMarkdownTextOnly(extractedText);
        return "An error occurred while parsing the CRM data response.";
    }
    
    return parseMarkdownTextOnly(text);
}

function parseMarkdownTextOnly(text) {
    if (!text) return "";
    
    // Standard Markdown Parser
    let lines = text.split("\n");
    let result = [];
    let inList = false;
    let inOrderedList = false;
    let inSuggestionsList = false;
    let inCode = false;
    let codeBlock = [];
    let inTable = false;
    let tableRows = [];
    let currentParagraph = [];

    const flushParagraph = () => {
        if (currentParagraph.length > 0) {
            result.push(`
                <p class="leading-6 mb-2">
                    ${parseInlineMarkdown(currentParagraph.join(" "))}
                </p>
            `);
            currentParagraph = [];
        }
    };

    for (let line of lines) {
        let lTrimmed = line.trim();

        // If in suggestions list and we hit a non-list line, close suggestions container
        if (inSuggestionsList && !lTrimmed.startsWith("- ") && !lTrimmed.startsWith("* ") && lTrimmed !== "") {
            result.push("</div>");
            inSuggestionsList = false;
        }

        if (lTrimmed.startsWith("```")) {
            flushParagraph();
            if (inCode) {
                inCode = false;
                result.push(`<pre><code>${codeBlock.join("\n")}</code></pre>`);
                codeBlock = [];
            } else {
                inCode = true;
            }
            continue;
        }
        
        if (inCode) {
            codeBlock.push(line);
            continue;
        }

        if (/^\s*<\/?[a-zA-Z]/.test(line)) {
            flushParagraph();
            result.push(line);
            continue;
        }

        if (lTrimmed.startsWith("|")) {
            flushParagraph();
            inTable = true;
            tableRows.push(line);
            continue;
        } else if (inTable) {
            inTable = false;
            result.push(renderTable(tableRows));
            tableRows = [];
        }

        let headerMatch = line.match(/^(#{1,6})\s+(.*)$/);
        if (headerMatch) {
            flushParagraph();
            let level = headerMatch[1].length;
            let content = headerMatch[2];
            result.push(`<h${level}>${parseInlineMarkdown(content)}</h${level}>`);
            continue;
        }

        // Detect "Follow-up Suggestions" header and start chips container
        if (lTrimmed.toLowerCase().includes("follow-up suggestions")) {
            flushParagraph();
            result.push(`<div class="text-xs font-bold text-on-surface-variant/80 uppercase tracking-wider mb-2 mt-4">Follow-up Suggestions</div>`);
            result.push(`<div class="flex flex-wrap gap-2 mt-1.5">`);
            inSuggestionsList = true;
            continue;
        }

        // 1. Check for bullet list matching: starts with -, *, or •
        let bulletMatch = line.match(/^\s*[-*•]\s+(.*)$/);
        if (bulletMatch) {
            flushParagraph();
            if (inOrderedList) {
                inOrderedList = false;
                result.push("</ol>");
            }
            let content = bulletMatch[1].trim();
            if (inSuggestionsList) {
                let fillText = content;
                const boldMatch = content.match(/\*\*(.*?)\*\*/);
                if (boldMatch) {
                    fillText = boldMatch[1];
                }
                const escapedFill = fillText.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
                result.push(`<button type="button" class="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-full text-xs font-semibold cursor-pointer transition-all active:scale-95 mb-2 mr-2" onclick="fillSuggestedPrompt('${escapedFill}')">${parseInlineMarkdown(content)}</button>`);
            } else {
                if (!inList) {
                    inList = true;
                    result.push("<ul>");
                }
                result.push(`<li>${parseInlineMarkdown(content)}</li>`);
            }
            continue;
        }

        // 2. Check for numbered list matching: starts with digits like 1. 2.
        let numberMatch = line.match(/^\s*(\d+)\.\s+(.*)$/);

        if (numberMatch) {

            flushParagraph();

            if (inList) {
                inList = false;
                result.push("</ul>");
            }

            const number = numberMatch[1];
            const content = numberMatch[2].trim();

            result.push(`
                <div class="flex items-start gap-3 mb-0">
                    <div class="font-bold text-primary min-w-[22px] leading-6">
                        ${number}.
                    </div>
                    <div class="leading-6">
                        ${parseInlineMarkdown(content)}
                    </div>
                </div>
            `);

            continue;
        }

        // Close list tags if we hit a normal line
        if (inList) {
            inList = false;
            result.push("</ul>");
        }

        if (lTrimmed === "") {
            flushParagraph();
        }
        else if (lTrimmed.startsWith("Company:")) {

            flushParagraph();

            result.push(`
                <div class="ml-[34px] mb-3 leading-6 text-gray-700">
                    ${parseInlineMarkdown(lTrimmed)}
                </div>
            `);

        }
        else {
            currentParagraph.push(line);
        }
    }

    flushParagraph();
    if (inList) result.push("</ul>");
    if (inSuggestionsList) result.push("</div>");
    if (inTable) result.push(renderTable(tableRows));
    if (inCode) result.push(`<pre><code>${codeBlock.join("\n")}</code></pre>`);

    return result.join("\n");
}

function formatIndianCurrencyJS(amount) {
    const val = Math.abs(amount);
    const s = val.toFixed(2);
    const parts = s.split(".");
    let integerPart = parts[0];
    const decimalPart = parts[1];
    
    let intFormatted = "";
    if (integerPart.length <= 3) {
        intFormatted = integerPart;
    } else {
        const lastThree = integerPart.substring(integerPart.length - 3);
        let remaining = integerPart.substring(0, integerPart.length - 3);
        const groups = [];
        while (remaining.length > 0) {
            if (remaining.length >= 2) {
                groups.unshift(remaining.substring(remaining.length - 2));
                remaining = remaining.substring(0, remaining.length - 2);
            } else {
                groups.unshift(remaining);
                remaining = "";
            }
        }
        intFormatted = groups.join(",") + "," + lastThree;
    }
    
    return (amount < 0 ? "-" : "") + "₹" + intFormatted + "." + decimalPart;
}

// Router to render Zoho Assistant JSON responses dynamically
function renderJSONVisualization(json) {
    // Convert backend analytics format to frontend format
    if (!json.visualization_type && json.type) {

        json.visualization_type = json.type;

        json.chart_metadata = {
            title: json.title || "Analytics"
        };

        if (json.labels && json.values) {

            json.data = json.labels.map((label, index) => ({
                label: label,
                value: json.values[index]
            }));

        }
    }
    const type = json.visualization_type;
    const title = json.chart_metadata?.title || json.intent_detected || "CRM Analytics";
    const containerId = `chart-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

    // ----------------------------
    // Dashboard
    // ----------------------------

    if (type === "dashboard") {

        let html = "";

        if (json.charts && json.charts.length) {

            json.charts.forEach(chart => {

                html += renderJSONVisualization(chart);

            });

        }

        return html;

    }

    if (type === "text") {
        return `<p class="font-medium text-on-surface">${json.text_response || "No response provided."}</p>`;
    }

    if (type === "kpi_cards") {
        let cardsHtml = `<div class="font-bold text-primary text-xs uppercase mb-3 tracking-wider">${title}</div>`;
        cardsHtml += `<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 my-3">`;
        json.data.forEach(card => {
            let val = String(card.value !== null && card.value !== undefined ? card.value : "");
            
            // 1. Format Currency if applicable
            const labelLower = card.label.toLowerCase();
            if (labelLower.includes("amount") || labelLower.includes("revenue") || labelLower.includes("budget") || labelLower.includes("cost") || labelLower.includes("closing_rate")) {
                const num = parseFloat(val.replace(/[^\d.]/g, ""));
                if (!isNaN(num)) {
                    val = formatIndianCurrencyJS(num);
                }
            }
            
            // 2. Format ISO Timestamps/Dates
            if (val.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
                try {
                    const d = new Date(val);
                    val = d.toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit"
                    });
                } catch(e) {}
            } else if (val.match(/^\d{4}-\d{2}-\d{2}$/)) {
                try {
                    const d = new Date(val);
                    val = d.toLocaleDateString("en-IN", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric"
                    });
                } catch(e) {}
            }
            
            // 3. Dynamic Font Size based on value length to prevent overflow
            let fontSizeClass = "text-xl";
            if (val.length > 25) {
                fontSizeClass = "text-xs break-all";
            } else if (val.length > 15) {
                fontSizeClass = "text-sm break-words";
            } else if (val.length > 10) {
                fontSizeClass = "text-base";
            }
            
            // 4. Determine Card Column Span
            let colSpan = "";
            if (val.length > 25 || labelLower.includes("website") || labelLower.includes("email") || labelLower.includes("activity") || labelLower.includes("closing date") || labelLower.includes("modified")) {
                colSpan = "sm:col-span-2 md:col-span-3";
            }
            
            cardsHtml += `
                <div class="bg-white border border-outline-variant/60 rounded-xl p-3.5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-primary/30 transition-all duration-200 ${colSpan}">
                    <div class="text-[10px] font-bold text-on-surface-variant/70 uppercase tracking-wider">${card.label}</div>
                    <div class="${fontSizeClass} font-bold text-primary mt-1.5 leading-snug">${val}</div>
                </div>
            `;
        });
        cardsHtml += `</div>`;
        return cardsHtml;
    }

    if (type === "table") {
        let cols = json.columns || [];
        let rows = json.data || [];
        const tableContainerId = `table-container-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        let tableHtml = `<div id="${tableContainerId}" class="my-4">`;
        tableHtml += `<div class="flex justify-between items-center mb-2">`;
        tableHtml += `<div class="font-bold text-primary text-xs uppercase tracking-wider">${title}</div>`;
        tableHtml += `<button type="button" class="copy-table-btn flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-gray-50 border border-outline-variant rounded-lg text-xs font-semibold text-primary shadow-sm hover:shadow active:scale-95 cursor-pointer transition-all" onclick="copyTableToClipboard('${tableContainerId}')">`;
        tableHtml += `<span class="material-symbols-outlined text-[14px]">content_copy</span>`;
        tableHtml += `<span class="btn-label">Copy Table</span>`;
        tableHtml += `</button>`;
        tableHtml += `</div>`;
        tableHtml += `<div class="overflow-x-auto border border-outline-variant rounded-xl shadow-sm bg-white">`;
        tableHtml += `<table class="min-w-full divide-y divide-outline-variant">`;
        tableHtml += `<thead class="bg-surface-container"><tr>`;
        cols.forEach(col => {
            tableHtml += `<th class="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wider">${parseInlineMarkdown(String(col))}</th>`;
        });
        tableHtml += `</tr></thead><tbody class="divide-y divide-outline-variant">`;
        rows.forEach(row => {
            tableHtml += `<tr>`;
            row.forEach(cell => {
                const cellVal = cell !== null && cell !== undefined ? String(cell) : "";
                tableHtml += `<td class="px-4 py-3 text-sm text-on-surface">${parseInlineMarkdown(cellVal)}</td>`;
            });
            tableHtml += `</tr>`;
        });
        tableHtml += `</tbody></table></div></div>`;
        return tableHtml;
    }

    // Chart.js based visualizations (bar, bar_stacked, line, pie, scatter)
    if (["bar", "bar_stacked", "line", "pie", "scatter"].includes(type)) {
        // We create a canvas block. Chart will be initialized dynamically in micro-task
        setTimeout(() => initChartInstance(containerId, json), 50);
        
        return `
            <div class="w-full bg-white border border-outline-variant rounded-xl p-4 shadow-sm my-3">
                <div class="text-xs font-bold text-primary uppercase tracking-wider mb-4 text-center">${title}</div>
                <div class="relative h-[240px]">
                    <canvas id="${containerId}"></canvas>
                </div>
            </div>
        `;
    }

    // Funnel visualization
    if (type === "funnel") {
        let funnelHtml = `<div class="font-bold text-primary text-xs uppercase mb-3 tracking-wider">${title}</div>`;
        funnelHtml += `<div class="flex flex-col gap-2 my-3 max-w-[500px] mx-auto">`;
        
        const maxVal = json.data.length > 0 ? Math.max(...json.data.map(d => d.value)) : 1;
        json.data.forEach((item, index) => {
            const widthPct = maxVal > 0 ? (item.value / maxVal) * 100 : 0;
            const colors = ["#0051cb", "#0067ff", "#297eff", "#5ca0ff", "#8ec1ff", "#c0e2ff"];
            const color = colors[index % colors.length];
            funnelHtml += `
                <div class="flex items-center gap-3">
                    <div class="w-24 text-xs font-semibold text-on-surface truncate text-right">${item.stage}</div>
                    <div class="flex-1 bg-surface-container-low h-8 rounded-lg overflow-hidden relative border border-outline-variant/30">
                        <div class="h-full rounded-r-lg flex items-center px-3 text-white text-xs font-bold transition-all duration-500" style="width: ${widthPct}%; background-color: ${color};">
                            ${item.value}
                        </div>
                    </div>
                </div>
            `;
        });
        funnelHtml += `</div>`;
        return funnelHtml;
    }

    // Heatmap visualization (Retention/density grid)
    if (type === "heatmap") {
        let heatmapHtml = `<div class="font-bold text-primary text-xs uppercase mb-3 tracking-wider">${title}</div>`;
        heatmapHtml += `<div class="overflow-x-auto bg-white border border-outline-variant rounded-xl p-4 my-3 shadow-sm">`;
        heatmapHtml += `<div class="grid grid-cols-5 gap-2 max-w-[400px] mx-auto">`;
        
        json.data.forEach(item => {
            const intensityColor = `rgba(0, 81, 203, ${Math.min(item.intensity, 1)})`;
            const textColor = item.intensity > 0.5 ? "#ffffff" : "#131b2e";
            heatmapHtml += `
                <div class="aspect-square flex flex-col justify-between p-2 rounded border border-outline-variant/40 text-center" style="background-color: ${intensityColor}; color: ${textColor};">
                    <span class="text-[9px] uppercase tracking-wider opacity-60">${item.column}</span>
                    <span class="text-xs font-bold">${item.row}</span>
                    <span class="text-[9px] font-semibold opacity-70">${item.intensity}</span>
                </div>
            `;
        });
        heatmapHtml += `</div></div>`;
        return heatmapHtml;
    }

    // Waterfall visualization (Financial summary increments/decrements)
    if (type === "waterfall") {
        let waterfallHtml = `<div class="font-bold text-primary text-xs uppercase mb-3 tracking-wider">${title}</div>`;
        waterfallHtml += `<div class="flex flex-col gap-2 my-3">`;
        
        const maxVal = json.data.length > 0 ? Math.max(...json.data.map(d => Math.abs(d.amount))) : 1;
        json.data.forEach(item => {
            const pct = maxVal > 0 ? (Math.abs(item.amount) / maxVal) * 100 : 0;
            let barColor = "#0051cb"; // start / total
            if (item.type === "gain") barColor = "#2e7d32"; // Green
            if (item.type === "loss") barColor = "#c62828"; // Red
            
            waterfallHtml += `
                <div class="flex items-center justify-between text-xs border-b border-outline-variant/10 py-1.5">
                    <span class="font-semibold text-on-surface-variant w-28 truncate">${item.label}</span>
                    <div class="flex-1 bg-surface-container h-4 rounded overflow-hidden mx-3 relative max-w-[300px]">
                        <div class="h-full rounded" style="width: ${pct}%; background-color: ${barColor};"></div>
                    </div>
                    <span class="font-bold text-right w-20 ${item.type === 'gain' ? 'text-green-600' : item.type === 'loss' ? 'text-red-600' : 'text-primary'}">$${item.amount.toLocaleString()}</span>
                </div>
            `;
        });
        waterfallHtml += `</div>`;
        return waterfallHtml;
    }

    return `<pre class="bg-surface-container text-xs p-3 rounded overflow-x-auto"><code>${JSON.stringify(json, null, 2)}</code></pre>`;
}

// Chart.js initialization callback handler
function initChartInstance(canvasId, json) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    try {
        if (typeof Chart === "undefined") {
            throw new Error("Chart.js library is not loaded. Please check your internet connection.");
        }

        const type = json.visualization_type;
        const labels = json.data.map(d => d.label || d.stage || "");
        const values = json.data.map(d => d.value);

        let chartType = "bar";
        let datasets = [];
        let options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: type === "pie" }
            },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { borderDash: [2, 2] } }
            }
        };

        if (type === "bar" || type === "bar_stacked") {
            chartType = "bar";
            datasets = [{
                label: json.chart_metadata?.y_axis_label || "Value",
                data: values,
                backgroundColor: "#0051cb",
                borderRadius: 6
            }];
            
            if (type === "bar_stacked") {
                options.scales.x.stacked = true;
                options.scales.y.stacked = true;
            }

            // Dynamically choose orientation based on metadata or label length
            const maxLabelLength = labels.reduce((max, label) => Math.max(max, String(label).length), 0);
            if (json.chart_metadata?.orientation === 'horizontal' || maxLabelLength > 12) {
                options.indexAxis = 'y';
                options.scales = {
                    x: { grid: { borderDash: [2, 2] } },
                    y: { grid: { display: false } }
                };
            }
        } else if (type === "line") {
            chartType = "line";
            datasets = [{
                label: json.chart_metadata?.y_axis_label || "Trend",
                data: values,
                borderColor: "#0051cb",
                backgroundColor: "rgba(0, 81, 203, 0.05)",
                fill: true,
                tension: 0.3,
                borderWidth: 2.5,
                pointRadius: 4
            }];
        } else if (type === "pie") {
            chartType = "doughnut";
            datasets = [{
                data: values,
                backgroundColor: ["#0051cb", "#0067ff", "#297eff", "#5ca0ff", "#8ec1ff", "#c0e2ff", "#e0efff"]
            }];
            options.scales = {}; // Donut charts don't use cartesian scales
        } else if (type === "scatter") {
            chartType = "scatter";
            datasets = [{
                label: "Relationship",
                data: json.data.map(d => ({ x: d.x, y: d.y })),
                backgroundColor: "#0051cb",
                pointRadius: 6
            }];
            options.plugins.tooltip = {
                callbacks: {
                    label: function(context) {
                        const idx = context.dataIndex;
                        const item = json.data[idx];
                        return `${item.label || 'Point'}: (${item.x}, ${item.y})`;
                    }
                }
            };
        }

        new Chart(ctx, {
            type: chartType,
            data: {
                labels: labels,
                datasets: datasets
            },
            options: options
        });
    } catch (err) {
        console.error("Failed to render Chart.js visualization:", err);
        const container = ctx.parentElement;
        if (container) {
            container.innerHTML = `
                <div class="text-xs text-red-500 font-semibold mb-2">⚠️ Chart rendering fallback: ${err.message}</div>
                <div class="overflow-x-auto border border-outline-variant rounded-lg p-2 bg-gray-50">
                    <table class="min-w-full text-xs text-on-surface">
                        <thead>
                            <tr class="border-b border-outline-variant">
                                <th class="text-left font-bold py-1 pr-4">Label</th>
                                <th class="text-right font-bold py-1">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${json.data ? json.data.map(d => `
                                <tr class="border-b border-outline-variant/30">
                                    <td class="py-1 pr-4">${d.label || d.stage || d.x || ''}</td>
                                    <td class="text-right py-1">${d.value !== undefined ? d.value : d.y}</td>
                                </tr>
                            `).join('') : '<tr><td colspan="2" class="py-1">No data points available</td></tr>'}
                        </tbody>
                    </table>
                </div>
            `;
        }
    }
}

function parseInlineMarkdown(text) {
    let parsed = text;
    parsed = parsed.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    parsed = parsed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    parsed = parsed.replace(/`([^`]+)`/g, '<code>$1</code>');
    parsed = parsed.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="text-primary hover:underline font-semibold">$1</a>');
    return parsed;
}

function renderTable(rows) {
    if (rows.length < 1) return "";
    
    const tableContainerId = `table-container-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    let tableHtml = `<div id="${tableContainerId}" class="my-4">`;
    tableHtml += `<div class="flex justify-end mb-2">`;
    tableHtml += `<button type="button" class="copy-table-btn flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-gray-50 border border-outline-variant rounded-lg text-xs font-semibold text-primary shadow-sm hover:shadow active:scale-95 cursor-pointer transition-all" onclick="copyTableToClipboard('${tableContainerId}')">`;
    tableHtml += `<span class="material-symbols-outlined text-[14px]">content_copy</span>`;
    tableHtml += `<span class="btn-label">Copy Table</span>`;
    tableHtml += `</button>`;
    tableHtml += `</div>`;
    tableHtml += `<div class="overflow-x-auto border border-outline-variant rounded-xl shadow-sm bg-white"><table class="min-w-full"><thead><tr>`;
    
    // Parse headers
    let headers = rows[0].split("|").slice(1, -1).map(h => h.trim());
    headers.forEach(h => {
        tableHtml += `<th class="px-4 py-3 text-left text-xs font-semibold text-primary uppercase tracking-wider">${parseInlineMarkdown(h || "")}</th>`;
    });
    tableHtml += "</tr></thead><tbody class=\"divide-y divide-outline-variant\">";
    
    let startIdx = 1;
    if (rows[1] && rows[1].includes("-")) {
        startIdx = 2; // skip header separator like |---|---|
    }
    
    for (let i = startIdx; i < rows.length; i++) {
        let cells = rows[i].split("|").slice(1, -1).map(c => c.trim());
        tableHtml += "<tr>";
        // Ensure same cell count as header
        for (let j = 0; j < headers.length; j++) {
            tableHtml += `<td class="px-4 py-3 text-left text-sm text-on-surface">${parseInlineMarkdown(cells[j] || "")}</td>`;
        }
        tableHtml += "</tr>";
    }
    tableHtml += "</tbody></table></div></div>";
    return tableHtml;
}
function renderCurrentTablePage(tableId) {

    const state = tableStates[tableId];

    if (!state) return "";

    const start = (state.page - 1) * ROWS_PER_PAGE;
    const end = start + ROWS_PER_PAGE;

    const rows = state.rows.slice(start, end);

    let html = renderJSONVisualization({
        visualization_type: "table",
        chart_metadata: {
            title: "Results"
        },
        columns: state.columns,
        data: rows
    });

    html += renderClientPagination(tableId);

    return html;
}

function renderClientPagination(tableId) {

    const state = tableStates[tableId];

    const totalPages =
        Math.ceil(state.rows.length / ROWS_PER_PAGE);

    return `
    <div class="flex justify-between items-center mt-4">

        <button
            onclick="changeTablePage('${tableId}',-1)"
            ${state.page===1?"disabled":""}
            class="px-4 py-2 border rounded">

            ◀ Previous

        </button>

        <div>

            Page ${state.page} of ${totalPages}

        </div>

        <button
            onclick="changeTablePage('${tableId}',1)"
            ${state.page===totalPages?"disabled":""}
            class="px-4 py-2 border rounded">

            Next ▶

        </button>

    </div>
    `;
}

function changeTablePage(tableId, step) {

    const state = tableStates[tableId];

    if (!state) return;

    const totalPages =
        Math.ceil(state.rows.length / ROWS_PER_PAGE);

    const newPage = state.page + step;

    if (newPage < 1 || newPage > totalPages)
        return;

    state.page = newPage;

    document.getElementById(tableId).innerHTML =
        renderCurrentTablePage(tableId);
}