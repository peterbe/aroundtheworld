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
