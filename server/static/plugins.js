if (typeof PLUGINS !== 'object') throw "constant PLUGINS not defined";

var Plugins = (function() {
  var loaded_plugins = [];
  var callbacks = {};
  var extra_args = {};
  return {
     load: function(id, extra_arg) {
       //L('*load*', id, extra_arg);
       if (PLUGINS[id] && PLUGINS[id].length) {
         if ($.inArray(id, loaded_plugins) == -1) {
           $.each(PLUGINS[id], function (i, plugin_url) {
             if (STATE.debug) {
               if (plugin_url.search(/\?/) == -1) {
                 plugin_url += '?';
               } else {
                 plugin_url += '&';
               }
               plugin_url += 'r=' + Math.random();
             }
             var s = document.createElement('script');
             s.type = 'text/javascript';
             //s.defer = true;
             s.src = plugin_url;
             document.getElementsByTagName('head')[0].appendChild(s);
           });
           loaded_plugins.push(id);
           extra_args[id] = extra_arg;
         } else {
           var c = callbacks[id] || null;
           if (!c) {
             throw id + " doesn't have a callback";
           } else {
             c(extra_arg);
           }
         }
       }
     },
    start: function(id, callback) {
      callbacks[id] = callback;
      var extra_arg = extra_args[id] || null;
      if (extra_arg)
        callback(extra_arg);
      else
        callback();
    }
  }
})();
