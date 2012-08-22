var MOBILE = true;

var Mobile = (function() {
  var usernav = $('#usernav');
  var _nav_expansion = true;
  return {
     expand_usernav: function() {
       $('li.user-miles,li.user-coins,li.user-name,li.feedback,li.exit-mobile,li.user-awards', usernav).show();
       $('.menu-toggle', usernav).text('Close');
       if (STATE.user.anonymous) {
         $('li.user-un-anonymous', usernav).show();
       } else {
         $('li.signout', usernav).show();
       }
     },
     collapse_usernav: function() {
       $('li.user-miles,li.user-coins,li.user-name,li.feedback,li.exit-mobile,li.user-awards', usernav).hide();
       $('.menu-toggle', usernav).text('Menu');
       if (STATE.user.anonymous) {
         $('li.user-un-anonymous', usernav).hide();
       } else {
         $('li.signout', usernav).hide();
       }
     },
     toggle_usernav: function() {
       if (_nav_expansion) {
         Mobile.expand_usernav();
         _nav_expansion = false;
       } else {
         Mobile.collapse_usernav();
         _nav_expansion = true;
       }
     },
     setup_usernav: function() {
       $('.city-prefix', usernav).text('');
       $('<a href="#">')
         .text('Menu')
         .click(function() {
           Mobile.toggle_usernav();
           return false;
           })
           .addClass('open-menu').addClass('menu-toggle')
             .prependTo(usernav);
       $('li.user-location').show();
       $('a', usernav).not('.menu-toggle').click(function() {
         _nav_expansion = true;
         Mobile.collapse_usernav();
       });
     },
    hack_external_links: function() {
      $('a.auth', '#login').each(function() {
        $(this).attr('href', $(this).attr('href') + '?next=/mobile/');
      });
    }
  };
})();


mapInitialized(function(map) {
  Mobile.setup_usernav();
  Mobile.hack_external_links();
});
