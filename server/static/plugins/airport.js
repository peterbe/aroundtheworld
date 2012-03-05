var Airport = (function() {
  var played_sound = [];
  var container = $('#airport');
  return {
     confirm: function(name, id, cost) {
       $('.choices', container).hide();
       var c = $('.confirm', container);
       c.show();
       $('.cant-afford:visible', c).hide();
       $('button[type="submit"]', c).removeAttr('disabled');
       $('em', c).text(name);
       $('input[name="id"]', c).val(id);
       $('.cost', c).text(Utils.formatCost(cost, true));
       $('.current-coins', c).text(Utils.formatCost(STATE.user.coins_total, true));
       $('button[type="reset"]', c).click(function() {
         c.hide();
         $('.choices', container).show();
       });
       if (cost > STATE.user.coins_total) {
         $('.cant-afford', c).show('fast');
         $('.cant-afford strong', c).text(Utils.formatCost(cost - STATE.user.coins_total, true));
         $('button[type="submit"]', c).attr('disabled', 'disabled');
       }
       $('form', c).unbind('submit').submit(function() {
         if (cost > STATE.user.coins_total) {
           return false;
         }
         $.post('/fly.json', {id: $('input[name="id"]', this).val()}, function(response) {
           if (response.cant_afford) {
             alert("Sorry. Can't afford the ticket");
             Loader.load_hash('#airport');
           } else {
             //State.update();
             State.show_coin_change(-1 * response.cost, true);
             var hash = '#fly,' + response.from_code + '->' + response.to_code;
             Loader.load_hash(hash);
           }
         });
         return false;
       });
     },
     load: function() {
       sounds.preload('airport-pa');
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
                   Airport.confirm(each.name, each.id, each.cost);
                   return false;
                 }).appendTo($('<td>').appendTo(r));
           $('<td>')
             .addClass('distance').addClass('number')
               .text(Utils.formatMiles(each.miles, true))
                 .appendTo(r);
           $('<td>')
             .addClass('cost').addClass('number')
               .text(Utils.formatCost(each.cost, true))
                 .appendTo(r);

           $('.destinations', container).append($('<tbody>').append(r));
         }); // $.each

         if (!STATE.user.disable_sound) {
           if ($.inArray(response.airport_name, played_sound) == -1) {
             sounds.play('airport-pa');
             played_sound.push(response.airport_name);
           }
         }
         Utils.update_title();

       });
     }
  };
})();

Plugins.start('airport', function() {
  Airport.load();
});


Plugins.stop('airport', function() {
  //Airport.teardown();
});
