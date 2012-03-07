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

  var _load_dom_element = function(plugin_url) {
    if (STATE.debug) {
      if (plugin_url.search(/\?/) == -1) {
        plugin_url += '?';
      } else {
        plugin_url += '&';
      }
      plugin_url += 'r=' + Math.random();
    }
    if (plugin_url.match(/\.css($|\?)/)) {
      var s = document.createElement('link');
      s.type = 'text/css';
      s.rel = 'stylesheet';
      s.href = plugin_url;
    } else {
      var s = document.createElement('script');
      s.type = 'text/javascript';
      //s.defer = true;
      s.src = plugin_url;
    }
    document.getElementsByTagName('head')[0].appendChild(s);
  };

  return {
     load: function(id, extra_arg) {
       _stop();
       //L('LOAD('+id+')');
       // assert (PLUGINS[id] && PLUGINS[id].length)
       if ($.inArray(id, loaded_plugins) == -1) {
         $.each(PLUGINS[id], function (i, plugin_url) {
           _load_dom_element(plugin_url);
         });
         loaded_plugins.push(id);
         extra_args[id] = extra_arg;
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
