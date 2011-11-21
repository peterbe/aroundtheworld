mapInitialized(function(map) {
  var flight_journeys = new FlightJourney();
  flight_journeys.fetch();

  var fpath = new FlightPath({

    from: LATLNGS.sanfran,
    to: LATLNGS.raleigh
  });
  //L(fpath.get('from').toString());

});
