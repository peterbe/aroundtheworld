var Feedback = (function() {
  var container = $('#feedback');
  return {
    setup: function() {
      $('button[type="reset"]', container).click(function() {
        Feedback.reset();
        return false;
      });

      $('form', container).submit(function() {
        var data = {
          what: $('#id_what').val(),
          comment: $.trim($('#id_comment').val())
        };
        if (!data.comment.length) {
          alert("Please write something first");
          return;
        }
        $.post('/feedback.json', data, function() {
          Feedback.reset();
          $('.alert:hidden', container).show();
          setTimeout(function() {
            $('.alert:visible', container).hide();
          }, 5 * 1000);
        });
        return false;
      });
      Utils.update_title();
   },
    reset: function() {
      $('textarea', container).val('');
      //$('button[type="reset"]', container).click();
    }
  };
})();

Plugins.start('feedback', function() {
  // called every time this plugin is loaded
  Feedback.setup();
});

Plugins.stop('feedback', function() {
  Feedback.reset();
});
