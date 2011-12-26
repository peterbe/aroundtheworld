var Welcome = (function() {
  var container = $('#welcome');
  return {
     update: function() {
       $('.alternative', container).hide();
       if (!STATE.user) {
         $('.not-logged-in', container).show();
       } else if (!STATE.location) {
         $('.not-chosen-location', container).show();
         $.getJSON('/location.json', function(response) {
           var c = $('select[name="id"]', container);
           $.each(response.locations, function(i, each) {
             $('<option>')
               .attr('value', each.id)
                 .text(each.name)
                   .appendTo(c);
           });
           c.on('change', function() {
             $(this).parent('form').submit();
           });
           $('.not-chosen-location form', container).on('submit', function() {
             var id = $('select[name="id"] option:selected', container).attr('value');
             $.post('/location.json', {id:id}, function(response) {
               State.update();
               var new_hash = '#city,' + STATE.location.id;
               window.location.hash = new_hash;
               Loader.load_hash(new_hash);
             });
             return false;
           });
         });

       } else {
         $('.welcome-back', container).show();
         var c = $('.welcome-back', container);
         $('.current-location', c).html(STATE.location.name);
         var hash = '#city,' + STATE.location.id;
         $('.overlay-changer', c)
           .attr('href', hash)
             .click(function() {
               Loader.load_hash(hash);
             });

       }
     }
  };
})();

Plugins.start('welcome', function() {
  // called every time this plugin is loaded
  Welcome.update();
});
