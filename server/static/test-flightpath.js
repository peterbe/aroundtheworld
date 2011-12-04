var flights = new FlightPathsCollection();
var flightsview = new FlightPathsView();

mapInitialized(function(map) {

  flights.fetch({
     success: function(){
       flightsview.render(map);
     }
  });

  var fpath = new FlightPath({
    from: [LATLNGS.sanfran.lat(), LATLNGS.sanfran.lng()],
    to: [LATLNGS.raleigh.lat(), LATLNGS.raleigh.lng()]
  });
  //fpath.save();
  //L(fpath.get('from').toString());

});
