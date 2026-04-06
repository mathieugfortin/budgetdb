// static 'budgetdb/js/base.js'
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');


/**
 * UI Helper Functions
 */
function tsToDate(ts) {
    return new Date(ts).toLocaleDateString('fr-CA', {
        year: 'numeric', month: 'numeric', day: 'numeric'
    });
}
function onRangeUpdate(begin, end) {
    // Placeholder for page-specific range logic
}

function addHRef(label, url, attachTo) {
    const container = document.getElementById(attachTo);
    if (!container) return;

    const newA = document.createElement('a');
    newA.href = url;
    newA.className = 'dropdown-item';
    newA.innerHTML = label;
    container.append(newA);
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


function triggerManualExtension() {
    const config = window.DjangoConfig;
    const btn = document.getElementById('btn-sync');
    const progressBar = document.getElementById('sync-progress');
    const statusBadge = document.getElementById('status-badge');
    
    // Get token from the hidden input Django creates
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    btn.disabled = true;
    progressBar.classList.remove('d-none');
    statusBadge.classList.replace('bg-primary', 'bg-warning');

    fetch(config.urls.trigger_extend_ledger, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/json"
        }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('ledger-status-text').innerText = data.status;
        startStatusPoller(config.urls.trigger_extend_ledger);
    })
    .catch(error => {
        console.error('Error:', error);
        btn.disabled = false;
        progressBar.classList.add('d-none');
    });
}


function triggerNuclearRebuild() {
    if (!confirm("Are you sure? This will wipe the entire balance cache and recalculate from scratch. This may take a moment.")) {
        return;
    }

    const config = window.DjangoConfig;
    const btn = document.getElementById('btn-rebuild');
    const progressBar = document.getElementById('rebuild-progress');
    const statusBadge = document.getElementById('rebuild-status-badge');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    btn.disabled = true;
    progressBar.classList.remove('d-none');
    statusBadge.classList.replace('bg-secondary', 'bg-warning');
    document.getElementById('rebuild-status-text').innerText = 'Rebuilding...';

    fetch(config.urls.trigger_rebuild_ledger, { // You'll need to add this URL
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
            "Content-Type": "application/json"
        }
    })
    .then(response => response.json())
    .then(data => {
        // Reuse your existing status poller logic
        startStatusPoller(config.urls.trigger_rebuild_ledger, 'rebuild');
    })
    .catch(error => {
        console.error('Error:', error);
        btn.disabled = false;
        progressBar.classList.add('d-none');
    });
}




function startStatusPoller(url, taskType = 'extend') {
    // Mapping of which elements to update based on the task
    const elements = {
        'extend': {
            status: 'ledger-status-text',
            btn: 'btn-sync',
            progress: 'sync-progress',
            badge: 'status-badge'
        },
        'rebuild': {
            status: 'rebuild-status-text',
            btn: 'btn-rebuild',
            progress: 'rebuild-progress',
            badge: 'rebuild-status-badge'
        }
    }[taskType];

    const pollInterval = setInterval(() => {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                const status = data.status;
                document.getElementById(elements.status).innerText = status;

                if (status === 'Completed' || status.includes('Error')) {
                    clearInterval(pollInterval);
                    
                    // Reset UI
                    document.getElementById(elements.btn).disabled = false;
                    document.getElementById(elements.progress).classList.add('d-none');
                    
                    // Update Badge Color
                    const badge = document.getElementById(elements.badge);
                    if (status === 'Completed') {
                        badge.className = 'badge bg-success px-3 py-2';
                        // Refresh the last run timestamp if provided
                        if (data.last_run) {
                            document.getElementById('ledger-last-run').innerText = data.last_run;
                        }
                    } else {
                        badge.className = 'badge bg-danger px-3 py-2';
                    }
                }
            })
            .catch(error => {
                console.error('Polling error:', error);
                clearInterval(pollInterval);
            });
    }, 2000); // Poll every 2 seconds
}


document.addEventListener('DOMContentLoaded', function() {
    const healthModal = document.getElementById('systemHealthModal');
    
    healthModal.addEventListener('shown.bs.modal', function () {
        // Initial load of data when modal opens
        refreshLedgerStatus();
    });
});

function refreshLedgerStatus() {
    const config = window.DjangoConfig;
    const statusText = document.getElementById('ledger-status-text');
    const lastRun = document.getElementById('ledger-last-run');
    const statusBadge = document.getElementById('status-badge');

    fetch(config.urls.trigger_extend_ledger)
        .then(res => res.json())
        .then(data => {
            statusText.innerText = data.status;
            lastRun.innerText = data.last_run || 'Never';
            
            // Update badge color based on status
            if (data.status === 'Running') {
                statusBadge.classList.replace('bg-primary', 'bg-warning');
                document.getElementById('sync-progress').classList.remove('d-none');
                startStatusPoller(); // Start polling if it's already running
            } else if (data.status === 'Idle') {
                statusBadge.classList.replace('bg-primary', 'bg-success');
                statusBadge.classList.replace('bg-warning', 'bg-success');
            }
        })
        .catch(err => {
            statusText.innerText = "Offline";
            statusBadge.classList.replace('bg-primary', 'bg-danger');
        });
}

function openHealth(tabId) {
    const el = document.getElementById('systemHealthModal');
    if (!el) return;
    
    const modal = new bootstrap.Modal(el);
    if (tabId) {
        const targetTab = document.querySelector(`a[href="#${tabId}"]`);
        if (targetTab) new bootstrap.Tab(targetTab).show();
    }
    modal.show();
}

