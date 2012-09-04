var League = (function() {
  var URL = '/league.json';
  var container = $('#league');
  var _once = false;

  function _show_highscore(list) {
    var c = $('.highscore table', container);
    $('tr', c).remove();
    $.each(list, function(i, each) {
      $('<tr>')
        .addClass(each.you ? 'you' : '')
        .addClass(i == 0 ? 'first' : '')
        .addClass(i == 1 ? 'second' : '')
        .addClass(i == 2 ? 'third' : '')
        .append($('<td>').text(i + 1))
        .append($('<td>').text(each.name))
        .append($('<td>').addClass('total').text(Utils.formatCost(each.total)))
        .appendTo(c);
    });
  }

  function _show_total_earned(info) {
    $('.total-earned', container).text(Utils.formatCost(info.coins, true));
    $('.total-earned-rank', container).text('#' + info.rank);
  }

  function post_form(f) {
    $('input[name="username"]', f).off('keydown');
    $.post(URL, f.serializeObject(), function(response) {
      $('.saved-notification:hidden', container).hide().fadeIn(200);
      _set_form_data(response);
      State.update();
      setTimeout(function() {
        $('.saved-notification:visible', container).fadeOut(500);
      }, 2 * 1000);
    });
  }

  function _click_connect(element) {
    var button = $(element);
    $('table.search-results', container).hide();
    $.post(URL, {'id': button.data('id')}, function(response) {
      $('input[name="email"]', container).val('');
       $.getJSON(URL, function(response) {
         _show_highscore(response.highscore);
       });
    });
  }

  function _show_search_results(data) {
    var c = $('table.search-results', container).show();
    $('tr.result', c).remove();
    $('tr.head', c).show();
    $.each(data.result, function(i, each) {
      $('<tr>').addClass('result')
        .append($('<td>').text(each[1]))
        //.append($('<td>').text(each[3]))
        .append($('<td>')
                .append($('<abbr>')
                        .attr('title', each[2])
                        .text(each[3]))
               )
        .append($('<td>')
                .append($('<button>')
                        .data('id', each[0])
                        .addClass('btn').addClass('btn-mini')
                        .text('Connect')
                        .click(function() {
                          _click_connect(this);
                        }))

                )
        .appendTo(c);
    });
    if (data.capped) {
      $('<tr>')
        .addClass('result')
        .addClass('capped')
        .append($('<td>')
                .text('Only show the first ' + data.count)
                .attr('colspan', 3))
        .appendTo(c);
    }
    $('.result-count', container).text(data.count + ' found');
  }

  var _previous_search;
  var _locked = false;

  function _process_autocomplete() {
    var value = $.trim($('input[name="email"]', container).val());
    if (!value) {
      $('.invite-hint', container).hide();
      $('table.search-results', container).hide();
    }
    if (value && value != _previous_search) {
      _locked = true;
      _previous_search = value;
      $.getJSON(URL, {find: value}, function(response) {
        _show_search_results(response);
        if (!response.result.length) {
          $('table.search-results', container).hide();
          if (value.search('@') > -1) {
            $('.invite-hint', container).show(200);
          } else {
            $('.invite-hint', container).hide();
          }
        } else {
          $('.invite-hint', container).hide();
        }
        $('.invite-preview', container).hide();
        $('.invite-sent', container).hide();
        $('.invite-not-sent', container).hide();
        _locked = false;
      });
    }
  }

  function setup_once() {
    $('form', container).submit(function() {
      //var value = $.trim($('input[name="email"]', container).val());
      //console.log('SUBMIT', value);
      return false;
    });

    // auto-complete for search
    $('input[name="email"]', container).keyup(function(event) {
      if (_locked) return;
      _process_autocomplete();
    });

    if ($.trim($('input[name="email"]', container).val())) {
      _process_autocomplete();
    }

    $('button.sendit', container).click(function() {
      var email = $.trim($('input[name="email"]', container).val());
      var text = $.trim($('textarea.preview').val());
      $.post(URL, {email: email, text: text}, function(response) {
        if (response.errors) {
          $.each(response.errors, function(i, each) {
            alert(each);
          });
        } else {
          $('button.cancel', container).click();
          if (!response.sent) {
            // NO ERROR BUT THE EMAIL COULD NOT BE SENT
            $('.invite-not-sent', container).show();
            setTimeout(function() {
              $('.invite-not-sent:visible', container).hide(300);
            }, 5 * 1000);
          } else {
            // ALL IS WELL
            $('.invite-sent', container).show();
            setTimeout(function() {
              $('.invite-sent:visible', container).hide(300);
            }, 3 * 1000);
          }
        }


      });
      return false;
    });

    $('button.preview', container).click(function() {
      $('.invite-hint', container).hide();
      $('table.search-results', container).hide();
      $.getJSON(URL, {preview: true}, function(response) {
        $('textarea.preview', container).val(response.text);
      });
      $('.invite-preview', container).show(200);
      return false;
    });

    $('button.cancel', container).click(function() {
      $('.invite-hint', container).hide();
      $('.invite-preview', container).hide();
      $('.invite-sent', container).hide();
      $('.invite-errors', container).hide();
      $('input[name="email"]', container).val('');
    });

    /*
    $('form', container).submit(function() {
      var email = $.trim($('input[name="email"]', this).val());
      var f = $(this);
      if (username.length) {
        $.getJSON(URL, {'check-email': email}, function(response) {
          if (response.wrong) {
            $('input[name="username"]', f).on('keydown', function() {
              $('.username-error-text').fadeOut(300);
              $(this).off('keydown');
            });
            $('.username-error-text')
              .text("Something not right: " + response.wrong)
                .hide()
                  .fadeIn(200);
          } else {
            post_form(f);
          }
        });
      } else {
        post_form(f);
      }
      return false;
    });
     */

  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }

       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         _show_total_earned(response.total_earned);
         _show_highscore(response.highscore);
         _show_invites(response.invites);

         if (STATE.user.anonymous) {
           $('.friends input', container).attr('disabled', 'disabled');
           $('.not-signed-in', container).show(300);
         } else {
           $('.friends input', container).removeAttr('disabled');
           $('.not-signed-in', container).hide();
         }

       });

       Utils.update_title();
     },
    teardown: function() {
      $('table.search-results', container).hide();
    }
  };
})();


Plugins.start('league', function() {
  League.setup();
});

Plugins.stop('league', function() {
  League.teardown();
});
