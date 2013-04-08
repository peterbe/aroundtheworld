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
    sounds.preload('airport-pa');
  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
     },
     confirm: function(name, code, cost, first, locked) {
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
       if (first) {
         $('.first-class', c).show();
         $.getJSON('/flight-stats.json', {code: code, first: true}, function(response) {
           if (response.html) {
             $('.first-class .flight-stats', c)
               .html(response.html)
                 .show();
           } else {
             $('.first-class .flight-stats', c)
               .hide();
           }
         });
       } else {
         $('.first-class', c).hide();
       }
       $('.cant-afford:visible', c).hide();
       $('button[type="submit"]', c).removeAttr('disabled');
       $('em', c).text(name);
       $('input[name="code"]', c).val(code);
       if (first) {
         $('input[name="first"]', c).val(true);
       } else {
         $('input[name="first"]', c).val('');
       }
       $('.cost', c).text(Utils.formatCost(cost, true));
       $('.current-coins', c).text(Utils.formatCost(STATE.user.coins_total, true));
       $('button[type="reset"]', c).click(function() {
         c.hide();
         Airport.load(function() {
           $('.choices', container).show();
         });
       });

       if (locked) {
         $('.locked', c).fadeIn(300);
         $('button[type="submit"]', c).attr('disabled', 'disabled');
       } else if (cost > STATE.user.coins_total) {
         $('.cant-afford', c).fadeIn(300);
         $('.cant-afford .more-coins', c).text(Utils.formatCost(cost - STATE.user.coins_total, true));
         $('button[type="submit"]', c).attr('disabled', 'disabled');
       } else {
         $('.locked', c).hide();
         $('.cant-afford', c).hide();
       }
       sounds.preload('cash-2');
       $('form', c).unbind('submit').submit(function() {
         if (cost > STATE.user.coins_total) {
           return false;
         }
         var data = {
            code: $('input[name="code"]', this).val(),
           first: $('input[name="first"]', this).val()
         };
         $.post('/fly.json', data, function(response) {
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
           if (response.error == 'LOCKED') {
             alert("Sorry. Destination locked.");
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
           if (map.getZoom() != 15) {
             map.setZoom(15);
           }
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
         var a_title;
         $.each(response.destinations, function(i, each) {
           r = $('<tr>');
           r.data('cost', each.cost);
           if (each.locked) {
             r.addClass('locked');
             a_title = "Flying to " + each.name + " is locked until you sign in";
           } else {
             r.removeClass('locked');
             if (!each.canafford) {
               r.addClass('cantafford');
               a_title = "You can not yet afford to fly to " + each.name;
             } else {
               r.removeClass('cantafford');
               a_title = "You can afford to fly to " + each.name;
             }
           }

           if (each.flag) {
             $('<td>')
               .append($('<img>')
                       .attr('alt', each.country)
                       .attr('src', each.flag))
                 .appendTo(r);
           } else {
             $('<td>')
               .text('')
                 .appendTo(r);
           }
           $('<td>')
             .text(each.name)
               .appendTo(r);

           $('<td>')
             .addClass('distance').addClass('number')
               .text(Utils.formatMiles(each.miles, true))
                 .appendTo(r);

           $('<a href="#">')
               .data('code', each.code)
               .data('first', false)
               .text(Utils.formatCost(each.cost.economy, true))
               .attr('title', a_title)
                 .click(function() {
                   Airport.confirm(each.name, each.code, each.cost.economy, false, each.locked);
                   return false;
                 }).appendTo($('<td>')
                             .addClass('cost')
                             .addClass('number')
                             .appendTo(r));

           if (each.cost.first) {
             $('<a href="#">')
                 .data('code', each.code)
                 .data('first', true)
                 .attr('title', 'First Class tickets are for first class people')
                 .text(Utils.formatCost(each.cost.first, true))
                   .click(function() {
                     Airport.confirm(each.name, each.code, each.cost.first, true, each.locked);
                     return false;
                   }).appendTo($('<td>')
                               .addClass('cost')
                               .addClass('number')
                               .appendTo(r));
           } else {
             $('<td>')
               .addClass('cost')
                 .text('not available')
                   .appendTo(r);
           }
           if (each.locked) {
           $('<td>')
             .append($('<img>')
                     .attr('src', LOCK_IMG_URL)
                     .attr('alt', "Locked until you sign in"))
               .appendTo(r);
           } else {
             $('<td>').text(' ').appendTo(r);
           }

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
      if (map === null) {
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
          content += Utils.formatCost(each.cost.economy, true);
          if (each.cost.first) {
            content += ' (' + Utils.formatCost(each.cost.first, true) + ' First Class)';
          }
          content += '<br>';
          if (each.locked) {
            content += ' <span class="locked">locked until you sign in</span><br>';
          } else if (!each.canafford) {
            content += ' <span class="cantafford">can\'t afford it yet</span><br>';
          } else {
            content += ' <a href="#airport,' + each.code + '"';
            content += ' onclick="Airport.confirm(\''+each.name+ '\',\''+each.code+ '\',\''+each.cost.economy+'\',false,false);return false">Buy ticket</a>';
            if (each.cost.first) {
              content += ' <a href="#airport,' + each.code + '"';
              content += ' onclick="Airport.confirm(\''+each.name+ '\',\''+each.code+ '\',\''+each.cost.first+'\',true,false);return false">First Class</a>';
            }
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
        });
      });
      $('#airport-tucked').show();
    },
    click_on: function(code) {
      var the_one;
      $('a', container).each(function(i, each) {
        if ($(each).data('code') == code) {
          if (!$(each).data('first')) {
            the_one = $(each);
          }
        }
      });
      if (the_one) {
        the_one.click();
      }
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
