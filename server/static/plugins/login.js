var Login = (function() {
  var container = $('#login');

  return {
    init: function() {
      if (STATE.user && STATE.user.anonymous) {
        $('.right:visible', container).hide();
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
