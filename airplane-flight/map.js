function L() {
   if (window.console && window.console.log)
     console.log.apply(console, arguments);
}

  function CustomMarker(latlng,  map) {
    this.latlng_ = latlng;

    // Once the LatLng and text are set, add the overlay to the map.  This will
    // trigger a call to panes_changed which should in turn call draw.
    this.setMap(map);
  }

  CustomMarker.prototype = new google.maps.OverlayView();

  CustomMarker.prototype.draw = function() {
    var me = this;

    // Check if the div has been created.
    var div = this.div_;
    if (!div) {
      // Create a overlay text DIV
      div = this.div_ = document.createElement('DIV');
      // Create the DIV representing our CustomMarker
      div.style.border = "1px solid red";
      div.style.position = "absolute";
      div.style.paddingLeft = "0px";
      //div.style.cursor = 'pointer';

      var img = document.createElement("img");
      img.src = "airplane.png";
      div.appendChild(img);
      //google.maps.event.addDomListener(div, "click", function(event) {
      //  google.maps.event.trigger(me, "click");
      //});

      // Then add the overlay to the DOM
      var panes = this.getPanes();
      panes.overlayImage.appendChild(div);
    }

    // Position the overlay
    var point = this.getProjection().fromLatLngToDivPixel(this.latlng_);
    if (point) {
      div.style.left = point.x + 'px';
      div.style.top = point.y + 'px';
    }
  };

  CustomMarker.prototype.remove = function() {
    // Check if the overlay was on the map and needs to be removed.
    if (this.div_) {
      this.div_.parentNode.removeChild(this.div_);
      this.div_ = null;
    }
  };

  CustomMarker.prototype.getPosition = function() {
   return this.latlng_;
  };


//-------
  function PointMarker(latlng,  map, left_radius, top_radius, destination) {
    this.latlng_ = latlng;
    // Once the LatLng and text are set, add the overlay to the map.  This will
    // trigger a call to panes_changed which should in turn call draw.
    this.setMap(map);
    this.left_radius = left_radius;
    this.top_radius = top_radius;
    this.destination = destination;
  }

  PointMarker.prototype = new google.maps.OverlayView();

  PointMarker.prototype.draw = function() {
    var me = this;

    // Check if the div has been created.
    var div = this.div_;
    if (!div) {
      // Create a overlay text DIV
      div = this.div_ = document.createElement('DIV');
      // Create the DIV representing our PointMarker
      div.style.border = "1px solid red";
      div.style.position = "absolute";
      div.style.paddingLeft = "0px";
      //div.style.cursor = 'pointer';

      var img = document.createElement("img");
      img.src = "airplane.png";
      div.appendChild(img);
      //google.maps.event.addDomListener(div, "click", function(event) {
      //  google.maps.event.trigger(me, "click");
      //});

      // Then add the overlay to the DOM
      var panes = this.getPanes();
      panes.overlayImage.appendChild(div);
    }

    // Position the overlay
    var point = this.getProjection().fromLatLngToDivPixel(this.latlng_);
    var point2 = this.getProjection().fromLatLngToDivPixel(this.destination);
    L('point2', point2);
    if (point) {
      L('point', point);
      div.style.left = (point.x - this.left_radius) + 'px';
      div.style.top = (point.y - this.top_radius) + 'px';
    }
  };

  PointMarker.prototype.remove = function() {
    // Check if the overlay was on the map and needs to be removed.
    if (this.div_) {
      this.div_.parentNode.removeChild(this.div_);
      this.div_ = null;
    }
  };

  PointMarker.prototype.getPosition = function() {
    return this.latlng_;
  };

//------

var PLACES = {
   kansas: [39.114053, -94.6274636],
  raleigh: [35.772096, -78.6386145],
  sanfran: [37.7749295, -122.4194155]
}

var overlay;
function initialize() {
  var LATLNGS = {};
  for (var k in PLACES) {
    LATLNGS[k] = new google.maps.LatLng(PLACES[k][0], PLACES[k][1]);
  }

  var myOptions = {
     zoom: 5,
    //center: myLatLng,
    center: LATLNGS.kansas,
    mapTypeId: google.maps.MapTypeId.TERRAIN
  };

  var map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);
  overlay = new PointMarker(LATLNGS.sanfran, map, 57, 43, LATLNGS.kansas);
//  L(overlay);
  var flightPlanCoordinates = [LATLNGS.sanfran, LATLNGS.raleigh];
  var flightPath = new google.maps.Polyline({
     path: flightPlanCoordinates,
    strokeColor: "#FF0000",
    strokeOpacity: 1.0,
    strokeWeight: 2
  });

  flightPath.setMap(map);

  return map;
}
window.onload = function() {
  initialize();
}
