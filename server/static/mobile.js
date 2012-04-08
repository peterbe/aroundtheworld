var Mobile = (function() {
  var usernav = $('#usernav');
  return {
     expand_usernav: function() {
       $('li.was-visible', usernav).removeClass('was-visible').show();
     },
     collapse_usernav: function() {
       $('li:visible', usernav)
         .not('.user-location')
           .addClass('was-visible').hide();
     },
     toggle_usernav: function() {
       if ($('li.was-visible').size()) {
         Mobile.expand_usernav();
         $('.menu-toggle', usernav).text('Close');
       } else {
         Mobile.collapse_usernav();
         $('.menu-toggle', usernav).text('Menu');
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
       //Mobile.collapse_usernav();
       $('li.user-location').show();
       $('li.user-miles,li.user-coins,li.user-name,li.feedback,li.user-un-anonymous').show();
     },
    hack_external_links: function() {
      $('a.auth', '#login').each(function() {
        $(this).attr('href', $(this).attr('href') + '?next=/mobile/');
      });
    }
  }
})();


mapInitialized(function(map) {
  Mobile.setup_usernav();
  Mobile.hack_external_links();
});
