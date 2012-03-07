var Coins = (function() {
  var container = $('#coins');
  var transactions_page = 0;
  var transactions_shown = 0;
  var jobs_page = 0;
  var jobs_shown = 0;

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
             Utils.update_title();
           });
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

  if (window.addEventListener) {
    var state = 0, konami = [38,38,40,40,37,39,37,39,66,65];
    window.addEventListener("keydown", function(e) {
      if ( e.keyCode == konami[state] ) state++;
      else state = 0;
      if ( state == 10 ) {
        $.post('/coins.json', {cheat:true}, function(response) {
          if (response.coins) {
            State.update();
            alert("You cheater!\n" + response.coins + " coins awarded to you");
          } else if (response.ERROR) {
            alert(response.ERROR);
          } else {
            alert("Sorry. Can't cheat");
          }
        });
      }
    }, true);
  }
});

Plugins.stop('coins', function() {
  L('coins stop');
  if (window.removeEventListener) {
    try {
      window.removeEventListener('keydown');
    } catch(e) {
      L("ERROR on removeEventListener");
    }
  }
});
