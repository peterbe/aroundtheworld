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

       /*
         new google.maps.Rectangle({
            bounds: new google.maps.LatLngBounds(sw, ne),
           strokeColor: '#ff0000',
           strokeWeight: 1,
           fillColor: '#ff3300',
           fillOpacity: 0.5
         }).setMap(map);
         L(map);
        */
       var bounds = new google.maps.LatLngBounds(sw, ne);
       map.fitBounds(bounds);

       if (callback) {
         callback(bounds);
       }

     }
  }
})();
