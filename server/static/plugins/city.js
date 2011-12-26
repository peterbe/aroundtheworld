var City = (function() {
  var container = $('#city');
  return {
     load: function(search) {
       $.getJSON('/city.json', {search: search}, function(response) {
         if (response.wrong_city) {
           var hash = '#city,' + response.current_city
           Loader.load_hash(hash);
           window.location.hash = hash;
           return;
         }
         $('h2 strong', container).text(response.name);
       });
     }
  };
})();


Plugins.start('city', function(city) {
  City.load(city);
});
