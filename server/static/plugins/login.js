var Login = (function() {
  var container = $('#login');
  var _once = false;

  function setup_once() {
    $('a.anonymous', container).click(function() {
      $.post($(this).attr('href'), function() {
        State.update(function() {
          Loader.load_hash('#welcome');
        });
      });
      return false;
    });
  }

  return {
    init: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }

      if (STATE.user && STATE.user.anonymous) {
        $('.right:visible', container).hide();
        $('.hint:hidden', container).show();
      } else {
        $('.right:hidden', container).show();
      }
    }
  };
})();



Plugins.start('login', function() {
  Login.init();
});

Plugins.stop('login', function() {
});
