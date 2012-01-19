var Coins = (function() {
  var container = $('#coins');
  var transactions_page = 0;
  var transactions_shown = 0;
  var jobs_page = 0;
  var jobs_shown = 0;

  function _show_transactions(transactions, count, clear) {
    if (clear) {
      $('.purchases tbody tr', container).remove();
    }
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
      transactions_shown++;
    });
    if (count > transactions_shown) {
      $('.purchases .load-more:hidden', container).show();
      $('.purchases .load-more', container)
        .off('click').click(function() {
          $.getJSON('/coins.json', {'transactions-page': transactions_page + 1}, function(response) {
            if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
            transactions_page++;
            _show_transactions(response.transactions, response.count_transactions, false);
          });
          return false;
        });
    } else {
      $('.purchases .load-more:visible', container).hide();
    }
  }

  function _show_jobs(jobs, count, clear) {
    if (clear) {
      $('.jobs tbody tr', container).remove();
    }
    $.each(jobs, function(i, each) {
      $('.jobs:hidden', container).show();
      var c = $('<tr>');
      $('<td>')
        .addClass('job-description')
        .text(each.description)
          .appendTo(c);
      $('<td>')
        .addClass('job-location')
        .text(each.location)
          .appendTo(c);
      $('<td>')
        .addClass('job-coins')
        .text(Utils.formatCost(each.coins))
          .appendTo(c);
      $('<td>')
        .addClass('job-when')
        .text(each.date)
          .appendTo(c);
      c.appendTo($('.jobs tbody', container));
      jobs_shown++;
    });
    if (count > jobs_shown) {
      $('.jobs .load-more:hidden', container).show();
      $('.jobs .load-more', container)
        .off('click').click(function() {
          $.getJSON('/coins.json', {'jobs-page': jobs_page + 1}, function(response) {
            if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
            jobs_page++;
            _show_jobs(response.jobs, response.count_jobs, false);
          });
          return false;
        });
    } else {
      $('.jobs .load-more:visible', container).hide();
    }
  }

  return {
     load: function() {
       $.getJSON('/coins.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

         $('.short-stats strong', container).text(Utils.formatCost(STATE.user.coins_total, true));
         $('.short-stats:hidden', container).fadeIn(100);
         _show_transactions(response.transactions, response.count_transactions, true);
         _show_jobs(response.jobs, response.count_jobs, true);
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
