var Welcome = (function() {
  var container = $('#welcome');
  return {
     update: function() {
       if (map && !STATE.location) {
         var t0 = new Date().getTime();
         $.getJSON('/iplookup/', function(response) {
           if (response.lat && response.lng) {
             var t1 = new Date().getTime();
             // if it took a really long time, (more than 1 second)
             // then don't bother because it would just look weird
             if ((t1 - t0) < 1000) {
               map.setCenter(new google.maps.LatLng(response.lat, response.lng));
               map.setZoom(5);
             }
           }
         });
       }
       $('.alternative', container).hide();
       if (!STATE.user) {
         $('.not-logged-in', container).show();
       } else if (!STATE.location) {
         $('.not-chosen-location', container).show();
         $.getJSON('/location.json', function(response) {
           var c = $('select[name="id"]', container);
           var text;
           $.each(response.locations, function(i, each) {
             text = each.name;
             if (each.distance) {
               text += ' (' + Utils.formatMiles(each.distance) + ' miles from you)';
             }
             $('<option>')
               .attr('value', each.id)
                 .text(text)
                   .appendTo(c);
           });
           c.on('change', function() {
             $(this).parent('form').submit();
           });
           $('.not-chosen-location form', container).on('submit', function() {
             var id = $('select[name="id"] option:selected', container).attr('value');
             $.post('/location.json', {id:id}, function(response) {
               State.update();
               Loader.load_hash('#city');
             });
             return false;
           });
         });

       } else {
         $('.welcome-back', container).show();
         var c = $('.welcome-back', container);
         $('.current-location', c).html(STATE.location.name);
       }
     }
  };
})();

Plugins.start('welcome', function() {
  // called every time this plugin is loaded
  Welcome.update();
});
