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


function addA(baseURL, pk, label, attachTo) {
    const container = document.getElementById(attachTo);
    if (!container) return;

    const newA = document.createElement('a');
    newA.href = baseURL.replace(/12345/, pk.toString());
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
                
                // 3. Create the slider
                noUiSlider.create(sliderElement, {
                    range: {
                        'min': new Date(res.timeline_start).getTime(),
                        'max': new Date(res.timeline_stop).getTime()
                    },
                    step: 24 * 60 * 60 * 1000, // 1 day
                    start: [new Date(res.slider_start).getTime(), new Date(res.slider_stop).getTime()],
                    connect: true,
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
                    const tooltips = sliderElement.querySelectorAll('.noUi-tooltip');
                    if (tooltips.length < 2) return;

                    // Get the horizontal position (%) of both handles
                    const positions = sliderElement.noUiSlider.getPositions();
                    const distance = Math.abs(positions[0] - positions[1]);

                    // If handles are within 15% of the total bar width, trigger the offset
                    // This is much smoother than pixel-counting tooltips
                    const isOverlapping = distance < 18; 

                    sliderElement.classList.toggle('tooltips-overlapping', isOverlapping);
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
});