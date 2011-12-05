mapInitialized(function(map) {

    setTimeout(function() {
      L('about to fly');
      //map.setCenter(LATLNGS.raleigh);
      map.setZoom(map.getZoom()+1);
      //airplane.setMap(map);
      //airplane = new AirplaneMarker(map, PLANE_IMG_RADIUS / 2);
      airplane.init(map);
      airplane.fly(LATLNGS.raleigh, LATLNGS.sanfran, function() {
        airplane.fly(LATLNGS.sanfran, LATLNGS.kansas);
      });
    }, 1000);

});
