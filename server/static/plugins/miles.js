var Miles = (function() {
  var URL = '/miles.json';
  var container = $('#miles');

  function _show_flights(flights) {
    var tbody = $('.flightlog tbody', container);
    $.each(flights, function(i, each) {
      var c = $('<tr>');
      $('<td>')
        .addClass('flight-from')
        .text(each.from.name)
          .appendTo(c);
      $('<td>')
        .html('&rarr;')
          .appendTo(c);
      $('<td>')
        .addClass('flight-to')
        .text(each.to.name)
          .appendTo(c);
      $('<td>')
        .addClass('flight-miles')
        .text(Utils.formatMiles(each.miles))
          .appendTo(c);
      $('<td>')
        .addClass('flight-when')
        .text(each.date)
          .appendTo(c);
      c.appendTo(tbody);
    });
    $('.flightlog', container).hide().fadeIn(400);
  }

  return {
     load: function() {
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         Utils.loading_overlay_stop();
         $('.miles-friendly', container)
           .text(Utils.formatMiles(STATE.user.miles_total) + ' miles');
         $('.percentage', container).text(response.percentage);
         if (response.cities == 1) {
           $('.no-cities', container).text('1 city');
         } else {
           $('.no-cities', container).text(response.no_cities + ' cities');
         }
         $('.no-cities-possible', container).text(response.no_cities_possible + ' cities');
         $('.short-stats', container).hide().fadeIn(600);
         _show_flights(response.flights);
         Utils.update_title();
       });
       if (STATE.location) {
         $('.exit:hidden', container).show();
         $('.exit a', container).attr('title', STATE.location.name);
       } else {
         $('.exit:visible', container).hide();
       }
     },
    teardown: function() {
      Utils.loading_overlay_reset();
      $('.short-stats', container).hide();
      $('.flightlog', container).hide();
      $('tbody tr', container).remove();
    }
  };
})();

Plugins.start('miles', function() {
  // called every time this plugin is loaded
  Miles.load();
});

Plugins.stop('miles', function() {
  Miles.teardown();
});
