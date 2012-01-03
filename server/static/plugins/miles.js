var Miles = (function() {
  var container = $('#miles');

  function _show_flights(flights) {
    $.each(flights, function(i, each) {
      $('.flightlog:hidden', container).show();

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
      c.appendTo($('.flightlog tbody', container));
    });

  }

  return {
     load: function() {
       $.getJSON('/miles.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         $('.miles-friendly', container)
           .text(Utils.formatMiles(STATE.user.miles_total) + ' miles');
         $('.percentage', container).text(response.percentage);
         $('.no-cities', container).text(response.no_cities + ' cities');
         $('.short-stats:hidden', container).fadeIn(100);
         _show_flights(response.flights);
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
