function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

function initialize(callback) {
  var LATLNGS = getLATLNGs();

  var myOptions = {
     zoom: 6,
     center: LATLNGS.istanbul,
     mapTypeId: google.maps.MapTypeId.TERRAIN,
    panControl: false,
    zoomControl: false,
    mapTypeControl: false,
    scaleControl: false,
    streetViewControl: false,
    overviewMapControl: false
  };

  var map = new google.maps.Map(document.getElementById("canvas"), myOptions);
  callback(map);
}

window.onload = function() {
  initialize(function() {

    function navigateContent(id) {

      $('.content-block:visible').hide();
      $(id).show();
      setupSlides();
    }
    $('a.nav').on('click', function() {
      //$('.content-block:visible').hide();
      navigateContent($(this).attr('href'));
    });
    if (location.hash && $(location.hash).size()) {
      navigateContent(location.hash);
    }

    //$('#intro').hide(300);
    //$('#facts').show(300);
  });
}
