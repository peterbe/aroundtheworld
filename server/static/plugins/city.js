var City = (function() {
  var container = $('#city');

  function _load_jobs(jobs) {
    $('.jobs li', container).remove();
    var c = $('.jobs', container);
    $.each(jobs, function(i, each) {
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
  }

  return {
     load: function() {
       $.getJSON('/city.json', function(response) {
         $('h2 strong', container).text(response.name);
         if (map && map.getZoom() < 15) {
           var p = new google.maps.LatLng(response.lat, response.lng);
           if (p != map.getCenter()) {
             map.setCenter(p);
           }
           map.setZoom(15);
         }
         _load_jobs(response.jobs);
       });
     }
  };
})();

Plugins.start('city', function() {
  City.load();
});
