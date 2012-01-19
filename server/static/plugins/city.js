var City = (function() {
  var container = $('#city');

  function _load_jobs(callback) {
    $.getJSON('/city.json', {get: 'jobs'}, function(response) {
    $('ul.jobs li', container).remove();
      var c = $('ul.jobs', container);
      $.each(response.jobs, function(i, each) {
        var hash = '#' + each.type;
        if (each.category) {
          hash += ',' + each.category.replace(' ','+');
        }
        $('<a>')
        .attr('href', hash)
            .text(each.description)
              .click(function() {
                L($(this).attr('href'));
                Loader.load_hash($(this).attr('href'));
                return true;
              }).appendTo($('<li>').appendTo(c));
      });
      callback();
    });
  }

  function _load_embassy(callback) {
    $.getJSON('/city.json', {get: 'ambassadors'}, function(response) {
      if (response.html) {
        $('.embassy .none:visible', container).hide();
        $('.embassy .html-container', container).html(response.html);
      } else {
        $('.embassy .none:hidden', container).show();
      }
      callback();
    });
  }

  return {
     load: function(page) {
       $.getJSON('/city.json', function(response) {
         $('h2 strong', container).text(response.name);
         if (map && map.getZoom() < 15) {
           var p = new google.maps.LatLng(response.lat, response.lng);
           if (p != map.getCenter()) {
             map.setCenter(p);
           }
           map.setZoom(15);
         }
         $('.section:visible', container).hide();
         if (page == 'embassy') {
           $('.country', container).text(response.country);
           _load_embassy(function() {
             $('.embassy .none', container).hide();
             $('.embassy', container).show();
           });
         } else if (page == 'jobs') {
           _load_jobs(function() {
             $('.jobs', container).show();
           });
         } else {
           $('.home', container).show();
         }

         //_load_jobs(response.jobs);
       });
     }
  };
})();

Plugins.start('city', function(page) {
  City.load(page);
});
