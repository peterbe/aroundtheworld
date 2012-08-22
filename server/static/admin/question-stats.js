$(function() {
  function change_points_value(delta, parent) {
    var id = parent.data('id');
    $('a,span', parent).fadeTo(100, 0.1);
    var url = '/admin/questions/' + id + '/change-points-value.json';
    $.post(url, {delta: delta}, function(response) {
      $('span', parent).text(response.points_value);
      $('a,span', parent).fadeTo(100, 1.0);
    });
  }
  $('a.increase-points-value').click(function() {
    change_points_value(1, $(this).parent('td'));
    return false;
  });
  $('a.decrease-points-value').click(function() {
    change_points_value(-1, $(this).parent('td'));
    return false;
  });
});
