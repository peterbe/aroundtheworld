mapInitialized(function(map) {
  map.setCenter(LATLNGS.sanfran);
  map.setZoom(9);
  setTimeout(function() {
    FlightZoom.fit(map, LATLNGS.raleigh, function(bounds) {
      L('zoomed out');
      airplane.fly(LATLNGS.sanfran, LATLNGS.raleigh);
    });
  }, 2*1000);
  /*
    setTimeout(function() {
      airplane.fly(LATLNGS.raleigh, LATLNGS.sanfran, function() {
        airplane.fly(LATLNGS.sanfran, LATLNGS.kansas);
      });
    }, 1000);
   */

});
