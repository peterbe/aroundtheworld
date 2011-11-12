var PLACES = {
   kansas: [39.114053, -94.6274636],
  raleigh: [35.772096, -78.6386145],
  sanfran: [37.7749295, -122.4194155],
  istanbul: [41.00527, 28.97696]
};

function getLATLNGs() {
  var latlngs = {};
  for (var k in PLACES) {
    latlngs[k] = new google.maps.LatLng(PLACES[k][0], PLACES[k][1]);
  }
  return latlngs
}
