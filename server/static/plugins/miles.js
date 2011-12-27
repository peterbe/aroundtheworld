var Miles = (function() {
  var container = $('#miles');
  return {
     load: function() {
       $.getJSON('/miles.json', function(response) {
         $('.miles-friendly', container).text(response.miles_friendly);
         $('.percentage', container).text(response.percentage);
         $('.short-stats:hidden', container).fadeIn(400);
       });
       if (STATE.location) {
         $('.exit:hidden', container).show();
         $('.exit a', container).attr('title', STATE.location.name);
       } else {
         $('.exit:visible', container).hide();
       }
     }
  };
})();

Plugins.start('miles', function() {
  // called every time this plugin is loaded
  Miles.load();
});
