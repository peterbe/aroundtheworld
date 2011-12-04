mapInitialized(function(map) {

    setTimeout(function() {
      airplane.fly(LATLNGS.raleigh, LATLNGS.sanfran, function() {
        airplane.fly(LATLNGS.sanfran, LATLNGS.kansas);
      });
    }, 1000);

});
