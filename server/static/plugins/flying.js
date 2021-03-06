
var Flying = (function() {
  return {
     animate: function (route) {
       if (map === null) {
         throw "Can't run flying plugin without map";
       }
       $.getJSON('/fly.json', {route: route}, function(response) {
         if (response.error == 'INVALIDROUTE') {
           Utils.general_error("It seems that you have selected an invalid route.");
           return;
         }

         var from = {lat: response.from.lat, lng: response.from.lng};
         from = new google.maps.LatLng(from.lat, from.lng);
         var to = {lat: response.to.lat, lng: response.to.lng};
         to = new google.maps.LatLng(to.lat, to.lng);
         var miles = response.miles;
         $('#usernav .user-location:visible').hide();
         if (map.getCenter() != from) {
           // extra assurance that the animation starts from the right place
           map.setCenter(from);
         }
         FlightZoom.fit(map, to, function(bounds) {
           latlngcontrol.animate(from, to, miles, function() {
             State.show_miles_change(miles, true);
             if (map.getZoom() < 15) {
               map.setCenter(to);
               map.setZoom(15);
             }
             var hash = '#city';
             Loader.load_hash(hash);
             State.update();
           });

         });
       });
     }
  };
})();

Plugins.start('flying', function(route) {
  Flying.animate(route);
});


Plugins.stop('flying', function() {
  // nothing
});
