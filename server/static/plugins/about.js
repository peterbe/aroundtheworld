var About = (function() {
  var container = $('#about');
  var _once = false;

  function setup_once() {
    // copied from https://developers.google.com/+/plugins/+1button/
    var po = document.createElement('script'); po.type = 'text/javascript'; po.async = true;
    po.src = 'https://apis.google.com/js/plusone.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(po, s);
    L(s);
  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
       Utils.update_title();
     }
  }

})();

Plugins.start('about', function() {
  About.setup();
});


Plugins.stop('about', function() {
  //
});
