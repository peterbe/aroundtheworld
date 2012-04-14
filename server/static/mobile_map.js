function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

function initialize(callback) {
  callback(null);
}

var _init_callbacks = [];
function mapInitialized(callback) {
  _init_callbacks.push(callback);
}

var map, latlngcontrol;

function setupMap() {
  L($('script'));
  var center = new google.maps.LatLng(STATE.location.lat, STATE.location.lng);
  var zoom = 15;  // known locations is zoomed in
  var opts = {
     zoom: zoom,
    center: center,
    disableDefaultUI: true,
    mapTypeId: google.maps.MapTypeId.TERRAIN
  };
  map = new google.maps.Map(document.getElementById("map_canvas"), opts);
  latlngcontrol = new LatLngControl(map);

}

$(function() {
  initialize(function(map) {
    $.each(_init_callbacks, function(i, callback) {
      callback(map);
    });
  });
});
