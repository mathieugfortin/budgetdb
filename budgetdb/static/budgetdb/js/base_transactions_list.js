// static 'budgetdb/js/base_transactions_list.js'

const TransactionManager = {
    // 1. CONFIGURATION & SELECTORS
    // Update these in one place if your HTML changes
    config: {},
    ui: {
        modal: "#modal",
        deleteSection: "#delete-section",
        normalActions: "#normal-actions",
        isDeletedInput: "input[name='is_deleted']",
        tableRows: "tbody tr[data-date]"
    },

    // 2. INITIALIZATION
    init() {
        this.config = document.getElementById('tx-config').dataset;
        this.allCat1s = JSON.parse(document.getElementById('cat1-data').textContent);
        this.csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        this.initTooltips();
        this.bindEvents();
        this.handlePostLoadNavigation();
    },

    // 3. EVENT BINDING (The "Traffic Controller")
    bindEvents() {
        const self = this;

        // Category Editing (Cat1 & Cat2)
        $(document).on('click', '.cat1-wrapper .cat-display', (e) => self.editCat1(e));
        $(document).on('change', '.cat1-select', (e) => self.saveCat1(e));
        $(document).on('click', '.cat2-wrapper .cat-display', (e) => self.editCat2(e));
        $(document).on('change', '.cat2-select', (e) => self.saveCat2(e));
        $(document).on('blur', '.cat-select', (e) => self.closeInlineEdit(e));

        // Delete Functionality
        $(document).on("click", ".show-delete-confirm", () => self.toggleDeleteUI(true));
        $(document).on("click", ".cancel-delete", () => self.toggleDeleteUI(false));
        $(document).on("click", ".confirm-delete", (e) => self.prepareDelete(e));

        // Modal Integration
        $(".update-transaction").each(function () {
            $(this).modalForm({ formURL: $(this).data("form-url"), modalID: self.ui.modal });
        });

        $(document).on("shown.bs.modal", this.ui.modal, (e) => self.onModalOpen(e));
        $(document).on('bs.modal.forms.submit', this.ui.modal, (e, resp) => self.onModalSubmit(resp));
    },

    // 4. CATEGORY LOGIC
    editCat1(e) {
        const $span = $(e.currentTarget);
        const $wrapper = $span.closest('.cat1-wrapper');
        const $container = $wrapper.find('.cat1-select-container');
        const currentId = $wrapper.data('cat1-id');

        const $select = $('<select>', { class: 'cat-select cat1-select form-select form-select-sm' });
        $select.append('<option value="">---------</option>');
        
        this.allCat1s.forEach(cat => {
            let selected = (cat.id == currentId) ? 'selected' : '';
            $select.append(`<option value="${cat.id}" ${selected}>${cat.name}</option>`);
        });

        $container.empty().append($select).removeClass('d-none');
        $span.addClass('d-none');
        $select.select2({ width: '100%' }).select2('open');
    },

    saveCat1(e) {
        const $select = $(e.currentTarget);
        const txId = $select.closest('.cat1-wrapper').data('txid');
        const val = $select.val();

        $.post(this.config.urlUpdateTransactionCategory, {
            'transaction_id': txId, 'cat_level': 1, 'category_id': val, 'csrfmiddlewaretoken': this.csrftoken
        }).done(() => {
            this.flashSuccess('#save-check-cat1' + txId);
            // Reset Cat2 sibling in same row
            const $cat2Disp = $select.closest('tr').find('.cat2-wrapper .cat-display');
            $cat2Disp.text('---------').addClass('pulse-warning');
            setTimeout(() => $cat2Disp.removeClass('pulse-warning'), 1500);
        });
    },

    editCat2(e) {
        const $span = $(e.currentTarget);
        const $wrapper = $span.closest('.cat2-wrapper');
        const txId = $wrapper.data('txid');
        const $cat1Wrapper = $span.closest('tr').find('.cat1-wrapper');
        const cat1Id = $cat1Wrapper.attr('data-cat1-id') || $cat1Wrapper.data('cat1-id');

        if (!cat1Id) return alert("Select a Category first.");

        $.getJSON(this.config.urlGetCat2List, { 'cat1_id': cat1Id }).done((data) => {
            const $select = $('<select>', { class: 'cat-select cat2-select form-select form-select-sm' });
            $select.append('<option value="">---------</option>');
            data.cat2s.forEach(item => {
                let selected = (item.id == $wrapper.data('cat2-id')) ? 'selected' : '';
                $select.append(`<option value="${item.id}" ${selected}>${item.name}</option>`);
            });
            $wrapper.find('.cat2-select-container').empty().append($select).removeClass('d-none');
            $span.addClass('d-none');
            $select.select2({ width: '100%' }).select2('open');
        });
    },

    saveCat2(e) {
        const $select = $(e.currentTarget);
        const txId = $select.closest('.cat2-wrapper').data('txid');
        $.post(this.config.urlUpdateTransactionCategory, {
            'transaction_id': txId, 'cat_level': 2, 'category_id': $select.val(), 'csrfmiddlewaretoken': this.csrftoken
        }).done(() => this.flashSuccess('#save-check-cat2' + txId));
    },

    // 5. DELETE & MODAL LOGIC
    toggleDeleteUI(show) {
        const $norm = $(this.ui.normalActions);
        const $del = $(this.ui.deleteSection);
        if (show) {
            $norm.slideUp(200, () => $del.removeClass("d-none").slideDown(250));
        } else {
            $del.slideUp(200, () => { $del.addClass("d-none"); $norm.slideDown(250); });
        }
    },

    prepareDelete(e) {
        const $form = $(e.currentTarget).closest("form");
        const txId = $form.data('txid');
        // Set the actual Django field to true
        $form.find(this.ui.isDeletedInput).val("true");
        // Immediate UX feedback
        $('#T' + txId).fadeOut(400);
    },

    onModalSubmit(response) {
        console.log("RAW RESPONSE FROM SERVER:", response);
        if (!response.success) return;
       
        if (response.needs_refresh) {
            const url = new URL(window.location.href);
            if (response.scroll_date) {
                url.searchParams.set('scroll_date', response.scroll_date);
                url.searchParams.set('updated_id', response.transaction_id);
                //url.searchParams.delete('updated_id');
            } else {
                url.searchParams.set('updated_id', response.transaction_id);
                url.searchParams.set('scroll_date', response.scroll_date);
                //url.searchParams.delete('scroll_date');
            }
            window.location.href = url.toString();
        } else {
            const $row = $('#T' + response.transaction_id);
            $row.find('.description-column').text(response.description);
            $(this.ui.modal).modal('hide');
            this.flashRow($row);
        }
    },

    // 6. NAVIGATION & HELPERS
    handlePostLoadNavigation() {
        const params = new URLSearchParams(window.location.search);
        console.log(params);
        const updatedId = params.get('updated_id');
        const scrollDate = params.get('scroll_date');
        let $target;

        if (updatedId) {
            $target = $('#T' + updatedId);
        } else if (scrollDate) {
            $target = this.findRowByDate(scrollDate);
        }

        if ($target && $target.length) {
            $target[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            this.flashRow($target);
            this.cleanUrl(['updated_id', 'scroll_date']);
        }
    },

    findRowByDate(targetDate) {
        console.log("Searching for closest row to:", targetDate);
        const targetTime = new Date(targetDate).getTime();
        let $bestMatch = null;
        let closestDiff = Infinity;

        // Use the selector defined in ui.tableRows
        $(this.ui.tableRows).each(function() {
            const dateStr = $(this).attr('data-date'); // Use attr to be safe
            if (!dateStr) return;

            const rowTime = new Date(dateStr).getTime();
            const diff = Math.abs(targetTime - rowTime);

            if (diff < closestDiff) {
                closestDiff = diff;
                $bestMatch = $(this);
            }
        });

        if ($bestMatch) {
            console.log("Best match found:", $bestMatch.attr('id'), "with date:", $bestMatch.data('date'));
        } else {
            console.warn("No rows with data-date found in the table.");
        }
        
        return $bestMatch;
    },

    flashRow($row) {
        $row.addClass('table-success');
        setTimeout(() => $row.removeClass('table-success'), 2000);
    },

    flashSuccess(selector) {
        $(selector).addClass('show');
        setTimeout(() => $(selector).removeClass('show'), 1500);
    },

    closeInlineEdit(e) {
        const $select = $(e.currentTarget);
        $select.closest('.cat1-select-container, .cat2-select-container').addClass('d-none');
        $select.closest('.cat1-wrapper, .cat2-wrapper').find('.cat-display').removeClass('d-none');
    },

    initTooltips() {
        [...document.querySelectorAll('[data-bs-toggle="tooltip"]')].map(el => new bootstrap.Tooltip(el));
    },

    onModalOpen() {
        const $modal = $(this.ui.modal);
        $modal.find("select:not(.select2-hidden-accessible)").select2({ 
            dropdownParent: $modal, width: '100%', allowClear: true 
        });
        setTimeout(() => $('#id_amount_actual').focus(), 300);
    },

    cleanUrl(keysToRemove) {
        const params = new URLSearchParams(window.location.search);
        keysToRemove.forEach(k => params.delete(k));
        const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.history.replaceState(null, '', newUrl);
    }
};

// Start everything
$(document).ready(() => TransactionManager.init());