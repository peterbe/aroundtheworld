var Pinpoint = (function() {
  var container = $('#pinpoint');
  var timer;
  var skip_timer;
  var countdown;
  var click_listener;
  var _cities_removed = false;
  var count_questions = 0;

  function _show_question(question) {
    $('#pinpoint-tucked:visible').hide();
    $('#pinpoint-splash h1, #pinpoint-tucked p.current').text(question.name);
    $('#pinpoint-splash:hidden').show();
    //$('#pinpoint:hidden').show();
    setTimeout(function() {
      Pinpoint.start(question.seconds);
      $('#pinpoint-splash').hide(400);
      $('#pinpoint-tucked').show();
    }, 3 * 1000);
  }

  return {
     tick: function () {
       countdown--;
       $('#pinpoint-tucked .timer').text(countdown);
       if (countdown == 0) {
         Pinpoint.stop_timer(true);
       } else {
         timer = setTimeout(function() {
           Pinpoint.tick();
         }, 1000);
       }
     },
     start: function (seconds) {
       countdown = seconds + 1;
       Pinpoint.tick();
       //timeout_timer = setTimeout(function() {
       //  L("time out!");
       //}, seconds * 1000);
       click_listener = google.maps.event.addListener(map, 'click', function(event) {
         google.maps.event.removeListener(click_listener);
         Pinpoint.place_marker(event.latLng);
       });
     },
     place_marker: function (latlng) {
       L("place a marker on", latlng);
       Pinpoint.stop_timer(false);
       var dropped_marker = new google.maps.Marker({
          position: latlng,
         map: map,
         title: "Your guess!",
         draggable: false,
         icon: '/static/images/pinpoint/dropped.png',
         animation: google.maps.Animation.DROP
       });

       $.post('/pinpoint.json', {lat: latlng.lat(), lng:latlng.lng()}, function(response) {
         if (false && response.correct) {
           dropped_marker.setAnimation(google.maps.Animation.BOUNCE);
           setTimeout(function() {
             dropped_marker.setAnimation(null);
           }, 3 * 1000);
         }
         var correct_marker = new google.maps.Marker({
            position: new google.maps.LatLng(response.correct_position.lat, response.correct_position.lng),
           map: map,
           title: "Correct place!",
           draggable: false,
           icon: '/static/images/pinpoint/correct.png',
           animation: google.maps.Animation.DROP
         });
         setTimeout(function() {
         var info_message = response.correct ? "Correct!" : "Sorry";
         info_message += '<br>' + Utils.formatMiles(response.miles, true);
         var infowindow = new google.maps.InfoWindow({
            content: info_message
         });
         infowindow.open(map, dropped_marker);
         }, 2*1000);

         setTimeout(function() {
           Pinpoint.load_next();
         }, 3 * 1000);

       });
     },
     stop_timer: function (timedout) {
       L('stop timer!', timedout);
       clearTimeout(timer);
       $('#pinpoint-tucked').hide();
       if (timedout) {
         Pinpoint.load_next();
       }
     },
     setup: function (callback) {
       if (map == null) {
         throw "Can't run flying plugin without map";
       }

       $.getJSON('/pinpoint.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

         var sw = new google.maps.LatLng(response.center.sw.lat,
                                         response.center.sw.lng);
         var ne = new google.maps.LatLng(response.center.ne.lat,
                                         response.center.ne.lng);
         var bounds = new google.maps.LatLngBounds(sw, ne);
         L("BEFORE", map.getZoom());
         map.fitBounds(bounds);
         /*if (map.getZoom() >
         L("AFTER", map.getZoom());*/

         /*
         new google.maps.Rectangle({
            bounds: new google.maps.LatLngBounds(sw, ne),
           strokeColor: '#ff0000',
           strokeWeight: 1,
           fillColor: '#ff3300',
           fillOpacity: 0.5
         }).setMap(map);
          */

         $('form', container).off('submit').submit(function() {
           container.hide();
           $('#pinpoint-tucked .skip:hidden').show();
           $('#pinpoint-tucked .skip a').click(function() {
             Pinpoint.stop_timer(true);
             return false;
           });
           $('#pinpoint-tucked').show();
           $('#pinpoint-tucked .skip:hidden').show();
           $('#pinpoint-tucked .current:visible').hide();
           countdown = 10 + 1;
           Pinpoint.tick();
           return false;
         });

         Utils.preload_image('/static/images/pinpoint/dropped.png');
         Utils.preload_image('/static/images/pinpoint/correct.png');

         callback();
       });

     },
    teardown: function() {
      throw "WORK HARDER!";
    },
    load_next: function() {
      if (!_cities_removed) {
         var styles = [{
            featureType: "administrative.locality",
           stylers: [{
              visibility: "off"
           }]
         }];
         map.setOptions({styles: styles});
        _cities_removed = true;
      }
      $.getJSON('/pinpoint.json', {next: true}, function(response) {
        _show_question(response.question);
      });
    }
  };
})();

Plugins.start('pinpoint', function() {
  Pinpoint.setup(function() {
    //Pinpoint.load_next();
  });
});


// XXX: this is not implemented yet
Plugins.stop('pinpoint', function() {
  L("CALLING stop pinpoint");
//  Pinpoint.teardown();
});
