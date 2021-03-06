var MOBILE = false;

var Loader = (function() {
  return {
     load_hash: function (hash, blank_location_hash) {
       // so that reloads works nicer
       if (hash == '#signout' || hash == '#welcome') blank_location_hash = true;
       if (blank_location_hash) {
         if (window.location.hash) {
           window.location.hash = '';
         }
       } else if (hash !== window.location.hash) {
         window.location.hash = hash;
       }
       var arg = hash.split(',')[1] || null;
       hash = hash.split(',')[0];
       if ($(hash + '.overlay').size()) {
         $('.overlay').hide();
         $(hash + '.overlay').show();
         $('img.deferred', hash).each(function() {
           var el = $(this);
           el.attr('src', el.data('src'));
           el.removeClass('deferred');
         });
         Plugins.load(hash.substr(1, hash.length - 1), arg, function() {
           Loader.update_title();
         });
       } else if (hash == '#fly') {
         $('.overlay:visible').hide();
         Plugins.load('flying', arg, function() {
           Loader.update_title();
         });
       } else {
         throw "Unrecognized hash: " + hash;
         //L('ignoring: ' + hash); // xxx: console.warn(..) instead??
       }

       // when blanking the location hash, don't bubble
       if (blank_location_hash) return false;
       return true;
     }
  };
})();

var State = (function() {

  function _show_change(delta, animated, selector, suffix, callback) {
    var e = $('#usernav ' + selector + ' a');
    var b_float = parseFloat(e.text().replace(/[^\d]/g, ''));
    var b = parseInt(b_float, 10);
    if (animated) {
      var c = 0;
      var incr;
      if (delta > 0) incr = 1;
      else incr = -1;
      var deltainterval = setInterval(function() {
        if ((delta > 0 && c >= delta) || (delta < 0 && c <= delta)) {
          clearInterval(deltainterval);
          // make sure it really is right
          e.text(Utils.formatCost(parseInt(b_float + delta, 10)) + ' ' + suffix);
          if (callback) {
            callback();
          }
        } else {
          e.text(Utils.formatCost(b + c) + ' ' + suffix);
        }
        c += incr;
        if (delta > 0) {
          incr++;
        } else {
          incr--;
        }
      }, 35);
    } else {
      e.text(Utils.formatCost(b + delta) + ' ' + suffix);
      if (callback) {
        callback();
      }
    }
  }

  return {
     update: function(callback) {
       $.getJSON('/state.json', function(response) {
         STATE = response.state;
         State.render(STATE);
         if (callback) {
           callback(STATE);
         }
       });
     },
    render: function(state) {
      var container = $('#usernav');
      if (state.user) {
        if (!MOBILE) {
          $('.user-login:visible', container).hide();
          $('.logged-in:hidden', container).show();
        }
        if (state.location) {
          if (!MOBILE) {
            $('.user-location:hidden', container).show();
          }
          $('.user-location a', container).text(state.location.name);
        } else {
          if (!MOBILE) {
            $('.user-location:visible', container).hide();
          }
        }
        if (state.user.anonymous) {
          $('.user-name a', container).text('Settings');
          if (!MOBILE) {
            $('.user-un-anonymous', container).show();
            $('.signout', container).hide();
          }
        } else {
          $('.user-name a', container).text(state.user.name);
          if (!MOBILE) {
            $('.user-un-anonymous', container).hide();
            $('.signout', container).show();
          }
        }
        $('.user-miles a', container)
          .text(Utils.formatMiles(state.user.miles_total, true));
        $('.user-coins a', container)
          .text(Utils.formatCost(state.user.coins_total, true));
        if (state.user.awards.count) {
          $('.user-awards a', container)
          .text('Awards (' + state.user.awards.count + ')');
        } else {
          $('.user-awards a', container).text('Awards');
        }
        if (state.user.awards.unread) {
          $('.user-awards a', container)
            .attr('title', state.user.awards.unread + ' unread')
              .addClass('unread');
          $('.user-awards', container).show();
        } else {
          if (state.user.awards.count == 1) {
            $('.user-awards a', container)
              .attr('title', '1 award');
          } else {
            $('.user-awards a', container)
              .attr('title', state.user.awards.count + ' awards');
          }
          $('.user-awards a.unread', container).removeClass('unread');
        }
        if (!MOBILE) {
          if (state.user.admin_access) {
            $('.admin', container).show();
          } else {
            $('.admin', container).hide();
          }
        }
      } else {
        if (!MOBILE) {
          $('.logged-in:visible', container).hide();
          $('.user-login:hidden', container).show();
        }
      }
    },
    show_coin_change: function(delta, animated, callback) {
      _show_change(delta, animated, '.user-coins', 'coins', callback);
    },
    show_miles_change: function(delta, animated, callback) {
      _show_change(delta, animated, '.user-miles', 'miles', callback);
    },
    redirect_login: function() {
      Loader.load_hash('#signin');
    },
    redirect_to_city: function() {
      Loader.load_hash('#city');
    }
  };
})();

