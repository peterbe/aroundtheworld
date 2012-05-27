function L() {
  if (window.console && window.console.log)
    console.log.apply(console, arguments);
}

$(function() {
  $('.dropdown-toggle').dropdown();

  $('a.close').click(function() {
    $(this).parents('.alert').fadeOut(400);
    return false;
  });

  $('a.thumbnail-preview').click(function() {
    $('h3', '#picture-modal').text($(this).data('title'));
    $('img', '#picture-modal').attr('src', $(this).attr('href'));
    $('#picture-modal').modal('show');
    return false;
  });
  $('.modal a.close, .modal a.btn').click(function() {
    $('#picture-modal').modal('hide');
    return false;
  });

  $('a[rel="tooltip"]').tooltip();

  $('button[type="reset"]').click(function() {
    window.location = '..';
  });

  $('.error input', 'form').change(function() {
    $(this).parents('.error').removeClass('error');
  });

  var title = null;
  if ($('h1:visible').size()) {
    if ($('h1:visible').size() == 1) {
      title = $('h1:visible').text();
    }
  } else if ($('h2:visible').size()) {
    if ($('h2:visible').size() == 1) {
      title = $('h2:visible').text();
    }
  }
  if (title) {
    document.title = "Admin: " + title;
  }

  if ($('.next a').size()) {
    jwerty.key('→', function () {
      // xxx why doesn't $('.next a').click() work?!
      window.location.href = $('.next a').attr('href');
    });
  }

  if ($('.prev a').size()) {
    jwerty.key('←', function () {
      window.location.href = $('.prev a').attr('href');
    });
  }

});
