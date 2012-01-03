var Coins = (function() {
  var container = $('#coins');

  function _show_transactions(transactions) {
    $.each(transactions, function(i, each) {
      $('.purchases:hidden', container).show();
      var c = $('<tr>');
      $('<td>')
        .addClass('transaction-type-' + each.type)
          .appendTo(c);
      $('<td>')
        .addClass('transaction-description')
        .text(each.description)
          .appendTo(c);
      $('<td>')
        .addClass('transaction-cost')
        .text(Utils.formatCost(each.cost))
          .appendTo(c);
      $('<td>')
        .addClass('transaction-when')
        .text(each.date)
          .appendTo(c);
      c.appendTo($('.purchases tbody', container));
    });
  }

  return {
     load: function() {
       $.getJSON('/coins.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

         $('.short-stats strong', container).text(Utils.formatCost(STATE.user.coins_total));
         $('.short-stats:hidden', container).fadeIn(100);

         _show_transactions(response.transactions);

       });

       if (STATE.location) {
         $('.exit:hidden', container).show();
       } else {
         $('.exit:visible', container).hide();
       }
     }
  };
})();

Plugins.start('coins', function() {
  // called every time this plugin is loaded
  Coins.load();
});
