/*
==========================================
Recruiter Analytics Dashboard v2
static/script.js
==========================================
*/

document.addEventListener("DOMContentLoaded", () => {
    initializeDashboard();
});

/**
 * Initialize all dashboard functionality.
 */
function initializeDashboard() {
    initializeTooltips();
    animateProgressBars();
    animateMetricCards();
    smoothAccordionScroll();
    highlightSearchBox();
}

/**
 * Enable Bootstrap tooltips if any element
 * uses data-bs-toggle="tooltip".
 */
function initializeTooltips() {
    if (typeof bootstrap === "undefined") return;

    const tooltipTriggerList = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]'
    );

    [...tooltipTriggerList].forEach((tooltipTriggerEl) => {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Animate skill assessment progress bars.
 */
function animateProgressBars() {

    const bars = document.querySelectorAll(".progress-bar");

    bars.forEach((bar) => {

        const finalWidth = bar.style.width;

        bar.style.width = "0%";

        requestAnimationFrame(() => {

            setTimeout(() => {

                bar.style.transition =
                    "width 1s ease-in-out";

                bar.style.width = finalWidth;

            }, 150);

        });

    });

}

/**
 * Simple fade-up animation
 * for recruiter metric cards.
 */
function animateMetricCards() {

    const cards = document.querySelectorAll(
        ".metric-card, .signal-card, .stat-box"
    );

    cards.forEach((card, index) => {

        card.style.opacity = "0";
        card.style.transform = "translateY(20px)";

        setTimeout(() => {

            card.style.transition =
                "all .45s ease";

            card.style.opacity = "1";
            card.style.transform = "translateY(0)";

        }, index * 70);

    });

}

/**
 * Scroll accordion into view
 * after opening Original JSON.
 */
function smoothAccordionScroll() {

    const jsonSection =
        document.getElementById("collapseJson");

    if (!jsonSection) return;

    jsonSection.addEventListener(
        "shown.bs.collapse",
        () => {

            setTimeout(() => {

                jsonSection.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            }, 150);

        }
    );

}

/**
 * Automatically focus search field
 * on page load.
 */
function highlightSearchBox() {

    const input = document.querySelector(
        'input[name="candidate_id"]'
    );

    if (!input) return;

    input.focus();

    input.addEventListener("keydown", (event) => {

        if (event.key === "Escape") {
            input.value = "";
        }

    });

}