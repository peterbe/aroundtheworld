var PictureDetective = (function() {
  var URL = '/picturedetective.json';
  var container = $('#picturedetective');
  var _can_begin = false;
  var _left_to_load;
  var _total_to_load;
  var _indexes = [];
  var _on_index;
  var _timer;
  var _pause_timer;
  var _submitted = false;
  var _once = false;

  function setup_once() {
    // set up the form submission
    $('form', container).on('submit', function() {
      clearTimeout(_timer);
      clearTimeout(_pause_timer);  // paranoia
      var answer = $.trim($('input[name="answer"]', container).val());
      if (answer.length) {
        PictureDetective.submit(false, answer);
      } else {
        if (_on_index) {
          PictureDetective.carryon();
        } else {
          PictureDetective.submit(true);
        }
      }
      return false;
    });

    $('.begin a', container).click(function() {
      PictureDetective.begin_load();
      return false;
    });

    $('input[name="continue"]', container).on('click', function() {
      PictureDetective.carryon();
    });

  }

  return {
     begin_load: function() {
       $('.pre-finish', container).show();
       $('.intro', container).hide();
       $('.loading', container).show();

       _indexes = [];
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         if (response.error == 'NOQUESTIONS') {
           alert("Error. No more picture detective questions");
           return State.redirect_to_city();
         }
         _left_to_load = response.pictures.length;
         _total_to_load = response.pictures.length;
         $('.question .questiontext', container).text(response.question);
         var _was_first = true;
         var _index;

         // reset bar
         $('.bar', container).css('width', '0%');

         $.each(response.pictures, function(i) {
           _index = 'picture-index-' + i;
           _indexes.push(_index);

           var image = $('<img>')
             .addClass('thumbnail').addClass('alternative')
               .attr('id', _index)
                 .hide()
                   .attr('width', this.width)
                     .attr('height', this.height)
                       .attr('alt', response.question)
                         .load(function() {
                           _left_to_load--;
                           if (_left_to_load <= 0) {
                             //_can_begin = true;
                             PictureDetective.begin();
                           } else {
                             // update the progress bar
                             var p = parseInt(100 * (1 - _left_to_load / _total_to_load));
                             $('.bar', container)
                               .css('width', p + '%');
                           }
                         }).attr('src', this.src);
           $('.pictures', container).append(image);
         });
       });
     },
    begin: function() {
      $('.inpause', container).hide();
      $('.incorrect', container).hide();
      $('.loading', container).hide();
      $('.question', container).fadeIn(700);
      $('.timeleft', container).text(_indexes.length - 1);
      _on_index = _indexes.length - 1;
      //_next_picture_id = _indexes[_indexes.length - 1];
      $('input[name="answer"]', container).val('');
      $('img.playbutton')
        .css('width', $('img.alternative').eq(0).css('width'))
          .on('click', function() {
            PictureDetective.tick();
          });

      $('input[name="answer"]', container).on('keyup', function() {
        if ($(this).val().length) {
          PictureDetective.pause();
        }
      });

      // perhaps this can wait
      $('img.alternative')
        .on('click', function() {
          PictureDetective.pause();
          $('input[name="answer"]', container).focus();
        });
    },
    pause: function() {
      if (_on_index <= 0) {
        PictureDetective.submit(true);
      }
      $('input[name="answer"]', container).off('keyup').on('keyup', function() {
        clearTimeout(_pause_timer);
        _pause_timer = setTimeout(function() {
          PictureDetective.carryon();
        }, 15 * 1000);
      });

      clearTimeout(_timer);
      $('img.playbutton', container).show();
      $('img.alternative', container).hide();
      $('.inpause', container).show();
      $('input[name="submit"]', container).show();
      $('input[name="continue"]', container).show();

    },
    carryon: function() {
      _on_index--;
      $('input[name="submit"]', container).hide();
      $('.inpause', container).hide();
      $('.incorrect', container).hide();
      PictureDetective.tick();
    },
    tick: function() {
      if (_submitted) return;
      $('input[name="answer"]', container).off('keyup').on('keyup', function() {
        if ($(this).val().length) {
          PictureDetective.pause();
        }
      });
      $('input[name="answer"]', container).val('').focus();
      $('input[name="continue"]', container).hide();
      $('img.playbutton', container).hide();
      $('.timeleft', container).text(_on_index);
      $('img.alternative:visible').hide();
      $('#' + _indexes[_on_index]).show();
      _timer = setTimeout(function() {
        if (_on_index > 0) {
          _on_index--;
          PictureDetective.tick();
        } else {
          PictureDetective.submit(true);
        }
      }, 1000);
    },
    submit: function(timedout, answer) {
      if (_submitted) return;
      _submitted = true;
      clearTimeout(_timer);
      clearTimeout(_pause_timer);
      var data = {
         answer: answer,
        timedout: timedout,
        seconds_left: _on_index
      };
      $.post(URL, data, function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
        if (response.incorrect) {
          _submitted = false;
          $('.inpause', container).hide();
          $('.incorrect', container).show();
          setTimeout(function() {
            PictureDetective.carryon();
          }, 3 * 1000);
        } else {
          PictureDetective.finish(response);
        }
      });
    },
    finish: function(result) {
      $('.question', container).hide();
      var c;
      if (result.points) {
        c = $('.finish-success', container);
        $('.total-points', c).text(Utils.formatPoints(result.points, true));
        $('.coins', c).text(Utils.formatCost(result.coins, true));
        State.show_coin_change(result.coins, true);
        State.update();

      } else {
        c = $('.finish-timedout', container);
        $('.correct-answer', c).text(result.correct_answer);
      }
      if (result.left) {
        $('a.start-over .left', c).text(result.left);
        $('a.start-over', c).show();
      } else {
        $('a.start-over', c).hide();
      }
      //c.show();
      c.fadeIn(700);
      if (result.didyouknow) {
        $('.didyouknow', c).html(result.didyouknow);
        $('.didyouknow', c).show();
      } else {
        $('.didyouknow', c).hide();
      }

    },
    setup: function() {
      if (!_once) {
        setup_once();
        _once = true;
      }
      _submitted = false;
      _submitted = false;
      _indexes = [];
      _can_begin = false;
      $('img.alternative', container).remove();
      $('img.playbutton').off('click');
      $('.question', container).hide();
      $('.intro', container).show();
      $('.pre-finish', container).hide();
      Utils.update_title();
    },
    teardown: function() {
      $('.finish:visible', container).hide();
      clearTimeout(_timer);
      clearTimeout(_pause_timer);
    }
  }
})();

Plugins.start('picturedetective', function() {
  // called every time this plugin is loaded
  PictureDetective.setup();
});

Plugins.stop('picturedetective', function() {
  PictureDetective.teardown();
});
