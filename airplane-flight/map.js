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
MIN_SCALING = 0.2;
function PointMarker(latlng,  map, image_radius, destination) {
  this.latlng_ = latlng;
  // Once the LatLng and text are set, add the overlay to the map.  This will
  // trigger a call to panes_changed which should in turn call draw.
  this.setMap(map);
  this.image_radius = image_radius;
  this.destination = destination;
}


PointMarker.prototype = new google.maps.OverlayView();

PointMarker.prototype.scale = function(p) {
  this.div_jelement.css({
    "-moz-transform" : 'scale(' + p + ') rotate(' + this.rotation_angle + 'deg)',
    "-webkit-transform" : 'scale(' + p + ') rotate(' + this.rotation_angle + 'deg)'
  });
};

  PointMarker.prototype.draw = function() {
    var me = this;

    // Check if the div has been created.
    var div = this.div_;
    if (!div) {
      // Create a overlay text DIV
      div = this.div_ = document.createElement('div');
      // Create the DIV representing our PointMarker
      div.style.border = "none";
      div.style.position = "absolute";
      div.style.paddingLeft = "0px";
      //div.style.width = '200px';
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
    this.div_jelement = $(this.div_);


    // Position the overlay
    var point = this.getProjection().fromLatLngToDivPixel(this.latlng_);
    var point2 = this.getProjection().fromLatLngToDivPixel(this.destination);
    //L('point2', point2);
    //L('point', point);

    this.rotation_angle = calculate_angle(point, point2);
    L('ROTATION_ANGLE', this.rotation_angle);
    this.scale(MIN_SCALING);

    var d = distance(point.x, point.y, point2.x, point2.y);
    //L('distance', d);
    var VELOCITY = 100.0; // pixels/second
    var t = d / VELOCITY;
    //L('time', t);
    div.style.left = (point.x - this.image_radius) + 'px';
    div.style.top = (point.y - this.image_radius) + 'px';
    this._place_point(point);
    this._place_point(point2);
    var d_left = point.x - point2.x;// + this.left_radius;
    var d_top = point.y - point2.y;// + this.top_radius;
    L('d_left', d_left);
    L('point.x', point.x);
    L('point2.x', point2.x);
    L('image_radius', this.image_radius);

    var animation = {};

    if (d_left < 0) {
      animation['left'] = '+=';
      d_left *= -1;
    } else {
      animation['left'] = '-=';
    }
    animation['left'] += parseInt(d_left) + 'px';

    if (d_top < 0) {
      animation['top'] = '+=';
      d_top *= -1;
    } else {
      animation['top'] = '-=';
    }
    animation['top'] += parseInt(d_top) + 'px';
//    L(animation);
//    var h = (point.x - this.image_radius + d) / 2;  // half-way point
    var h = (point.x + point2.x) / 2;
    L('DISTANCE', d);
  //  L('H', h);

    var FW = this.image_radius * 2;
    /* See more on http://jqueryui.com/demos/effect/#easing */
    setTimeout(function() {
      $(div).animate(animation, {
         duration: t * 1000,
          easing: 'easeInOutQuint',//'easeInOutSine',
          step: function(now, fx) {
            if (fx.prop === 'left') {
              if (now > h) {
                // beyond half-way point
                var p = 1 - (now - h) / h;
              } else {
                var p = now / h;
              }
//              L(now);
              //L(parseInt(100 * p) + '%');
              p = Math.max(MIN_SCALING, p);
              //L(p);
              me.scale(p);
            }

          }
      });
    }, 1 * 1000);
    //}
  };

  PointMarker.prototype._place_point = function(p) {
    var d = document.createElement('div');
    d.style.border = '2px solid green';
    d.style.backgroundColor = 'green';
    d.style.position = 'absolute';
    d.style.paddingLeft = '0px';
    d.style.paddingTop = '0px';
    d.style.width = '2px';
    d.style.left = p.x + 'px';
    d.style.top = p.y + 'px';
    this.getPanes().overlayImage.appendChild(d);
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
  //overlay = new PointMarker(LATLNGS.sanfran, map, 107/2, LATLNGS.raleigh);
  overlay = new PointMarker(LATLNGS.raleigh, map, 107/2, LATLNGS.sanfran);
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

  return map;
}
window.onload = function() {
  initialize();
}
