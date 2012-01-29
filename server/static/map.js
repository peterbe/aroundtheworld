      function MouseControl(map) {
        /**
         * Offset the control container from the mouse by this amount.
         */
        this.ANCHOR_OFFSET_ = new google.maps.Point(8, 8);

        /**
         * Pointer to the HTML container.
         */
        this.node_ = this.createHtmlNode_();

        // Add control to the map. Position is irrelevant.
        map.controls[google.maps.ControlPosition.TOP].push(this.node_);

        // Bind this OverlayView to the map so we can access MapCanvasProjection
        // to convert LatLng to Point coordinates.
        this.setMap(map);

        // Register an MVC property to indicate whether this custom control
        // is visible or hidden. Initially hide control until mouse is over map.
        this.set('visible', false);
      }

      // Extend OverlayView so we can access MapCanvasProjection.
      MouseControl.prototype = new google.maps.OverlayView();
      MouseControl.prototype.draw = function() {};

      /**
       * @private
       * Helper function creates the HTML node which is the control container.
       * @return {HTMLDivElement}
       */
      MouseControl.prototype.createHtmlNode_ = function() {
        var divNode = document.createElement('div');
        divNode.id = 'mouse-control';
        divNode.index = 101;
        return divNode;
      };

      /**
       * MVC property's state change handler function to show/hide the
       * control container.
       */
      MouseControl.prototype.visible_changed = function() {
        this.node_.style.display = this.get('visible') ? '' : 'none';
      };

      /**
       * Specified LatLng value is used to calculate pixel coordinates and
       * update the control display. Container is also repositioned.
       * @param {google.maps.LatLng} latLng Position to display
       */
      MouseControl.prototype.updatePosition = function(latLng) {
        var projection = this.getProjection();
        var point = projection.fromLatLngToContainerPixel(latLng);

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

var map, latlngcontrol;
function initialize(callback) {

  //preload_sound('jet-taking-off');
  //sounds.preload('jet-taking-off');

  // somewhere in north-western Afria somewhere
  var center = new google.maps.LatLng(26.6093, 7.1498);
  var zoom = 3;

  if (STATE.location) {
    center = new google.maps.LatLng(STATE.location.lat, STATE.location.lng);
    zoom = 15;  // known locations is zoomed in
  }
  var opts = {
     zoom: zoom,
    center: center,
    disableDefaultUI: true,
    mapTypeId: google.maps.MapTypeId.TERRAIN
  };

  //var airplane;
  map = new google.maps.Map(document.getElementById("map_canvas"), opts);
  latlngcontrol = new LatLngControl(map);

  /*
        var mouse = new MouseControl(map);
        google.maps.event.addListener(map, 'mouseover', function(mEvent) {
          mouse.set('visible', true);
        });
        google.maps.event.addListener(map, 'mouseout', function(mEvent) {
          mouse.set('visible', false);
        });
        google.maps.event.addListener(map, 'mousemove', function(mEvent) {
          mouse.updatePosition(mEvent.latLng);
        });
   *
   */

  callback(map);
}

var _init_callbacks = [];
function mapInitialized(callback) {
  _init_callbacks.push(callback);
}

$(function() {
  initialize(function(map) {
    $.each(_init_callbacks, function(i, callback) {
      callback(map);
    });
  });
});
