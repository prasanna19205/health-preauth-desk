
const API_BASE = "";

const requestForm = document.getElementById("requestForm");
const submitButton = document.getElementById("submitButton");
const formMessage = document.getElementById("formMessage");

const trackingEmpty = document.getElementById("trackingEmpty");
const trackingDetails = document.getElementById("trackingDetails");

// Display messages
function showMessage(message, isError = false) {
    formMessage.textContent = message;
    formMessage.style.color = isError ? "#b33b3b" : "#53637a";
}

// Format names for display
function formatName(value) {
    return String(value || "—")
        .replaceAll("_", " ")
        .replaceAll("-", " ")
        .replace(/\b\w/g, character => character.toUpperCase());
}

// API request helper
async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        const detail = data.detail || data.message || `HTTP ${response.status}`;

        throw new Error(
            typeof detail === "string"
                ? detail
                : JSON.stringify(detail)
        );
    }

    return data;
}

// Check backend health
async function checkHealth() {
    const dot = document.getElementById("healthDot");
    const text = document.getElementById("healthText");

    try {
        const data = await apiRequest("/health");

        dot.className = "dot online";
        text.textContent =
            data.status === "ok" ? "API Online" : "API Available";

    } catch (error) {
        dot.className = "dot offline";
        text.textContent = "API Offline";
    }
}

// Update request tracking
function setTracking(jobId, status, message) {
    trackingEmpty.classList.add("hidden");
    trackingDetails.classList.remove("hidden");

    document.getElementById("jobId").textContent = jobId;

    const statusElement = document.getElementById("jobStatus");

    statusElement.textContent = formatName(status);
    statusElement.className = "status-pill";

    const progress = document.getElementById("progressBar");
    const trackingMessage = document.getElementById("trackingMessage");

    if (status === "completed") {
        statusElement.classList.add("completed");
        progress.style.width = "100%";

    } else if (status === "failed") {
        statusElement.classList.add("failed");
        progress.style.width = "100%";

    } else if (status === "running") {
        progress.style.width = "65%";

    } else {
        progress.style.width = "20%";
    }

    trackingMessage.textContent = message;
}

// Display lists
function renderList(elementId, values) {
    const list = document.getElementById(elementId);

    list.replaceChildren();

    if (!Array.isArray(values) || values.length === 0) {
        const item = document.createElement("li");
        item.textContent = "None reported.";
        list.appendChild(item);
        return;
    }

    values.forEach(value => {
        const item = document.createElement("li");

        item.textContent =
            typeof value === "string"
                ? value
                : JSON.stringify(value);

        list.appendChild(item);
    });
}

// Display supporting policy clauses
function renderClauses(clauses) {
    const container = document.getElementById("supportingClauses");

    container.replaceChildren();

    if (!Array.isArray(clauses) || clauses.length === 0) {
        container.textContent = "No supporting clauses were returned.";
        return;
    }

    clauses.forEach(clause => {
        const card = document.createElement("div");

        card.className = "clause";

        if (typeof clause === "string") {
            card.textContent = clause;

        } else {
            const heading = document.createElement("strong");

            heading.textContent =
                clause.clause_id ||
                clause.id ||
                clause.section ||
                clause.source ||
                "Supporting Evidence";

            const content = document.createElement("p");

            content.textContent =
                clause.text ||
                clause.content ||
                clause.description ||
                JSON.stringify(clause);

            card.append(heading, content);
        }

        container.appendChild(card);
    });
}

