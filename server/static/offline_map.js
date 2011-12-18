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

var map;
$(function() {
  initialize(function(map) {
    $.each(_init_callbacks, function(i, callback) {
      callback(map);
    });
  });
});
