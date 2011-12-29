var FlightZoom = (function() {
  return {
     fit: function (map, location, callback) {
       var n, w, e, s;
       if (map.getCenter().lat() > location.lat()) {
         n = map.getCenter().lat();
         s = location.lat();
       } else {
         s = map.getCenter().lat();
         n = location.lat();
       }
       if (map.getCenter().lng() > location.lng()) {
         e = map.getCenter().lng();
         w = location.lng();
       } else {
         w = map.getCenter().lng();
         e = location.lng();
       }
       var sw = new google.maps.LatLng(s, w);
       var ne = new google.maps.LatLng(n, e);

       //L('Compare', map.getCenter().lat(), location.lat());
       //L('And', map.getCenter().lng(), location.lng());
       //var bound = new google.maps.LatLngBounds(sw, ne);
       //map.setZoom(level);
       //setTimeout(function () {
         //airplane._place_point(sw);
         //L('SW', sw);
         //L('NE', ne);
         var bounds = new google.maps.LatLngBounds(sw, ne);
         map.fitBounds(bounds);
         //L('contains sw?', bounds.contains(sw));
         //L('contains ne?', bounds.contains(ne));
         //map.panToBounds(bounds);
       //}, 2*1000);

       if (callback) {
         callback(bounds);
       }

       //map.panTo(location);
       //map.setZoom(level);
       //map.getZoom
       //map.setZoom

     }
  }
})();



var Flying = (function() {
  return {
     animate: function (route) {
       if (map === null) {
         throw "Can't run flying plugin without map";
       }
       //sounds.preload('jet-taking-off');
       $.getJSON('/fly.json', {route: route}, function(response) {
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
             setTimeout(function() {
               State.update();
             }, 1000);
           });

         });
       });
     }
  };
})();

Plugins.start('flying', function(route) {
  Flying.animate(route);
});
