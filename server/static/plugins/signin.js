var Login = (function() {
  var URL = '/auth/email/';
  var container = $('#signin');
  var _once = false;
  var waiting_signin_token_id = null;
  var waiting_loop_count = 0;

  function setup_once() {
    $('a.anonymous', container).click(function() {
      $.post($(this).attr('href'), function() {
        State.update(function() {
          Loader.load_hash('#welcome');
        });
      });
      return false;
    });

    $('form', container).submit(function() {
      var $email = $('input[name="email"]', this);
      var email = $.trim($email.val());
      if (!email.length) {
        $email.addClass('error');
      } else {
        $.post(URL, {email: email}, function(response) {
          $('.before', container).hide();
          var cc = $('.after', container);
          $('.email', cc).text(response.email);
          $('.subject', cc).text(response.subject);
          $('.from', cc).text(response.from);
          cc.hide().fadeIn(300);
          waiting_signin_token_id = response.id;
          setTimeout(function() {
            Login.logged_in_yet();
          }, 5 * 1000);
        });
      }
      return false;
    });

    $('input[name="email"]', container).on('focus', function() {
      $('.signin', container).show();
    }).on('blur', function() {
      if (!$(this).val()) {
        $('.signin', container).hide();
      }
    });
  }

  return {
    init: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }

      if (STATE.user && STATE.user.anonymous) {
        $('.play-anonymously:visible', container).hide();
        $('.hint:hidden', container).show();
      } else {
        $('.right:hidden', container).show();
      }
    },
    logged_in_yet: function() {
      $.getJSON(URL, {id: waiting_signin_token_id}, function(response) {
        if (response.signed_in) {
          State.update(function() {
            Loader.load_hash('#city');
          });
        } else {
          waiting_loop_count++;
          setTimeout(function() {
            Login.logged_in_yet();
          }, (5 + waiting_loop_count) * 1000);
        }
      });
    }
  };
})();



Plugins.start('signin', function() {
  Login.init();
});

Plugins.stop('signin', function() {
});
