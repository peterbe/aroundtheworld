var Airport = (function() {
  var played_sound = [];
  var container = $('#airport');
  var open_infowindows = [];
  var made_markers = [];
  var _once = false;

  function setup_once() {
    $('.show-map a', container).click(function() {
      Airport.show_on_map();
    });

    $('#airport-tucked a').click(function() {
      $('#airport-tucked').hide();
      container.show();
      Airport.teardown();
      Airport.load();
    });
  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
       sounds.preload('airport-pa');

     },
     confirm: function(name, id, cost) {
       if ($('#airport:hidden').size()) {
         // was on the interactive map
         $('#airport').show();
         if (map.getZoom() != 15) {
           map.setZoom(15);
         }
         $('#airport-tucked').hide();
       }
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
         $('.cant-afford .more-coins', c).text(Utils.formatCost(cost - STATE.user.coins_total, true));
         $('button[type="submit"]', c).attr('disabled', 'disabled');
       }
       sounds.preload('cash-2');
       $('form', c).unbind('submit').submit(function() {
         if (cost > STATE.user.coins_total) {
           return false;
         }
         $.post('/fly.json', {id: $('input[name="id"]', this).val()}, function(response) {
           if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
           if (response.error == 'FLIGHTALREADYTAKEN') {
             Utils.general_error("It appears that flight has already started once.");
             return;
           }
           if (response.error == 'CANTAFFORD') {
             alert("Sorry. Can't afford the ticket");
             Loader.load_hash('#airport');
             return;
           }

           sounds.play('cash-2');
           State.show_coin_change(-1 * response.cost, true);
           if (!response.from_code || !response.to_code) {
             Utils.general_error("No route found for some reason.");
             return;
           }
           var hash = '#fly,' + response.from_code + '->' + response.to_code;
           Loader.load_hash(hash);
           //State.update();
         });
         return false;
       });
     },
     load: function(callback) {
       $('.confirm:visible', container).hide();
       $('.choices:hidden', container).show();
       $.getJSON('/airport.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         $('h2', container).text(response.airport_name);
         $('.current-total', container).text(Utils.formatCost(STATE.user.coins_total, true));
         //var c = $('.destinations', container);
         $('.destinations tbody', container).remove();
         var r;
         $.each(response.destinations, function(i, each) {
           r = $('<tr>');
           r.data('cost', each.cost);
           var a_title;
           if (each.cost > STATE.user.coins_total) {
             r.addClass('cantafford');
             a_title = "You can afford to fly to " + each.name;
           } else {
             r.removeClass('cantafford');
             a_title = "You can not yet afford to fly to " + each.name;
           }
           $('<a href="#">')
               .attr('id', 'code-' + each.code)
               .text(each.name).attr('title', a_title)
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
         callback();
       });
     },
    show_on_map: function() {
      if (map == null) {
        throw "Can't run pinpoint plugin without a map";
      }
      container.hide();
      map.setZoom(3);
      $.getJSON('/airport.json', function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
        $.each(response.destinations, function(i, each) {

          var center = new google.maps.LatLng(each.lat, each.lng);
          var marker = new google.maps.Marker({
             position: center,
            map: map,
            title: each.name,
            draggable: false//,
            //animation: google.maps.Animation.DROP
          });
          made_markers.push(marker);
          var content = '<strong>'+each.name+'</strong><br>';
          content += Utils.formatMiles(each.miles, true) + '<br>';
          content += Utils.formatCost(each.cost, true) + '<br>';
          if (!each.canafford) {
            content += ' <span class="cantafford">can\'t afford it yet</span><br>';
          } else {
            content += ' <a href="#airport,' + each.code + '"';
            content += ' onclick="Airport.confirm(\''+each.name+ '\',\''+each.id+ '\',\''+each.cost+'\');return false">Buy ticket</a>';
          }
          var infowindow = new google.maps.InfoWindow({
              content: content
          });
          google.maps.event.addListener(marker, 'click', function() {
            map.panTo(center);
            $.each(open_infowindows, function() {
              this.close();
            });
            open_infowindows = [];
            open_infowindows.push(infowindow);
            infowindow.open(map, marker);
          });
        })
      });
      $('#airport-tucked').show();
    },
    click_on: function(code) {
      $('a#code-' + code, container).click();
    },
    teardown: function() {
      if (open_infowindows.length) {
        $.each(open_infowindows, function() {
          this.close();
        });
        open_infowindows = [];
      }
      if (made_markers.length) {
        $.each(made_markers, function() {
          this.setVisible(false);
        });
      }

    }
  };
})();

Plugins.start('airport', function(map_or_code) {
  Airport.setup();
  if (map_or_code && map_or_code.search(/[A-Z][A-Z][A-Z]/) == -1) {
    Airport.show_on_map();
  } else {
    Airport.load(function() {
      if (map_or_code && map_or_code.search(/[A-Z][A-Z][A-Z]/) > -1) {
        Airport.click_on(map_or_code);
      }
    });
  }
});


Plugins.stop('airport', function() {
  Airport.teardown();
});
