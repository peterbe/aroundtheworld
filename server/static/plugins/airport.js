var Airport = (function() {
  var container = $('#airport');
  return {
     confirm: function(name, id, cost) {
       $('.choices', container).hide();
       var c = $('.confirm', container);
       c.show();
       $('.cant-afford:visible', c).hide();
       $('input[name="yes"]', c).removeAttr('disabled');
       $('em', c).text(name);
       $('input[name="id"]', c).val(id);
       $('.price', c).text(Utils.formatCost(cost));
       $('.current-coins', c).text(Utils.formatCost(STATE.user.coins_total));
       $('input[name="cancel"]', c).click(function() {
         c.hide();
         $('.choices', container).show();
       });
       if (cost > STATE.user.coins_total) {
         $('.cant-afford', c).show('fast');
         $('.cant-afford strong', c).text(Utils.formatCost(cost - STATE.user.coins_total));
         $('input[name="yes"]', c).attr('disabled', 'disabled');
       }
       $('form', c).submit(function() {
         if (cost > STATE.user.coins_total) {
           return false;
         }

         $.post('/fly.json', {id: $('input[name="id"]', this).val()}, function(response) {
           if (response.cant_afford) {
             alert("Sorry. Can't afford the ticket");
             Loader.load_hash('#airport');
           } else {
             State.update();
             var hash = 'fly,' + response.from_code + '->' + response.to_code;
             Loader.load_hash(hash);
             window.location.hash = hash;
           }
         });
         return false;
       });
     },
     load: function() {
       $('.confirm:visible', container).hide();
       $('.choices:hidden', container).show();
       $.getJSON('/airport.json', function(response) {
         $('h2', container).text(response.airport_name);
         $('.current-total', container).text(STATE.user.coins_total);
         //var c = $('.destinations', container);
         $('.destinations tbody', container).remove();
         var r;
         $.each(response.destinations, function(i, each) {
           r = $('<tr>');
           $('<a href="#">')
               .text(each.name)
                 .click(function() {
                   Airport.confirm(each.name, each.id, each.price);
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
