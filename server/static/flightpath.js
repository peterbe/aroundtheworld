window.FlightPath = Backbone.Model.extend({
   url: '/flightpaths/'
});

window.FlightPathsCollection = Backbone.Collection.extend({
   model: FlightPath,
  url: '/flightpaths/'
});

//var flights = new FlightPathsCollection();

window.FlightPathsView = Backbone.View.extend({
   render: function (map) {

     L(flights);

     var coordinates = [];
     flights.each(function(flightpath) {
       coordinates.push(new google.maps.LatLng(flightpath.get('from')[0], flightpath.get('from')[1]));
       coordinates.push(new google.maps.LatLng(flightpath.get('to')[0], flightpath.get('to')[1]));
     });
     L('coordinates', coordinates);
     var gflightPath = new google.maps.Polyline({
        path: coordinates,
       strokeColor: "#FF0000",
       strokeOpacity: 0.8,
       strokeWeight: 3
     }).setMap(map);

     return this;
   }
});

//var flightsview = new FlightPathsView();

//FlightPath.collection = FlightPathsCollection

//var flights = new FlightPathsCollection();
//flights.fetch();
