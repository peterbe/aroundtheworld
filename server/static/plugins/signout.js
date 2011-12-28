var Signout = (function() {
  var container = $('#signout');
  return {
     signout: function() {
       $('.pleasewait:hidden', container).show();
       $('.success:visible', container).hide();
       $.post('/logout/', function(response) {
         $('.pleasewait:visible', container).hide();
         $('.success:hidden', container).show();
       });
     }
  };
})();

Plugins.start('signout', function() {
  Signout.signout();
});
