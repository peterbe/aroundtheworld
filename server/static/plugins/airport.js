var Airport = (function() {
  var container = $('#airport');
  return {
     load: function() {
       $.getJSON('/airport.json', function(response) {
         $('h2', container).text(response.airport_name);
         $('.current-total', container).text(STATE.user.coins_total);
         //var c = $('.destinations', container);
         $('.destinations tbody', container).remove();
         var r;
         $.each(response.destinations, function(i, each) {
           r = $('<tr>');
           $('<a>')
             .attr('href', '#fly,' + each.code)
               .text(each.name)
                 .click(function() {
                   alert(each.name);
                   return false;
                 }).appendTo($('<td>').appendTo(r));
           $('<td>')
             .addClass('distance')
               .text(each.distance)
                 .appendTo(r);
           $('<td>')
             .addClass('price')
               .text(each.price)
                 .appendTo(r);

           $('.destinations', container).append($('<tbody>').append(r));
         });
       });
     }
  };
})();

Plugins.start('airport', function() {
  Airport.load();
});
