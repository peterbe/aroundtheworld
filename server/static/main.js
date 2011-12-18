var Loader = (function() {
  return {
     load_hash: function (hash) {
       if ($(hash + '.overlay').size()) {
         $(hash + '.overlay').show();
         loadPlugin(hash.substr(1, hash.length - 1));
       }
     }
  }
})();

mapInitialized(function(map) {
  if (window.location.hash) {
    Loader.load_hash(window.location.hash);
  }
});
