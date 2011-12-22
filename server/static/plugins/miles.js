var Miles = (function() {
  var container = $('#miles');
  return {
     load: function() {
       $.getJSON('/miles.json', function(response) {
         L(response);
         $('.miles-friendly', container).text(response.miles_friendly);
         $('.percentage', container).text(response.percentage);
         $('.short-stats:hidden', container).fadeIn(400);
       });
     }
  };
})();

Plugins.start('miles', function() {
  // called every time this plugin is loaded
  Miles.load();
});
