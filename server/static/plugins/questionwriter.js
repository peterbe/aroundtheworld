var QuestionWriter = (function() {
  var container = $('#questionwriter');
  var URL = '/questionwriter.json';
  var CHECK_URL = '/questionwriter-check.json';
  var _filepicker_key = null;
  var _once = false;

  function reset_form() {
    $('input[name="text"]', container).val('');
    $('input[name="correct"]', container).val('');
    $.each($('input[name="alternatives"]', container), function() {
      $(this).val('');
    });
    $('input[name="file_url"]', container).val('');
    $('input[name="correct"]', container).val('');
    $('textarea[name="didyouknow"]', container).val('');

    var c = $('.pictureupload', container);
    $('.preview', c).hide();
    $('.file-url-check', c).hide();
    $('.file-url-error', c).hide();
    $('.buttons', c).hide();

    $('a.upload-big').show();
    $('a.upload-small').hide();

  }

  function complain(key, message) {
    var el = $('form [name="' + key + '"]', container);
    var p = el.parents('div.control-group');
    // clear any existing errors
    $('.help-inline-error', p).remove();
    p.addClass('error');
    $('<span>')
      .addClass('help-inline')
      .addClass('help-inline-error')
      .text(message)
      .appendTo(el.parents('div.controls'));
    el.on('keyup', function() {
      $(this).off('keyup');
      $(this).parents('div.control-group').removeClass('error');
      $('.help-inline-error', $(this).parents('div.controls')).remove();
    });
  }

  function setup_once() {

    $('button[type="reset"]', container).click(function() {
      reset_form();
      $('a[href="#tab-questions"]', container).click();
      return false;
    });

    $('form input', container).on('blur', function() {
      $(this).val($.trim($(this).val()));
    });

    $('form', container).submit(function() {

      var alternatives = [];
      $.each($('input[name="alternatives"]', container), function() {
        if ($.trim($(this).val()).length) {
          alternatives.push($(this).val());
        }
      });

      var data = {
         text: $('input[name="text"]', container).val(),
        correct: $('input[name="correct"]', container).val(),
        alternatives: alternatives.join('\n'),
        points_value: $('select[name="points_value"]', container).val(),
        category: $('select[name="category"]', container).val(),
        file_url: $('input[name="file_url"]', container).val(),
        didyouknow: $('textarea[name="didyouknow"]', container).val()

      };

        /*
        if (!data.text.length) {
          complain('text', 'Empty');
          return false;
        } else if (data.text.search(/\?$/) == -1) {
          complain('text', 'Must be a question');
          return false;
        }
         */

      $.post('/questionwriter.json', data, function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
        if (response.errors) {
          $.each(response.errors, function(key, message) {
            complain(key, message);
          });
        }
        if (response.question_id) {
          $('.alert-success', container).show();
          setTimeout(function() {
            $('.alert-success:visible', container).fadeOut(1000);
          }, 5 * 1000);
          QuestionWriter.reload_questions();
          reset_form();
        }
      });
      return false;
    });

    // picture upload actions
    $('button[name="confirm"]', container).click(function() {
      $('fieldset', container).css('opacity', '1.0');
      $('.pictureupload .buttons', container).hide();

    });

    // for the uploader
    $('.file-url-error', container).hide();
    $('.file-url-check', container).hide();

    // prepping picture upload
    $('a.upload', container).click(function() {
      if (!_filepicker_key) {
        alert("Error! Filepicker not initialized");
        return false;
      }
      filepicker.setKey(_filepicker_key);
      filepicker.getFile('image/*', function(url) {
        $('a.upload-big').hide();
        $('a.upload-small').show();

        $('.preview img', container).remove();
        $('.preview', container).show();
        $('.file-url-check', container).show();
        $('button[name="confirm"]', container).hide();
        $.post(CHECK_URL, {check_file_url: url}, function(response) {
          $('.file-url-check', container).hide();
          $('.file-url-error', container).hide();
          if (response.error) {
            $('.file-url-error', container)
              .text(response.error)
                .show();

          } else if (response.url) {
            $('button[name="confirm"]', container).show();
            $('input[name="file_url"]', container).val(response.url);

            $('<img>')
              .attr('src', response.static_url)
                .attr('width', '300')
                  .addClass('thumbnail')
                  .appendTo($('.preview', container))
                    .load(function() {
                      $('.preview .loading', container).hide();
                      $('.preview', container).show();
                      $('.pictureupload .buttons', container).show();
                      $('fieldset', container).css('opacity', '0.3');
                    });
          }
        });

      });
      return false;
    });

    // for going back
    $('div.question a.return', container).click(function() {
      $('div.question', container).hide();
      $('div.questions table', container).show();
    });

    $('ul.nav a', container).click(function() {
      var destination = $(this).attr('href');
      if (destination === '#tab-questions') {
        $('div.question:visible', container).hide();
        $('div.questions table', container).show();
      }
    });

    // the info box
    $('.alert-info button.close', container).click(function() {
      $('.alert-info', container).fadeOut(500);
      $('.info-toggle', container).fadeIn(300);
    });
    $('.info-toggle a', container).click(function() {
      $('.info-toggle', container).hide();
      $('.alert-info', container).fadeIn(300);
    });
  }

  return {
    setup: function() {
      if (!_once) {
        setup_once();
        _once = true;
      }
      // update title
      Utils.update_title();


      // init form
      $.getJSON(URL, function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

        if (!_filepicker_key) {
          _filepicker_key = response.filepicker_key;
        }

        var c = $('select[name="category"]', container);
        $('option', c).remove();
        $.each(response.categories, function() {
          $('<option>')
            .val(this.value)
              .text(this.label)
                .appendTo(c);
        });
        QuestionWriter.load_questions(response.questions, true);
      });
    },
    load_question: function(question_id) {
      if ($('div.question:hidden', container).size()) {
        $('a[href="#tab-questions"]', container).click();
      }
      $.getJSON(URL, {question_id: question_id}, function(response) {
        var c = $('div.question', container);
        $('img.thumbnail', c).remove();
        $('table', container).hide();
        c.show();
        $('h3', c).text(response.text);
        $('.correct', c).text(response.correct);
        $('.alternatives span', container).remove();
        $('.alternatives br', container).remove();
        $.each(response.alternatives, function(i, each) {
          $('<span>').text(each).appendTo($('.alternatives', c));
          $('<br>').text(each).appendTo($('.alternatives', c));
        });
        $('.category', c).text(response.category);
        $('.points-value', c).text(response.points_value);
        $('.status span', c).hide();

        if (response.published) {
          $('.status .published', c).show();
          $('.earned', c).text(response.earned);
        } else {
          $('.status .pending', c).show();
          $('.earned', c).text('--');
        }

        if (response.picture) {
         $('<img>')
           .attr('width', response.picture.width)
           .attr('height', response.picture.height)
           .attr('alt', response.text)
           .addClass('thumbnail')
           .appendTo($('.thumbnail-wrapper', c))
           .attr('src', response.picture.url);
        }
      });
    },
    reload_questions: function() {
      $.getJSON(URL, function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
        QuestionWriter.load_questions(response.questions, true);
      });
    },
    load_questions: function(questions, clear) {
      $('.count', container).text(questions.length);
      if (!questions.length) {
        $('.questions .none', container).show();
        $('.questions table', container).hide();
      } else {
        $('.questions .none', container).hide();
        $('.questions table', container).show();
      }
      if (clear) {
        $('div.questions tbody tr', container).remove();
      }
      $.each(questions, function(i, question) {
        var c = $('<tr>');
        $('<a>')
          .on('click', function() {
            QuestionWriter.load_question(question.id);
          })
            .attr('href', '#questionwriter,' + question.id)
              .text(question.text)
                .appendTo($('<td>').appendTo(c));
        var status = 'pending review';
        var earned = '-';
        if (question.published) {
          status = 'published';
          earned = question.earned
        }
        $('<td>').text(question.category).appendTo(c);
        $('<td>').text(status).appendTo(c);
        $('<td>').text(earned).appendTo(c);
        c.appendTo($('div.questions tbody', container));
      });
    },
    reset: function() {
      $('form', container).show();
      $('.alert-success', container).hide();

      $('.preview', container).hide();
      $('.preview img', container).remove();
      $('.a.upload-big', container).show();
      $('.a.upload-small', container).hide();

      $('.alert-success', container).hide();
      $('.pictureupload .buttons', container).hide();
      $('fieldset', container).css('opacity', '1.0');
    }
  };
})();

Plugins.start('questionwriter', function(question_id) {
  // called every time this plugin is loaded
  QuestionWriter.setup();
  if (question_id) {
    QuestionWriter.load_question(question_id);
  }
});

Plugins.stop('questionwriter', function() {
  QuestionWriter.reset();
});
