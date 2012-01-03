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
  _show_change = function(delta, animated, selector, suffix) {
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
  return {
     update: function() {
       $.getJSON('/state.json', function(response) {
         STATE = response.state;
         $('#usernav').load('/state.html');  // lazy! FIXME: make this all javascript template instead one day
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
     formatCost: function(v) {
       return tsep(v);
     },
    formatMiles: function(v) {
      return tsep(v);
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
