if (typeof PLUGINS !== 'object') throw "constant PLUGINS not defined";

var Plugins = (function() {
  var loaded_plugins = [];
  var callbacks = {};
  var stop_callbacks = {};
  var extra_args = {};
  var last_stop_callback;

  var _stop = function() {
    if (last_stop_callback) last_stop_callback();
  };

  var _load_dom_element = function(plugin_url, callback) {
    if (STATE.debug) {
      if (plugin_url.search(/\?/) == -1) {
        plugin_url += '?';
      } else {
        plugin_url += '&';
      }
      plugin_url += 'r=' + Math.random();
    }
    var s;
    if (plugin_url.match(/\.css($|\?)/)) {
      s = $('<link type="text/css" rel="stylesheet">')
        .attr('href', plugin_url)
          .ready(callback);
    } else {
      s = $('<script type="text/javascript">')
        .attr('src', plugin_url)
          .ready(callback);
    }
    $('head').append(s);
  };

  var _load_dom_elements = function(urls) {
    var url = urls.shift();
    if (url) {
      _load_dom_element(url, function() {
        _load_dom_elements(urls);
      });
    }
  };

  return {
     load: function(id, extra_arg) {
       _stop();
       if ($.inArray(id, loaded_plugins) == -1) {
         loaded_plugins.push(id);
         extra_args[id] = extra_arg;
         _load_dom_elements(PLUGINS[id]);
       } else {
         var c = callbacks[id];
         c(extra_arg);
         last_stop_callback = stop_callbacks[id];
       }
     },
    start: function(id, callback) {
      callbacks[id] = callback;
      var extra_arg = extra_args[id] || null;
      if (extra_arg)
        callback(extra_arg);
      else
        callback();
    },
    stop: function(id, callback) {
      stop_callbacks[id] = callback;
      last_stop_callback = callback;
    }
  }
})();