// Display the complete assessment result
function renderResult(response) {
    const panel = document.getElementById("resultPanel");

    panel.classList.remove("hidden");

    // Extract the actual result
    const result = response.result || response.data || response;

    // Recommendation can be a nested object
    const decision =
        result.recommendation ||
        result.decision ||
        {};

    const recommendation =
        typeof decision === "string"
            ? decision
            : decision.recommendation ||
              result.status ||
              "Assessment completed";

    document.getElementById("recommendation").textContent =
        formatName(recommendation);

    // Human review requirement
    const needsReview =
        decision.requires_human_review ??
        result.requires_human_review;

    document.getElementById("humanReview").textContent =
        needsReview === undefined
            ? "See assessment"
            : needsReview
                ? "Yes"
                : "No";

    // Assessment explanation
    document.getElementById("resultReason").textContent =
        decision.reason ||
        result.reason ||
        "No reason was provided.";

    // Missing information
    const missing =
        decision.missing_information ||
        result.missing_information ||
        result.analysis?.missing_information ||
        [];

    renderList("missingInformation", missing);

    // Supporting clauses from the investigation
    const clauses =
        decision.supporting_clauses ||
        result.supporting_clauses ||
        result.investigation?.retrieved_clauses ||
        [];

    renderClauses(clauses);

    // Full response for inspection
    document.getElementById("rawResult").textContent =
        JSON.stringify(response, null, 2);

    panel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// Track an asynchronous assessment job
async function trackJob(jobId) {
    let attempts = 0;
    const maximumAttempts = 120;

    while (attempts < maximumAttempts) {
        attempts++;

        const job = await apiRequest(
            `/requests/${encodeURIComponent(jobId)}`
        );

        const status = job.status || "queued";

        setTracking(
            jobId,
            status,
            `Assessment status: ${formatName(status)}.`
        );

        // Job completed
        if (status === "completed") {
            const result = await apiRequest(
                `/requests/${encodeURIComponent(jobId)}/result`
            );

            renderResult(result);

            showMessage("Assessment completed successfully.");

            return;
        }

        // Job failed
        if (status === "failed") {
            const result = await apiRequest(
                `/requests/${encodeURIComponent(jobId)}/result`
            );

            setTracking(
                jobId,
                "failed",
                result.error || "Assessment failed."
            );

            showMessage(
                result.error || "Assessment failed.",
                true
            );

            return;
        }

        // Wait before checking again
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    showMessage(
        "Assessment is taking longer than expected. Check the job status again.",
        true
    );
}

// Submit a new pre-authorisation request
requestForm.addEventListener("submit", async event => {
    event.preventDefault();

    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";

    showMessage("Submitting your request...");

    document.getElementById("resultPanel").classList.add("hidden");

    try {
        const formData = new FormData(requestForm);

        const requestBody = Object.fromEntries(
            formData.entries()
        );

        requestBody.estimated_cost =
            Number(requestBody.estimated_cost);

        // Remove optional empty diagnosis
        if (!requestBody.diagnosis.trim()) {
            delete requestBody.diagnosis;
        }

        // Send request to FastAPI
        const submission = await apiRequest("/requests", {
            method: "POST",
            body: JSON.stringify(requestBody)
        });

        showMessage(
            "Request submitted. Waiting for the AI agents..."
        );

        // Start tracking the returned job ID
        await trackJob(submission.job_id);

    } catch (error) {
        showMessage(error.message, true);

    } finally {
        submitButton.disabled = false;

        submitButton.textContent =
            "Submit for AI Assessment";
    }
});

// Load demonstration sample data
document.getElementById("sampleButton").addEventListener("click", () => {

    const sample = {
        patient_id: "DEMO001",
        policy_id: "POLICY001",
        policy_start_date: "2025-12-16",
        admission_date: "2026-11-16",
        procedure: "Cataract surgery",
        admission_type: "planned_surgical",
        room_category: "Single private room",
        estimated_cost: "85000",
        diagnosis: "Cataract",
        pre_existing_condition: "unknown"
    };

    Object.entries(sample).forEach(([name, value]) => {
        requestForm.elements[name].value = value;
    });

    showMessage(
        "Sample data loaded. Review it and click Submit for AI Assessment."
    );
});

// Load AI agent monitoring metrics
async function loadMetrics() {
    const container =
        document.getElementById("metricsContainer");

    container.textContent = "Loading agent metrics...";

    try {
        const data = await apiRequest(
            "/monitoring/agent-metrics"
        );

        const metrics =
            data.agents ||
            data.metrics ||
            data;

        container.replaceChildren();

        const entries = Object.entries(metrics).filter(
            ([, value]) =>
                value && typeof value === "object"
        );

        if (entries.length === 0) {
            container.textContent =
                "No agent metrics available yet. Submit a request first.";
        }

        entries.forEach(([name, metric]) => {
            const card = document.createElement("div");

            card.className = "metric-card";

            const heading = document.createElement("h3");

            heading.textContent = formatName(name);

            const values = document.createElement("div");

            values.className = "metric-values";

            const calls =
                metric.calls ??
                metric.total_calls ??
                0;

            const successes =
                metric.successes ??
                metric.successful_calls ??
                0;

            const failures =
                metric.failures ??
                metric.failed_calls ??
                0;

            [
                ["Calls", calls],
                ["Success", successes],
                ["Failures", failures]
            ].forEach(([label, value]) => {
                const item = document.createElement("div");

                const number = document.createElement("strong");
                const caption = document.createElement("span");

                number.textContent = value;
                caption.textContent = label;

                item.append(number, caption);

                values.appendChild(item);
            });

            card.append(heading, values);

            if (metric.average_time_seconds !== undefined) {
                const time = document.createElement("p");

                time.className = "muted";

                time.textContent =
                    `Average time: ${metric.average_time_seconds}s`;

                card.appendChild(time);
            }

            container.appendChild(card);
        });

        document.getElementById("metricsUpdated").textContent =
            `Last refreshed: ${new Date().toLocaleTimeString()}`;

    } catch (error) {
        container.textContent =
            `Unable to load metrics: ${error.message}`;
    }
}

// Refresh metrics button
document.getElementById("refreshMetrics").addEventListener(
    "click",
    loadMetrics
);

// Initial dashboard setup
checkHealth();
loadMetrics();

// Periodically check backend health
setInterval(checkHealth, 15000);