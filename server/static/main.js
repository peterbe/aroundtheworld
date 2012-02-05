var Loader = (function() {
  return {
     load_hash: function (hash, blank_location_hash) {

       // so that reloads works nicer
       if (hash == '#signout' || hash == '#welcome') blank_location_hash = true;

       if (blank_location_hash) {
         window.location.hash = '';
       } else if (hash !== window.location.hash) {
         window.location.hash = hash;
       }
       var arg = hash.split(',')[1] || null;
       hash = hash.split(',')[0];
       if ($(hash + '.overlay').size()) {
         $('.overlay:visible').hide();
         $(hash + '.overlay').show();
         Plugins.load(hash.substr(1, hash.length - 1), arg);
       } else if (hash == '#fly') {
         $('.overlay:visible').hide();
         Plugins.load('flying', arg);
       } else {
         L('ignoring: ' + hash); // xxx: console.warn(..) instead??
       }

       // when blanking the location hash, don't bubble
       if (blank_location_hash) return false;

       return true;
    }

  }
})();

var State = (function() {

  function _show_change(delta, animated, selector, suffix) {
    var e = $('#usernav ' + selector + ' a');
    var b = parseInt(e.text().replace(/[^\d]/g, ''));
    if (animated) {
      e.fadeTo(400, 0.1, function() {
        e.text(Utils.formatCost(b + delta) + ' ' + suffix)
          .fadeTo(700, 1.0);
      });
    } else {
      e.text(Utils.formatCost(b + delta) + ' ' + suffix);
    }
  }

  function _render_state(state) {
    var container = $('#usernav');
    if (state.user) {
      $('.user-login:visible', container).hide();
      $('.logged-in:hidden', container).show();
      if (state.location) {
        $('.user-location:hidden', container).show();
        $('.user-location a', container).text(state.location.name);
      } else {
        $('.user-location:visible', container).hide();
      }
      $('.user-name a', container).text(state.user.name);
      $('.user-miles a', container)
        .text(Utils.formatMiles(state.user.miles_total, true));
      $('.user-coins a', container)
        .text(Utils.formatCost(state.user.coins_total, true));
      if (state.user.admin_access) {
        $('.admin', container).show();
      } else {
        $('.admin', container).hide();
      }
    } else {
      $('.logged-in:visible', container).hide();
      $('.user-login:hidden', container).show();
    }
  }

  return {
     update: function() {
       $.getJSON('/state.json', function(response) {
         STATE = response.state;
         _render_state(STATE);
       });
     },
    show_coin_change: function(delta, animated) {
      _show_change(delta, animated, '.user-coins', 'coins');
    },
    show_miles_change: function(delta, animated) {
      _show_change(delta, animated, '.user-miles', 'miles');
    },
    redirect_login: function() {
      Loader.load_hash('#login');
    }
  }
})();

var Utils = (function() {

  function isInt(x) {
    var y = parseInt(x);
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

  return {
     formatCost: function(v, include_suffix) {
       if (include_suffix) {
         if (v == 1) return v + ' coin';
         return tsep(v) + ' coins';
       }
       return tsep(v);
     },
    formatMiles: function(v, include_suffix) {
      v = parseInt(v);
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
    preload_image: function(url) {
      var i = document.createElement('img');
      i.src = url;
    }
  }
})();

mapInitialized(function(map) {

  $('a.overlay-changer').click(function() {
    return Loader.load_hash($(this).attr('href'));
  });

  if (window.location.hash) {
    Loader.load_hash(window.location.hash);
  } else {
    Loader.load_hash('#welcome');
  }

});
