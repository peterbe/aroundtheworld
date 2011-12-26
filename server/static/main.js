var Loader = (function() {
  return {
     load_hash: function (hash) {
       L('*loading*', hash);
       var arg = hash.split(',')[1] || null;
       hash = hash.split(',')[0];
       if ($(hash + '.overlay').size()) {
         $('.overlay:visible').hide();
         $(hash + '.overlay').show();
         Plugins.load(hash.substr(1, hash.length - 1), arg);
       }
    }
  }
})();

var State = (function() {
  return {
     update: function() {
       $.getJSON('/state.json', function(response) {
         STATE = response.state;
         $('#usernav').load('/state.html');  // lazy! FIXME: make this all javascript template instead one day
       });
     }
  }
})();

mapInitialized(function(map) {

  $('a.overlay-changer').click(function() {
    Loader.load_hash($(this).attr('href'));
  });

  if (window.location.hash) {
    Loader.load_hash(window.location.hash);
  } else {
    Loader.load_hash('#welcome');
  }

});
