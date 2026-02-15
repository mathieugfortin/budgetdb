/**
 * UI Helper Functions
 */
function tsToDate(ts) {
    return new Date(ts).toLocaleDateString('fr-CA', {
        year: 'numeric', month: 'numeric', day: 'numeric'
    });
}

function parseDateIS(date) {
    const year = date.substr(0, 4);
    let month = date.substr(5, 2) - 1;
    const day = date.substr(8, 2);
    return new Date(year, month, day).valueOf();
}

function addA(baseURL, pk, label, attachTo) {
    const container = document.getElementById(attachTo);
    if (!container) return;

    const newA = document.createElement('a');
    newA.href = baseURL.replace(/12345/, pk.toString());
    newA.className = 'dropdown-item';
    newA.innerHTML = label;
    container.append(newA);
}

function onRangeUpdate(begin, end) {
    // Placeholder for page-specific range logic
}

/**
 * Modal & Help Logic
 */
function openHelp(tabId) {
    const el = document.getElementById('instructionsModal');
    if (!el) return;
    
    const modal = new bootstrap.Modal(el);
    if (tabId) {
        const targetTab = document.querySelector(`a[href="#${tabId}"]`);
        if (targetTab) new bootstrap.Tab(targetTab).show();
    }
    modal.show();
}

/**
 * Main Initialization
 */
$(document).ready(function() {
    const config = window.DjangoConfig;

    // 1. Authenticated Logic (AJAX & Menus)
    if (config.isAuthenticated) {
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", $("[name=csrfmiddlewaretoken]").val());
                }
            }
        });

        // Populate Dynamic Menus
        $.getJSON(config.urls.cattype_list, (result) => {
            result.forEach(field => {
                addA(config.urls.cattype_pie, field[0].pk, field[1].name, 'pie_chart_menu');
                addA(config.urls.cattype_bar, field[0].pk, field[1].name, 'bar_chart_menu');
            });
        });

        $.getJSON(config.urls.account_list, (result) => {
            result.forEach(field => addA(config.urls.account_activity, field[0].pk, field[1].name, 'account_menu'));
        });

        $.getJSON(config.urls.accountcat_list, (result) => {
            result.forEach(field => addA(`${config.urls.timeline_chart}?ac=12345`, field[0].pk, field[1].name, 'timeline_menu'));
        });

        // Initialize Slider
        $.getJSON(config.urls.preferences, (res) => {
            $(".js-range-slider").ionRangeSlider({
                type: "double",
                skin: "big",
                min: parseDateIS(res.timeline_start),
                max: parseDateIS(res.timeline_stop),
                from: parseDateIS(res.slider_start),
                to: parseDateIS(res.slider_stop),
                prettify: tsToDate,
                onFinish: function(data) {
                    $.post(config.urls.set_interval, {
                        'begin_interval': data.from_pretty,
                        'end_interval': data.to_pretty
                    });
                    onRangeUpdate(data.from_pretty, data.to_pretty);
                }
            });
        });
    }

    // 2. Optimized Instruction Search Listener
    const searchInput = document.getElementById('instructionSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            const items = document.querySelectorAll('#inst-tabs .list-group-item');
            const labels = document.querySelectorAll('.nav-section-label');
            let hasMatches = false;

            items.forEach(item => {
                const isMatch = item.textContent.toLowerCase().includes(query);
                item.classList.toggle('d-none', !isMatch);
                if (isMatch) hasMatches = true;
            });

            labels.forEach(l => l.classList.toggle('d-none', query.length > 0));
            document.getElementById('noResults')?.classList.toggle('d-none', hasMatches || !query);
        });
    }

    // 3. Auto-detect Help Context
    if (window.location.href.includes("recurring")) {
        document.querySelectorAll('.nav-link[onclick*="openHelp"]').forEach(btn => {
            btn.setAttribute('onclick', "openHelp('tab-recurring')");
        });
    }
});