window.FlightPath = Backbone.Model.extend({

});

window.FlightJourney = Backbone.Collection.extend({
   model: FlightPath,
  url: '/flightpaths/'
});

var flight_journeys = new FlightJourney();
flight_journeys.fetch();
