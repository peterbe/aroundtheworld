var Coins = (function() {
  var container = $('#coins');
  var transactions_page = 0;
  var transactions_shown = 0;
  var jobs_page = 0;
  var jobs_shown = 0;
  var earnings_page = 0;
  var earnings_shown = 0;

  function remove_previous_count(text) {
    return $.trim(text.replace(/\(\d+\)/g, ''));
  }

  function _show_transactions(transactions, count, clear) {
    if (clear) {
      $('div.purchases tbody tr', container).remove();
    }
    $.each(transactions, function(i, each) {
      //$('div.purchases:hidden', container).show();
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
      c.appendTo($('div.purchases tbody', container));
      transactions_shown++;
    });
    if (count > transactions_shown) {
      $('div.purchases .load-more:hidden', container).show();
      $('div.purchases .load-more', container)
        .off('click').click(function() {
          $.getJSON('/coins.json', {'transactions-page': transactions_page + 1}, function(response) {
            if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
            transactions_page++;
            _show_transactions(response.transactions, response.count_transactions, false);
          });
          return false;
        });
    } else {
      $('div.purchases .load-more:visible', container).hide();
    }
  }

  function _show_jobs(jobs, count, clear) {
    if (clear) {
      $('div.jobs tbody tr', container).remove();
    }
    $.each(jobs, function(i, each) {
      //$('div.jobs:hidden', container).show();
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
      c.appendTo($('div.jobs tbody', container));
      jobs_shown++;
    });
    if (count > jobs_shown) {
      $('div.jobs .load-more:hidden', container).show();
      $('div.jobs .load-more', container)
        .off('click').click(function() {
          $.getJSON('/coins.json', {'jobs-page': jobs_page + 1}, function(response) {
            if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
            jobs_page++;
            _show_jobs(response.jobs, response.count_jobs, false);
          });
          return false;
        });
    } else {
      $('div.jobs .load-more:visible', container).hide();
    }
  }

  function _show_earnings(earnings, total, clear) {
    if (clear) {
      $('div.earnings tbody tr', container).remove();
    }
    $.each(earnings, function(i, each) {
      var c = $('<tr>');
      $('<td>')
        .addClass('earning-type')
        .text(each.type)
          .appendTo(c);
      $('<td>')
        .addClass('earning-description')
        .html(each.description)
          .appendTo(c);
      $('<td>')
        .addClass('earning-coins')
        .text(Utils.formatCost(each.coins))
          .appendTo(c);
      $('<td>')
        .addClass('earning-when')
        .text(each.date)
          .appendTo(c);
      c.appendTo($('div.earnings tbody', container));
      jobs_shown++;
    });
  }

  function _show_banks(banks, total, clear) {
    if (clear) {
      $('div.banks tbody tr', container).remove();
    }

    $.each(banks, function(i, each) {
      var c = $('<tr>');
      if (each.in_current_location) {
        $('<td>')
          .addClass('bank-name')
            .append($('<a href="#banks"></a>')
                    .click(function() {
                      Loader.load_hash('#banks');
                    })
                    .text(each.name))
              .appendTo(c);
      } else {
        $('<td>')
          .addClass('bank-name')
            .text(each.name)
              .appendTo(c);
      }
      $('<td>')
        .addClass('bank-cities')
        .html(each.locations.join('; '))
          .appendTo(c);
      $('<td>')
        .addClass('bank-deposited')
        .text(Utils.formatCost(each.deposited))
          .appendTo(c);
      $('<td>')
        .addClass('bank-interest')
        .text(Utils.formatCost(each.interest))
          .appendTo(c);
      $('<td>')
        .addClass('bank-total')
        .text(Utils.formatCost(each.total))
          .appendTo(c);
      c.appendTo($('div.banks tbody', container));
      jobs_shown++;
    });
  }

  return {
     load: function(table) {
       // NB: parameter table is currently not being used
       $.getJSON('/coins.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

         $('.short-stats strong', container).text(Utils.formatCost(STATE.user.coins_total, true));
         $('.short-stats:hidden', container).fadeIn(100);

         $.getJSON('/coins.json', {'transactions-page': 0}, function(response) {
           $('.loading:visible', container).hide();

           $('a[href="#tab-purchases"]', container).text(
              remove_previous_count($('a[href="#tab-purchases"]', container).text())
                 + ' (' + response.count_transactions + ')');
           _show_transactions(response.transactions, response.count_transactions, true);
           $('.purchases table:hidden', container).show();

           $.getJSON('/coins.json', {'jobs-page': 0}, function(response) {
             $('a[href="#tab-jobs"]', container).text(
                remove_previous_count($('a[href="#tab-jobs"]', container).text())
                    + ' (' + response.count_jobs + ')');
             _show_jobs(response.jobs, response.count_jobs, true);
           });

           $.getJSON('/coins.json', {'earnings-page': 0}, function(response) {
             $('a[href="#tab-earnings"]', container).text(
                remove_previous_count($('a[href="#tab-earnings"]', container).text())
                    + ' (' + Utils.formatCost(response.earnings_total, true) + ')');
             _show_earnings(response.earnings, response.earnings_total, true);
           });

           $.getJSON('/coins.json', {'banks-page': 0}, function(response) {
             $('a[href="#tab-banks"]', container).text(
                remove_previous_count($('a[href="#tab-banks"]', container).text())
                    + ' (' + Utils.formatCost(response.banks_total, true) + ')');
             _show_banks(response.banks, response.banks_total, true);
           });

           Utils.update_title();
         });
       });

       if (STATE.location) {
         $('.exit:hidden', container).show();
       } else {
         $('.exit:visible', container).hide();
       }
     }
  };
})();

Plugins.start('coins', function(table) {
  // called every time this plugin is loaded
  Coins.load(table);
});

Plugins.stop('coins', function() {
  //
});