function setTheme(config, themeName) {
    //document.documentElement.setAttribute('data-bs-theme', themeName);
    
    // 2. (Optional) Save it to the server via AJAX so it persists
    // fetch('/update-preferences/', { method: 'POST', body: ... });



    // 1. Immediate UI update (Bootstrap 5.3 style)
    document.documentElement.setAttribute('data-bs-theme', themeName);

    // 2. Persist to the database
    $.post(config.urls.update_theme_preference, {
        'theme': themeName
    })
    .done(function(response) {
        console.log("Theme saved: " + themeName);
    })
    .fail(function() {
        // Fallback: Revert UI if the server save fails
        alert("Failed to save theme preference.");
    });



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
        $.getJSON(config.urls.cattype_pie_urls_json, (result) => {
            result.forEach(item => addHRef(item.name, item.url, 'pie_chart_menu'));
        });

        $.getJSON(config.urls.cattype_bar_urls_json, (result) => {
            result.forEach(item => addHRef(item.name, item.url, 'bar_chart_menu'));
        });

        $.getJSON(config.urls.account_transaction_list_urls_json, (result) => {
            result.forEach(item => addHRef(item.name, item.url, 'account_menu'));
        });

        $.getJSON(config.urls.cat1_list_URLsjson, (result) => {
            result.forEach(item => addHRef(item.name, item.url, 'categories_menu'));
        });        

        $.getJSON(config.urls.accountcat_timeline_URLs_json, (result) => {
            result.forEach(item => addHRef(item.name, item.url, 'timeline_menu'));
        });
        // 1. Get the container
        const sliderElement = document.getElementById('input_range'); // Use your actual ID

        document.getElementById('themeToggle').addEventListener('change', function(e) {
            const theme = e.target.checked ? 'dark' : 'light';
            setTheme(config, theme);
        });

        $(document).on('click', '.toggle-statement-lock', function(e) {
            e.preventDefault(); 
         
            const $link = $(this);
            const $icon = $link.find('.material-symbols-outlined');
            const url = $link.attr('href');

            // Add a slight fade to show "activity"
            $icon.css('opacity', '0.5');

            $.post(url, (data) => {
                if (data.status === 'success') {
                    // Check current state to flip it
                    debugger
                    if ($icon.hasClass('lock-icon-verified')) {
                        // Flip to UNVERIFIED (Unlocked)
                        $icon.removeClass('lock-icon-verified')
                            .addClass('lock-icon-unverified')
                            .text('lock_open'); // Changes the Material Icon shape
                        $link.attr('title', 'Click to Lock');
                    } else {
                        // Flip to VERIFIED (Locked)
                        $icon.removeClass('lock-icon-unverified')
                            .addClass('lock-icon-verified')
                            .text('lock'); // Changes the Material Icon shape
                        $link.attr('title', 'Click to Unlock');
                    }
                }
            })
            .always(() => {
                debugger
                $icon.css('opacity', '1'); // Bring opacity back
            })
            .fail(() => {
                debugger
                alert("Server error: Could not toggle lock status.");
            });
        });

        if (sliderElement) {
            // 2. Fetch the dates to initialize the slider
            $.getJSON(config.urls.preferences, (res) => {
                

                // Add keyboard support to handles
                const handles = sliderElement.querySelectorAll('.noUi-handle');

                handles.forEach((handle, index) => {
                    handle.setAttribute('tabindex', '0'); // Make it focusable
                    
                    handle.addEventListener('keydown', function (e) {
                        const value = Number(sliderElement.noUiSlider.get()[index]);
                        const day = 24 * 60 * 60 * 1000; // Your step size

                        switch (e.which) {
                            case 37: // Left Arrow
                                sliderElement.noUiSlider.setHandle(index, value - day, true);
                                break;
                            case 39: // Right Arrow
                                sliderElement.noUiSlider.setHandle(index, value + day, true);
                                break;
                        }
                    });
                });


                // 3. Create the slider
                noUiSlider.create(sliderElement, {
                    range: {
                        'min': new Date(res.timeline_start).getTime(),
                        'max': new Date(res.timeline_stop).getTime()
                    },
                    step: 24 * 60 * 60 * 1000, // 1 day
                    start: [new Date(res.slider_start).getTime(), new Date(res.slider_stop).getTime()],
                    connect: true,
                    behaviour: 'tap', // Allows clicking the bar to move the handle
                    tooltips: [true, true],
                    format: {
                        to: value => tsToDate(value), // Your existing date formatter
                        from: value => value
                    }
                });

                // 4. Attach the listener (The code you wrote)
                sliderElement.noUiSlider.on('change', function (values, handle) {
                    let [start, end] = values;
                    $.post(config.urls.set_interval, {
                        'begin_interval': start,
                        'end_interval': end
                    });
                    onRangeUpdate(start, end);
                });

                sliderElement.noUiSlider.on('update', function (values, handle) {
                    const sliderWidth = sliderElement.offsetWidth;
                    // Get the positions (0 to 100) of both handles
                    const positions = sliderElement.noUiSlider.getPositions();
                    const distancePx = Math.abs(positions[0] - positions[1]) * (sliderWidth / 100);
                    const thresholdPx = 80; 
                    const isOverlapping = distancePx < thresholdPx;

                    if (isOverlapping) {
                        sliderElement.classList.add('tooltips-overlapping');
                    } else {
                        sliderElement.classList.remove('tooltips-overlapping');
                    }
                });
            });
        }
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
    // 4. Auto-detect Health Context
    if (window.location.href.includes("recurring")) {
        document.querySelectorAll('.nav-link[onclick*="openHealth"]').forEach(btn => {
            btn.setAttribute('onclick', "openHealth('tab-recurring')");
        });
    }
});