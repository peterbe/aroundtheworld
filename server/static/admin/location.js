function _look_up() {
  var data = {
     city: $('#city').val(),
    country: $('#country').val(),
    locality: $('#locality').val()
  };
  $.getJSON('/admin/geocode.json', data, function(response) {
    $('#search-results:hidden').show();
    $('ul li', '#search-results').remove();
    $.each(response.results, function(i, item) {
      $('<a href="#"></a>')
        .text(item.place)
          .attr('title', 'Click to enter into form')
          .click(function() {
            $('#lat').val(item.lat);
            $('#lng').val(item.lng);
            return false;
          }).appendTo($('<li>')
                      .appendTo($('#search-results ul')));
    });
  });
}

$(function() {
  function _look_up_wrapper() {
    if ($('#city').val() && $('#country').val()) {
      _look_up();
    }
  }
  $('#city').change(_look_up_wrapper);
  $('#country').change(_look_up_wrapper);
  $('#locality').change(_look_up_wrapper);

});
