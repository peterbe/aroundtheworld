var Settings = (function() {
  var URL = '/settings.json';
  var container = $('#settings');
  var _once = false;

  function _set_form_data(data) {
    var f = $('form', container);
    if (data.disable_sound) {
      $('input[name="disable_sound"]', f).attr('checked', 'checked');
    } else {
      $('input[name="disable_sound"]', f).removeAttr('checked');
    }
    if (data.unsubscribe_emails) {
      $('input[name="unsubscribe_emails"]', f).attr('checked', 'checked');
    } else {
      $('input[name="unsubscribe_emails"]', f).removeAttr('checked');
    }
    $('input[name="username"]', f).val(data.username);
    if (data.anonymous) {
      $('input[name="username"]', f).attr('disabled', 'disabled');
      L($('.for-first_name', f));
      $('.for-first_name', f).hide();
      $('.for-last_name', f).hide();
    } else {
      $('input[name="username"]', f).removeAttr('disabled');
      $('input[name="first_name"]', f).val(data.first_name);
      $('input[name="last_name"]', f).val(data.last_name);
      $('.for-first_name', f).show();
      $('.for-last_name', f).show();
    }
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

  function setup_once() {
    $('form', container).submit(function() {
      var username = $.trim($('input[name="username"]', this).val());
      var f = $(this);
      if (username.length) {
        $.getJSON(URL, {'check-username': username}, function(response) {
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

  }

  return {
     setup_form: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }

       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         _set_form_data(response);
         if (STATE.user.anonymous) {
           $('.still-anonymous', container).hide().fadeIn(400);
         } else {
           $('.still-anonymous', container).hide();
         }
       });

       Utils.update_title();
     },
    teardown: function() {
      $('.still-anonymous', container).hide();
    }
  };
})();


$.fn.serializeObject = function() {
  var o = {};
  var a = this.serializeArray();
  $.each(a, function() {
    if (o[this.name] !== undefined) {
      if (!o[this.name].push) {
        o[this.name] = [o[this.name]];
      }
      o[this.name].push(this.value || '');
    } else {
      o[this.name] = this.value || '';
    }
  });
  return o;
};


Plugins.start('settings', function() {
  // called every time this plugin is loaded
  Settings.setup_form();
});

Plugins.stop('settings', function() {
  Settings.teardown();
});
