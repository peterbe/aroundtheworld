var VELOCITY = 90.0;//120.0; // pixels/second
var MIN_SCALING_START = 0.3;  // minimum percentage scale
var MIN_SCALING_FINISH = 0.05;  // minimum percentage scale
var MAX_SCALING = 0.9;  // maximum percentage scale
var IMAGE_RADIUS = 107; // see the airplane image

function calculateAngle(center, p1) {
  var p0 = {
    x: center.x,
    y: center.y
      - Math.sqrt(Math.abs(p1.x - center.x)
                  * Math.abs(p1.x - center.x)
                  + Math.abs(p1.y - center.y) * Math.abs(p1.y - center.y))};
  return (2 * Math.atan2(p1.y - p0.y, p1.x - p0.x)) * 180 / Math.PI;
}

function distance(x1, y1, x2, y2) {
  return Math.sqrt(Math.pow(x1 - x2, 2) + Math.pow(y1 - y2, 2));
}


/**
 * LatLngControl class displays the LatLng and pixel coordinates
 * underneath the mouse within a container anchored to it.
 * @param {google.maps.Map} map Map to add custom control to.
 */
function LatLngControl(map) {
  /**
   * Offset the control container from the mouse by this amount.
   */
  //this.ANCHOR_OFFSET_ = new google.maps.Point(8, 8);
  //this.

  /**
   * Pointer to the HTML container.
   */
  this.div_ = this.createHtmlNode_();
  //this.div_jelement = $(this.div_);

  // Add control to the map. Position is irrelevant.
  //map.controls[google.maps.ControlPosition.TOP].push(this.div_);
  //var panes = this.getPanes();
  //panes.overlayImage.appendChild(this.div_);

  // Bind this OverlayView to the map so we can access MapCanvasProjection
  // to convert LatLng to Point coordinates.
  this.setMap(map);

  // Register an MVC property to indicate whether this custom control
  // is visible or hidden. Initially hide control until mouse is over map.
  //this.set('visible', false);
}


// Extend OverlayView so we can access MapCanvasProjection.
LatLngControl.prototype = new google.maps.OverlayView();

LatLngControl.prototype.scale = function(p) {
  // even though we only want to change the scale,
  // we always have to set the rotation
  var transform = 'scale(' + p + ') rotate(' + this.rotation_angle + 'deg)';
  $(this.div_).css({
    "-moz-transform" : transform,
    "-webkit-transform" : transform
  });
};

