var Lookup = (function() {
  var _location_searches = [];
  var _user_searches = [];

  return {
     search_location: function() {
       var location = $('#location').val();
       if ($.inArray(location, _location_searches) > -1) {
         return;
       }
       var data = {
          location: location
       };
       _location_searches.push(location);
       $.getJSON('/admin/findlocation.json', data, function(response) {
         $('#search-results:hidden').show().detach().insertBefore($('#location').parents('div.clearfix'));

         $('ul li', '#search-results').remove();
         $.each(response.results, function(i, item) {
           $('<a href="#"></a>')
             .text(item)
               .attr('title', 'Click to enter into form')
                 .click(function() {
                   $('#location').val(item);
                   $('#search-results').hide();
                   return false;
                 }).appendTo($('<li>')
                             .appendTo($('#search-results ul')));
         });
       });
     },
    search_user: function() {
       var user = $('#user').val();
       if ($.inArray(user, _user_searches) > -1) {
         return;
       }
       var data = {
          user: user
       };
       _user_searches.push(location);
       $.getJSON('/admin/finduser.json', data, function(response) {
         $('#search-results:hidden').show().detach().insertBefore($('#user').parents('div.clearfix'));

         $('ul li', '#search-results').remove();
         $.each(response.results, function(i, item) {
           $('<a href="#"></a>')
             .text(item)
               .attr('title', 'Click to enter into form')
                 .click(function() {
                   $('#user').val(item);
                   $('#search-results').hide();
                   return false;
                 }).appendTo($('<li>')
                             .appendTo($('#search-results ul')));
         });
       });
     }
  }
})();

$(function() {

  $('#location').on('keyup', function() {
    if ($(this).val().length >= 2) {
      Lookup.search_location();
    }
  });

  $('#user').on('keyup', function() {
    if ($(this).val().length >= 2) {
      Lookup.search_user();
    }
  });

});
