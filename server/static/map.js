function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

function distance(x1, y1, x2, y2) {
  return Math.sqrt(Math.pow(x1 - x2, 2) + Math.pow(y1 - y2, 2));
}

function calculate_angle(center, p1) {
  var p0 = {
    x: center.x,
    y: center.y
      - Math.sqrt(Math.abs(p1.x - center.x)
                  * Math.abs(p1.x - center.x)
                  + Math.abs(p1.y - center.y) * Math.abs(p1.y - center.y))};
  return (2 * Math.atan2(p1.y - p0.y, p1.x - p0.x)) * 180 / Math.PI;
}


//-------
//------

function initialize(callback) {

  //preload_sound('jet-taking-off');
  sounds.preload('jet-taking-off');

  var opts = {
     zoom: 5,
    //center: myLatLng,
    center: LATLNGS.kansas,
    mapTypeId: google.maps.MapTypeId.TERRAIN
  };

  //var airplane;
  var map = new google.maps.Map(document.getElementById("map_canvas"), opts);


//  play_sound(
  /*
  var flightPlanCoordinates = [LATLNGS.sanfran, LATLNGS.raleigh];
  var flightPath = new google.maps.Polyline({
     path: flightPlanCoordinates,
    strokeColor: "#FF0000",
    strokeOpacity: 1.0,
    strokeWeight: 2
  });

  flightPath.setMap(map);
  */
  callback(map);
}

var _init_callbacks = [];
function mapInitialized(callback) {
  _init_callbacks.push(callback);
}

var map;
$(function() {
  initialize(function(map) {
    $.each(_init_callbacks, function(i, callback) {
      callback(map);
    });
  });
});