LatLngControl.prototype.draw = function() {
  var self = this;
  //L('IN draw()');
  var from = self.get('from');
  var to = self.get('to');
  var miles = self.get('miles');  // real world miles
  if (!from || !to) {
    // the from and to hasn't been defined yet
    //L("this.get('from') not set :(");
    return;
  }
  // so it only animates the draw once
  self.set('from', null);
  self.set('to', null);

  //L("this.get('from')=", from);

  var panes = this.getPanes();

  if (!$('#latlng-control').size()) {
    // first time
    if (typeof panes == 'undefined') {
      throw "getPanes not loaded :(";
    }
    panes.overlayImage.appendChild(this.div_);
  }

  /* debugging
  var coordinates = [this.get('from'), this.get('to')];
     var gflightPath = new google.maps.Polyline({
        path: coordinates,
       strokeColor: "#FF0000",
       strokeOpacity: 0.8,
       strokeWeight: 3
     }).setMap(map);
  */

  var point1 = this.getProjection().fromLatLngToContainerPixel(from);
  var point2 = this.getProjection().fromLatLngToContainerPixel(to);

  if (point1 === null) {
    //L('from?', from);
    throw "point1 is null!";
  }
  if (point2 === null) {
    //L('to?', to);
    throw "point2 is null!";
  }
  this.rotation_angle = calculateAngle(point1, point2);
  this.scale(MIN_SCALING_START);

  var d = distance(point1.x, point1.y, point2.x, point2.y);

  //L('DISTANCE', d);
  var velocity = VELOCITY;
  if (d < 100) velocity *= 0.6; // 40% slower
  else if (d < 200) velocity *= 0.7; // 30% slower
  else if (d < 300) velocity *= 0.8; // 20% slower
  else if (d < 500) velocity *= 0.9; // 10% slower

  //else if (d > 1000) velocity *= 1.1; // 10% faster
  //else if (d > 2500) velocity *= 1.2; // 20% faster
  //else if (d > 4000) velocity *= 1.3; // 30% faster
  //else if (d > 6500) velocity *= 1.4; // 40% faster

  var t = d / velocity;
  //L("D", d, "V", velocity, "T", t);
  this.div_.style.left = (point1.x - IMAGE_RADIUS/2) + 'px';
  this.div_.style.top = (point1.y - IMAGE_RADIUS/2) + 'px';
  $(this.div_).show();


  var d_left = point1.x - point2.x;// + this.left_radius;
  var d_top = point1.y - point2.y;// + this.top_radius;

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

  var left, right, halfway, length;
  if (point1.x > point2.x) {
    right = point1.x - IMAGE_RADIUS / 2;
    left = point2.x - IMAGE_RADIUS / 2;
  } else {
    left = point1.x - IMAGE_RADIUS / 2;
    right = point2.x - IMAGE_RADIUS / 2;
  }
  halfway = (point1.x + point2.x - IMAGE_RADIUS) / 2 ;
  length = (right - left) / 2;

  if (!STATE.user.disable_sound) {
    setTimeout(function() {
      if (t > 10) {
        sounds.play('jet-taking-off-long');
      } else {
        sounds.play('jet-taking-off');
      }
    }, 1 * 1000);
  }


  /* See more on http://jqueryui.com/demos/effect/#easing */
  /* XXX: Consider installing
   * http://playground.benbarnett.net/jquery-animate-enhanced/
   * for better animation with CSS3 transforms
   */
  var opts = {
     duration: t * 1000,
      //easing: 'easeInOutSine',
      easing: 'easeInOutQuint',
      step: function(now, fx) {
        if (fx.prop === 'left') {
          if (now > halfway) {
            // beyond half-way point
            var p = 1 - (now - left - length) / length;
            p = Math.min(Math.max(MIN_SCALING_FINISH, p), MAX_SCALING);
          } else {
            var p = (now - left) / length;
            p = Math.min(Math.max(MIN_SCALING_START, p), MAX_SCALING);
          }

          //p = Math.max(MIN_SCALING, p);
          // do this trick so that we don't have to call m.scale() too often
          p = Math.round(p * 1000, 2) / 1000;
          if (fx.elem.lastp != p) {
            //L(now, p);
            self.scale(p);
            fx.elem.lastp = p;
          }
        }

      }
  };
  opts.complete = function() {
    self.scale(MIN_SCALING_FINISH);
    if (self.get('callback')) {
      self.get('callback')();
    }
  };

  $(this.div_).animate(animation, opts);

};



/**
 * @private
 * Helper function creates the HTML node which is the control container.
 * @return {HTMLDivElement}
 */
LatLngControl.prototype.createHtmlNode_ = function() {
  var div = document.createElement('div');
  div.style.display = "none";
  div.style.border = "none";
  div.style.position = "absolute";
  div.style.paddingLeft = "0px";
  div.id = 'latlng-control';
  div.index = 100;
  var img = document.createElement("img");
  img.src = "/static/images/airplane.png";
  div.appendChild(img);
  return div;
};

/**
 * MVC property's state change handler function to show/hide the
 * control container.
 */
LatLngControl.prototype.visible_changed = function() {
  //L('visible_changed:', this.get('visible'));
  this.div_.style.display = this.get('visible') ? '' : 'none';
};

/**
 * Specified LatLng value is used to calculate pixel coordinates and
 * update the control display. Container is also repositioned.
 * @param {google.maps.LatLng} latLng Position to display

LatLngControl.prototype.updatePosition = function(latLng) {
  var projection = this.getProjection();
  var point = projection.fromLatLngToContainerPixel(latLng);
  L('POINT', point);
  L('(X,Y)', point.x, point.y);
  // Update control position to be anchored next to mouse position.
  this.node_.style.left = point.x + this.ANCHOR_OFFSET_.x + 'px';
  this.node_.style.top = point.y + this.ANCHOR_OFFSET_.y + 'px';

  // Update control to display latlng and coordinates.
  this.node_.innerHTML = [
                          latLng.toUrlValue(4),
                          '<br/>',
                          point.x,
                          'px, ',
                          point.y,
                          'px'
                         ].join('');
};
*/


LatLngControl.prototype.animate = function(from, to, miles, callback) {
//  from = new google.maps.LatLng(from.lat, from.lng);
//  to = new google.maps.LatLng(to.lat, to.lng);
  this.set('from', from);
  this.set('to', to);
  this.set('miles', miles);
  this.set('callback', callback);
  this.set('visible', true);
  this.draw();
};
