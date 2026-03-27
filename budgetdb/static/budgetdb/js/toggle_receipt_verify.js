// static 'budgetdb/js/toggle_receipt_verify.js'
(function($) {
    const config = document.getElementById('tx-config').dataset;
    const urlToggleReceipt = config.urlToggleReceipt
    const urlToggleVerify = config.urlToggleVerify
    const csrftoken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        
    window.togglereceiptT = function(transaction_id) {
        var data = {
            'transaction_id': transaction_id, 
            'csrfmiddlewaretoken': csrftoken
        };

        // Perform the POST request
        $.post(urlToggleReceipt, data)
         .done(function(response) {
            // ONLY toggle the classes if the server actually succeeded
            $('#R' + transaction_id).toggleClass('RECEIPT NORECEIPT');
            $('#T' + transaction_id).toggleClass('RECEIPT NORECEIPT');
         })
         .fail(function() {
            console.error("Failed to toggle receipt for: " + transaction_id);
         });
    };
    
    window.toggleverifyT = function(transaction_id) {
        var data = {
            'transaction_id': transaction_id, 
            'csrfmiddlewaretoken': csrftoken
        };
        $.post(urlToggleVerify, data)
         .done(function(response) {
            // ONLY toggle the classes if the server actually succeeded
            $('#V' + transaction_id).toggleClass('VERIFIED UNVERIFIED');
            $('#T' + transaction_id).toggleClass('VERIFIED UNVERIFIED');
         })        
         .fail(function() {
            console.error("Failed to toggle verify for: " + transaction_id);
         });
    };

})(jQuery);
