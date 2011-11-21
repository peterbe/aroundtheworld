window.FlightPath = Backbone.Model.extend({

});

window.FlightJourney = Backbone.Collection.extend({
   model: FlightPath,
  url: '/flightpaths'
});
