var City = (function() {
  var container = $('#city');
  return {
     load: function() {
       $.getJSON('/city.json', function(response) {
         $('h2 strong', container).text(response.name);
         if (map && map.getZoom() < 15) {
           var p = new google.maps.LatLng(response.lat, response.lng);
           if (p != map.getCenter()) {
             map.setCenter(p);
           }
           map.setZoom(15);
         }
       });
     }
  };
})();

Plugins.start('city', function() {
  City.load();
});
