var PLACES = {
   kansas: [39.114053, -94.6274636],
  raleigh: [35.772096, -78.6386145],
  sanfran: [37.7749295, -122.4194155]
}
var LATLNGS = {};

for (var k in PLACES) {
  LATLNGS[k] = new google.maps.LatLng(PLACES[k][0], PLACES[k][1]);
}
