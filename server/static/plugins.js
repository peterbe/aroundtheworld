if (typeof PLUGINS !== 'object') throw "constant PLUGINS not defined";

var Plugins = (function() {
  var loaded_plugins = [];
  var callbacks = {};
  return {
     load: function(id) {
       if ($.inArray(id, loaded_plugins) == -1 && PLUGINS[id] && PLUGINS[id].length) {
         $.each(PLUGINS[id], function (i, plugin_url) {
           var s = document.createElement('script');
           s.type = 'text/javascript';
           //s.defer = true;
           s.src = plugin_url;
           document.getElementsByTagName('head')[0].appendChild(s);
         });
         loaded_plugins.push(id);
       } else {
         callbacks[id]();
       }
     },
    start: function(id, callback) {
      callbacks[id] = callback;
      callback();
    }
  }
})();
