var VELOCITY = 120.0; // pixels/second
var MIN_SCALING = 0.15;  // minimum percentage scale
var MAX_SCALING = 0.7;  // maximum percentage scale
function AirplaneMarker(map, image_radius) {
  //this.latlng_ = latlng;
  // Once the LatLng and text are set, add the overlay to the map.  This will
  // trigger a call to panes_changed which should in turn call draw.
  this.setMap(map);
  this.image_radius = image_radius;
  //this.destination = destination;

}

AirplaneMarker.prototype = new google.maps.OverlayView();

AirplaneMarker.prototype.scale = function(p) {
//  L('scale', p);
  this.div_jelement.css({
    "-moz-transform" : 'scale(' + p + ') rotate(' + this.rotation_angle + 'deg)',
    "-webkit-transform" : 'scale(' + p + ') rotate(' + this.rotation_angle + 'deg)'
  });
};

AirplaneMarker.prototype.draw = function() {

  L('draw()!!');
  if (!this.div_jelement) {
    //L('creating this.div_jelement');
    var me = this;

    // Check if the div has been created.
    var div = this.div_;
    if (!div) {
      // Create a overlay text DIV
      div = this.div_ = document.createElement('div');
      // Create the DIV representing our AirplaneMarker
      div.style.display = "none";
      div.style.border = "none";
      div.style.position = "absolute";
      div.style.paddingLeft = "0px";
      //div.style.width = '200px';
      //div.style.cursor = 'pointer';

      var img = document.createElement("img");
      img.src = PLANE_IMG_URL;
      div.appendChild(img);

      // Then add the overlay to the DOM
      var panes = this.getPanes();
      panes.overlayImage.appendChild(div);
    }
    // create this as an instance of jquery so that we scale()
    // is called a lot it doesn't need to make the conversion from DOM element
    // to jquery element every single time.
    this.div_jelement = $(this.div_);
  }

};

AirplaneMarker.prototype.fly = function(latlng, destination, callback) {
  L('fly()!');
  if (!this.div_jelement) {
    this.draw();
  }
  this.div_jelement.show();
  this.latlng_ = latlng;
  this.destination = destination;

  // Position the overlay
  var point = this.getProjection().fromLatLngToDivPixel(this.latlng_);
  var point2 = this.getProjection().fromLatLngToDivPixel(this.destination);

  this.rotation_angle = calculate_angle(point, point2);
  //L('ROTATION_ANGLE', this.rotation_angle);
  this.scale(MIN_SCALING);

  var d = distance(point.x, point.y, point2.x, point2.y);

  var t = d / VELOCITY;
  this.div_.style.left = (point.x - this.image_radius) + 'px';
  this.div_.style.top = (point.y - this.image_radius) + 'px';
  //this._place_point(point);
  //this._place_point(point2);
  var d_left = point.x - point2.x;// + this.left_radius;
  var d_top = point.y - point2.y;// + this.top_radius;
  //L('d_left', d_left);
  //L('point.x', point.x);
  //L('point2.x', point2.x);
  //L('image_radius', this.image_radius);

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
  var h = (point.x + point2.x) / 2;

  var FW = this.image_radius * 2;
  /* See more on http://jqueryui.com/demos/effect/#easing */

  setTimeout(function() {
    sounds.play('jet-taking-off');
    //play_sound('jet-taking-off');
  }, 3* 1000);

  var self = this;

  var opts = {
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
          p = Math.min(Math.max(MIN_SCALING, p), MAX_SCALING);
          // do this trick so that we don't have to call m.scale() too often
          p = Math.round(p * 100, 2) / 100;
          if (fx.elem.lastp != p) {
            self.scale(p);
            fx.elem.lastp = p;
          }
        }

      }
  };
  if (callback) {
    opts.complete = callback;
  }

  self.div_jelement.animate(animation, opts);
};

AirplaneMarker.prototype._place_point = function(p) {
  /* for debugging positions */
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

AirplaneMarker.prototype.remove = function() {
  L('remove()');
  // Check if the overlay was on the map and needs to be removed.
  if (this.div_) {
    this.div_.parentNode.removeChild(this.div_);
    this.div_ = null;
  }
};

AirplaneMarker.prototype.getPosition = function() {
  return this.latlng_;
};

var airplane;
mapInitialized(function(map) {
  airplane = new AirplaneMarker(map, PLANE_IMG_RADIUS / 2);

  /*
    setTimeout(function() {
      airplane.fly(LATLNGS.raleigh, LATLNGS.sanfran, function() {
        airplane.fly(LATLNGS.sanfran, LATLNGS.kansas);
      });
    }, 1000);
*/

});