var Utils = (function() {
  var _loading_timer;

  function isInt(x) {
    var y = parseInt(x, 10);
    if (isNaN(y)) return false;
    return x == y && x.toString() == y.toString();
  }

  function tsep(n,swap) {
    var ts=",", ds="."; // thousands and decimal separators
    if (swap) { ts=","; ts="."; } // swap if requested

    var ns = String(n),ps=ns,ss=""; // numString, prefixString, suffixString
    var i = ns.indexOf(".");
    if (i!=-1) { // if ".", then split:
      ps = ns.substring(0,i);
      ss = ds+ns.substring(i+1);
    }
    return ps.replace(/(\d)(?=(\d{3})+([.]|$))/g,"$1"+ts)+ss;
  }

  function dotdotdot_loading() {
    $('.loading-overlay:visible')
      .text($('.loading-overlay:visible').text() + '.');
  }

  return {
     loading_overlay_reset: function() {
       $('.overlay:visible .loading-overlay').show();
       _loading_timer = setInterval(function() {
         dotdotdot_loading();
       }, 1000);

     },
    loading_overlay_stop: function() {
      $('.loading-overlay:visible')
        .text($('.loading-overlay:visible').text().replace(/[\.]+$/, '...'));
      $('.overlay:visible .loading-overlay').hide();
      clearInterval(_loading_timer);
    },
    loading_overlay_remove: function() {
      clearInterval(_loading_timer);
      $('.loading-overlay:visible').remove();
    },
    general_error: function(message, reload_tip) {
      message = 'Error!\n' + message;
      if (!reload_tip) {
        reload_tip = "Try reloading to arrive in your current city";
      }
      message += '\n' + reload_tip;
      alert(message);  // XXX which this was something more cool
    },
    formatCost: function(v, include_suffix) {
       if (include_suffix) {
         if (v == 1) return v + ' coin';
         return tsep(v) + ' coins';
       }
       return tsep(v);
     },
    formatMiles: function(v, include_suffix) {
      v = parseInt(v, 10);
      if (include_suffix) {
        if (v == 1) return v + ' mile';
        return tsep(v) + ' miles';
      }
      return tsep(v);
    },
    formatPoints: function(v, include_suffix) {
      if (include_suffix) {
        var suffix = 'points';
        if (v == 1) suffix = 'point';
        if (!isInt(v)) v = v.toFixed(1);
        return v + ' ' + suffix;
      }
      if (!isInt(v)) v = v.toFixed(1);
      return v;
    },
    preload_image: function(url, callback) {
      var i = $('<img>');
      if (callback) {
        i.ready(callback);
      }
      i.attr('src', url);
    },
    preload_images: function(urls, synchronous) {
      if (synchronous) {
        var url = urls.shift();
        if (url) {
          Utils.preload_image(url, function() {
            Utils.preload_images(urls);
          });
        }
      } else {
        $.each(urls, function(i, url) {
          Utils.preload_image(url);
        });
      }
    },
    update_title: function (title) {
      if (!title) {
        if ($('h1:visible').size()) {
          title = $('h1:visible').text();
        } else if ($('h2:visible').size()) {
          title = $('h2:visible').text();
        }
      }
      if (title) {
        document.title = title;
      }
    }
  };
})();

var ErrorCatcher = (function() {
  var _prev_onerror;

  function show_onerror() {
    $('#onerror').show();

    $('a', '#onerror')
      .attr('href', window.location.href)
        .click(function() {
          window.location.reload(true);
          return false;
        });
  }

  function post_error(data) {
    $.post('/errors/', data);
  }

  return {
     set_prev_onerror: function(func) {
       _prev_onerror = func;
     },
     trigger: function(message, file, line) {
       if (_prev_onerror) {
         return _prev_onerror(message, file, line);
       }
       //L(message, file, line);
       if (line === 0 && (
           message == "TypeError: 'null' is not an object" ||
           message == "TypeError: 'undefined' is not an object")) {
         console.warn('Swallowing error', message);
         // some strange Safari errors I'm getting that always gets in the way
         return;
       }
       if (message && message === 'Script error.' &&
           file && file.search(/devtools/) > -1) {
         // some sort of devtools error
         return;
       }

       show_onerror();
       var data = {};
       if (message) data.message = message;
       if (file) data.file = file;
       if (line) data.line = line;
       data.url = window.location.href;
       data.useragent = navigator.userAgent;
       try {
         var trace = printStackTrace();
         data.trace = trace.join('\n');
       } catch(e) {
         if (typeof printStackTrace !== 'undefined') {
           console.log('Error message:');
           console.log(message);
         }
       }
       post_error(data);
       return !STATE.debug;
     }
  };
})();


// some things can't wait for the map to load
$(function() {
  // here 'STATE' is a inline defined variable.
  // This makes it so that the usernav can be populate quickly on
  // loading time without having to do a JSON pull first
  State.render(STATE);
});


mapInitialized(function(map) {

  window.onerror = ErrorCatcher.trigger;

  $('a.overlay-changer').click(function() {
    return Loader.load_hash($(this).attr('href'));
  });

  if (window.location.hash) {
    Loader.load_hash(window.location.hash);
  } else {
    Loader.load_hash('#welcome');
  }

});
