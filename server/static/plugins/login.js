var Login = (function() {
  var container = $('#login');

  return {
    init: function() {
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
