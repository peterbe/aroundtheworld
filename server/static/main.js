var Loader = (function() {
  return {
     load_hash: function (hash) {
       $('.overlay:visible').hide();
       if ($(hash + '.overlay').size()) {
         $(hash + '.overlay').show();
         Plugins.load(hash.substr(1, hash.length - 1));
       }
    }
  }
})();

mapInitialized(function(map) {
  if (window.location.hash) {
    Loader.load_hash(window.location.hash);
  }

  $('a.overlay-changer').click(function() {
    Loader.load_hash($(this).attr('href'));
  });

});
