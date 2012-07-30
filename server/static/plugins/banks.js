var Banks = (function() {
  var URL = '/banks.json';
  var container = $('#banks');
  var _once = false;

  function _show_form_errors(errors, form) {
    if (errors.amount) {
      $('.amount-error-text', container)
        .text(errors.amount)
          .hide().fadeIn(200);
    }
    if (errors && !errors.amount) {
      L(errors);
      L('OTHER ERRORS', errors);
    }
  }

  function _prepare_open_account(bank) {
    _prepare_deposit(bank, true);
  }

  function _prepare_deposit(bank, open_account) {
    var c = $('.transact', container);
    var action;
    open_account = open_account == undefined && false;
    if (open_account) {
      $('.deposit-action', c).text('Open a new account');
      $('.balance', c).hide();
      action = 'open';
    } else {
      $('.deposit-action', c).text('Deposit more coins');
      action = 'deposit';
      $.getJSON(URL, {id: bank}, function(response) {
        var bank = response.bank;
        if (bank.has_account) {
          $('.balance strong', c).text(Utils.formatCost(bank.sum + bank.interest, true));
          $('.balance', c).show();
        }
      });
    }
    $('.index', container).hide();
    c.fadeIn(400)
      .off('submit')
        .on('submit', function() {
          var amount = $.trim($('input[name="amount"]', this).val());
          if (!amount.length) return false;

          $.post(URL, {amount: amount, id: bank, action: 'open'}, function(response) {
            if (response.errors) {
              _show_form_errors(response.errors);
            } else {
              $('input[name="amount"]', c).val('');
              State.show_coin_change(-1 * response.amount, true);
              load_banks(function() {
                c.hide();
                $('.index', container).fadeIn(400);
                Utils.update_title();
              });
            }
          });
          return false;
        });
  }

  function _prepare_withdrawal(bank) {
    var c = $('.transact', container);
    $('.deposit-action', c).text('Withdraw coins');
    $('.index', container).hide();
    $.getJSON(URL, {id: bank}, function(response) {
      var bank = response.bank;
      if (bank.has_account) {
        $('.balance strong', c).text(Utils.formatCost(bank.sum + bank.interest, true));
        $('.balance', c).show();
      }
    });

    c.fadeIn(400)
      .off('submit')
        .on('submit', function() {
          var amount = $.trim($('input[name="amount"]', this).val());
          if (!amount.length) return false;

          $.post(URL, {amount: amount, id: bank, action: 'withdraw'}, function(response) {
            if (response.errors) {
              _show_form_errors(response.errors);
            } else {
              $('input[name="amount"]', c).val('');
              State.show_coin_change(response.amount, true);
              load_banks(function() {
                c.hide();
                $('.index', container).fadeIn(400);
                Utils.update_title();
              });
            }
          });
          return false;
        });
  }

  function _display_bank(bank) {
    var c = $('.sample-bank', container).clone().removeClass('sample-bank');
    c.data('id', bank.id);
    $('.bank-name', c).text(bank.name);
    if (bank.open) {
      $('.bank-head .label', c).remove();
    }
    if (bank.other_cities.length) {
      $('.branches-none', c).hide();
      var b = $('.branches-some', c);
      var ul = $('.branches-some ul', c);
      $('li', ul).remove();
      $.each(bank.other_cities, function(i, each) {
        $('<li>')
          .text(each)
          .appendTo(ul);
      });
      ul.appendTo(b);
      b.show();
    } else {
      $('.branches-some', c).hide();
      $('.branches-none', c).show();
    }
    $('.default-interest-rate', c).text(bank.default_interest_rate + '%');
    $('.deposit-fee', c)
      .text(bank.deposit_fee ? Utils.formatCost(bank.deposit_fee, true) : 'FREE');
    $('.withdrawal-fee', c)
      .text(bank.withdrawal_fee ? Utils.formatCost(bank.withdrawal_fee, true) : 'FREE');

    if (bank.sum) {
      $('.current-balance', c).text(Utils.formatCost(bank.sum + bank.interest, true));
      $('.total-deposited', c).text(Utils.formatCost(bank.sum, true));
      $('.total-interest', c).text(Utils.formatCost(bank.interest, true));
      $('.balance', c).show();
    } else {
      $('.balance', c).hide();
    }

    $('button', c).hide();
    if (bank.has_account) {

      $('button.deposit', c)
        .click(function() {
          _prepare_deposit(c.data('id'));
          return false;
        })
        .show();
      $('button.withdraw', c)
        .click(function() {
          _prepare_withdrawal(c.data('id'));
          return false;
        })
        .show();

    } else {
      $('button.open', c)
        .click(function() {
          _prepare_open_account(c.data('id'));
          return false;
        })
        .show();

    }

    // finally, add it
    c.addClass('bank').show();
    $('.available-banks .index', container).append(c);
  }

  function setup_once() {

    $('form', container).submit(function() {
      L('form submitted');
      return false;
    });

    $('.transact button[name="cancel"]', container).click(function() {
      $('.transact', container).hide();
      $('.transact input[name="amount"]', container).val('');
      $('.index', container).fadeIn(400);
      return false;
    });

    $('input[name="amount"]', container).change(function() {
      $('.amount-error-text:visible', container).hide(400);
    });
  }

  function load_banks(callback) {
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

         $('.available-banks .bank', container).remove();
         $.each(response.banks, function(i, bank) {
           _display_bank(bank);
         });

         if (STATE.user.anonymous) {
           $('.available-banks', container).hide();
           $('.still-anonymous', container).hide().fadeIn(400);
         } else {
           $('.available-banks', container).hide().fadeIn(400);
           $('.still-anonymous', container).hide();
         }

         $('.location-name', container).text(response.location_name);
         callback();
       });
  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }

       load_banks(function() {
         Utils.update_title();
       });
     },
    teardown: function() {
      $('.still-anonymous', container).hide();
      $('.amount-error-text:visible', container).text('').hide();
    }
  };
})();




Plugins.start('banks', function() {
  Banks.setup();
});

Plugins.stop('banks', function() {
  Banks.teardown();
});
