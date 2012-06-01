var Quiz = (function() {
  var URL = '/quizzing.json';
  var RATE_URL = '/questionrating.json';
  var AIRPORT_URL = '/airport.json';
  var container = $('#quizzing');
  var countdown;
  var timer;
  var in_pause = false;
  var last_question = false;
  var _category;
  //var _next_is_last = false;
  var _next_is_first = true;
  var t0, t1;
  var _once = false;
  var _has_mousedover_raty = false;
  var _seen_intros = [];

  function _dirname(src) {
    return src.split('/').slice(0, src.split('/').length - 1).join('/') + '/';
  }

  function _show_no_questions(total, number) {
    $('.no-questions', container).text(number + ' of ' + total);
  }

  function _load_next_question(category) {
    category = category || _category;
    _category = category;
    var data = {category: category};
    if (_next_is_first) {
      $('.pre-finish:hidden', container).show();
      $('.post-finish:visible', container).hide();
      data.start = true;
      _next_is_first = false;
    }
    $.getJSON(URL, data, function(response) {
      if (response.error == 'NOTLOGGEDIN') return State.redirect_login();

      if (response.quiz_name) {
        Quiz.show_name(response.quiz_name);
      }
      last_question = response.no_questions.last;
      _show_no_questions(response.no_questions['total'],
                         response.no_questions['number']);
      if (response.question) {
        if (response.intro && $.inArray(category, _seen_intros) == -1) {
          _seen_intros.push(category);
          Quiz.show_intro(response.intro);
          $('div.intro', container).show();
          $('div.play', container).hide();
          $('.intro .begin a', container).click(function() {
            $('div.intro', container).hide();
            $('div.play', container).show();
            Quiz.start_timer(response.question.seconds);
            return false;
          });
          Quiz.show_question(response.question, false);
        } else {
          $('div.intro', container).hide();
          $('div.play', container).show();
          Quiz.show_question(response.question, true);
        }
      }
      Utils.update_title();
    });
  }

  function _finish() {
    $.post(URL, {finish: true}, function(response) {
      $('.play', container).hide();
      $('.results', container).show();
      $('.short-summary .total-points', container)
        .text(Utils.formatPoints(response.results.total_points, true));
      $('.short-summary .coins', container)
        .text(Utils.formatCost(response.results.coins, true));
      $('.pre-finish:visible', container).hide();
      $('.post-finish:hidden', container).show();
      State.show_coin_change(response.results.coins, true);
      State.update(function() {
        $('.short-summary .total-coins', container)
          .text(Utils.formatCost(STATE.user.coins_total, true));
        $('.short-summary .total-coins-outer', container).show();
      });

      var _total_points = 0;
      var tbody = $('.results tbody', container);
      $('tbody tr', container).remove();
      $('tfoot .points-total').text('');
      $.each(response.summary, function(i, each) {
        var tr = $('<tr>');
        if (each.correct) {
          tr.addClass('correct');
        } else {
          tr.addClass('wrong');
        }
        $('<td>')
          .text(i + 1)
            .appendTo(tr);
        $('<td>')
          .addClass('question')
          .text(each.question)
            .appendTo(tr);
        if (each.timedout) {
          $('<td>')
            .addClass('timedout')
              .text('timed out')
                .appendTo(tr);
        } else {
          $('<td>')
            .addClass('answer')
              .text(each.your_answer)
                .appendTo(tr);
        }
        $('<td>')
          .addClass('answer')
          .text(each.correct_answer)
            .appendTo(tr);
        if (each.timedout) {
          $('<td>')
            .addClass('timedout')
              .text('-')
                .appendTo(tr);
        } else {
          $('<td>')
            .addClass('number')
              .text(Utils.formatPoints(each.time))
                .appendTo(tr);
        }
        $('<td>')
          .addClass('number')
          .text(each.points)
            .appendTo(tr);

        _total_points += each.points;
        tr.appendTo(tbody);
      });

      $('tfoot .points-total-total', container)
        .text(Utils.formatPoints(_total_points));

      Utils.update_title();

      if (STATE.location.nomansland) {
        $.getJSON(AIRPORT_URL, {only_affordable: true}, function(response) {
          if (response.destinations.length) {
            $('.continue-tutorial-afford', container).fadeIn(400);
          } else {
            $('.continue-tutorial-cantafford', container).fadeIn(400);
          }
        });
      }

    });

  }

  function setup_once() {
    $('a.next-question', container).click(function() {
      Quiz.rush_next_question();
      return false;
    });

    // set up the necessary keyboard shortcuts
    if (typeof jwerty !== 'undefined') {
      jwerty.key('n', function() {
        $('a.next-question:visible', container).click();
      });
    }

    // no need to preload the images because they're already in the DOM
    var c = $('.rating-images', c);

    function _bname(cls) {
      var src = $('.' + cls, c).attr('src');
      return src.split('/')[src.split('/').length - 1];
    }

    $('.rate', container).raty({
       path: _dirname($('.face-a', c).attr('src')),
       iconRange: [
        { range: 2, on: _bname('face-a'), off: _bname('face-a-off')},
        { range: 3, on: _bname('face-b'), off: _bname('face-b-off')},
        { range: 4, on: _bname('face-c'), off: _bname('face-c-off')},
        { range: 5, on: _bname('face-d'), off: _bname('face-d-off')}
        ],
      mouseover : function(score, evt) {
        if (!_has_mousedover_raty) {
          Quiz.wait_longer(10);
          _has_mousedover_raty = true;
        }
      },
      click : function(score, evt) {
        $.post(RATE_URL, {score: score});
        $('a.next-question:visible', container).click();
        $('.rate:visible', container).raty('reload');
      }
    });

    $('.rating-images', container).hide();

  }

  return {
     setup: function(category) {
       if (!_once) {
         setup_once();
         _once = true;
       }
       Utils.update_title();
       $('.question-attention', container).hide();
       $('.continue-tutorial-cantafford', container).hide();
       $('.continue-tutorial-afford', container).hide();
       $('a.restart', container).attr('href', '#quizzing,' + category.replace(' ', '+'));
     },
     reset: function() {
       $('a.next-question', container)
         .text('Next question');
       if (timer) {
         clearTimeout(timer);
       }

       // reset the points-total
       $('.play .points-total', container).text('0');

     },
     answer: function (value) {
       t1 = new Date();
       Quiz.stop_timer();
       $('.pleasewait', container).show();
       $.ajax({
          url: URL,
         type: 'POST',
         cache: false,
         data: {
           answer: value,
             time: (t1 - t0) / 1000
         },
         dataType: 'json',
         success: function (response) {
           $('.pleasewait:visible', container).hide();
           $('.didyouknow', container).hide();
           if (response.correct) {
             $('.correct', container).show();
             if (response.points) {
               var v = parseInt($('.points-total', container).text());
               $('.points-total', container).text(v + response.points);
             }
           } else {
             if (response.correct_answer) {
               $('.correct-answer', container).text(response.correct_answer);
             }
             $('.wrong', container).show();//fadeIn(200);
           }
           if (response.didyouknow) {
             $('.didyouknow p', container).remove();
             $('.didyouknow', container)
               .append(response.didyouknow)
                 .fadeIn(300);
             Quiz.restart_timer(last_question && 3 || 10);
           } else {
             Quiz.restart_timer(3);
           }
           if (response.enable_rating) {
             $('.rate', container).show();
           } else {
             $('.rate', container).hide();
           }
         },
         error: function(xhr, status, error_thrown) {
           var msg = status;
           if (xhr.responseText)
             msg += ': ' + xhr.responseText;
           alert(msg);
         }
       });
     },
    restart_timer: function(seconds) {
      if (last_question) {
        $('a.next-question', container).text('Finish job');
        //$('.next-timer', container).hide();
      }
      seconds = seconds || 4;  // 4 is the default
      Quiz.start_timer(seconds);
      in_pause = true;
    },
    wait_longer: function(seconds) {
      countdown += seconds;
    },
    start_timer: function(seconds) {
      t0 = new Date();
      countdown = seconds;
      $('.timer', container).text(countdown);
      $('.timer-outer:hidden', container).show();
      timer = setTimeout(function() {
        Quiz.tick_timer();
      }, 1000);
    },
    rush_next_question: function() {
      countdown = 0;
      clearTimeout(timer);
      Quiz.stop_timer(true);
    },
    tick_timer: function() {
       countdown--;
       $('.timer', container).text(countdown);
       if (countdown <= 0) {
         Quiz.stop_timer(true);
       } else {
         timer = setTimeout(function() {
           Quiz.tick_timer();
         }, 1000);
       }

     },
     stop_timer: function(timedout) {
       _has_mousedover_raty = false;  // reset
       clearTimeout(timer);
       $('ul.question', container).css('opacity', 0.5);
       $('.alternatives', container).css('opacity', 0.5);
       $('.alternatives a', container)
         .off('click')
           .on('click', function() {
             return false;
           });
       if (in_pause) {
         in_pause = false;
         Quiz.load_next();
       } else {
         if (timedout) {
           $('.tooslow', container).fadeIn(200);
           if ($('.question:visible', container).size()) {
             Quiz.restart_timer();
           }
         }
       }
     },
     show_question: function(question, start_immediately) {
       if (question.picture) {
         Utils.preload_image(question.picture.url);
         $('.thumbnail-wrapper:hidden', container).show();
         $('.thumbnail-wrapper .loading:hidden', container).show();
         $('.thumbnail-wrapper img', container).remove();
       } else {
         $('.thumbnail-wrapper:visible', container).hide();
         $('.thumbnail-wrapper img', container).remove();
       }
       $('p.question span.question', container).remove();
       //$('ul.question li', container).remove();
       $('.alternatives li', container).remove();
       $('.alternatives', container).css('opacity', 1.0);
       $('.pleasewait:visible', container).hide();
       //$('input[name="id"]', container).val(question.id);
       $('.question-attention:visible', container).hide();
       $('<span>')
         .addClass('question')
           .html(question.text)
             .appendTo($('p.question', container));
       $('.alternatives li', container).remove();
       $('.alternatives', container).css('opacity', 1.0);
       $.each(question.alternatives, function(i, each) {
         $('<a href="#">')
           .html(each)
           .addClass('alt' + i)
           .attr('title', 'Press ' + (i + 1) + ' to select this answer')
           .click(function () {
             Quiz.answer(each);
             return false;
           }).appendTo($('<li>')
                       .appendTo($('.alternatives', container)));
         if (typeof jwerty !== 'undefined') {
           jwerty.key('' + (i + 1), function() {
             $('.alt' + i + ':visible', container).click();
           });
         }
       });
       if (question.picture) {
         $('<img>')
           .attr('width', question.picture.width)
           .attr('height', question.picture.height)
           .attr('alt', question.text)
           .addClass('thumbnail')
           .ready(function() {
             $('.thumbnail-wrapper .loading', container).hide();
             if (start_immediately) {
               Quiz.start_timer(question.seconds);
             }
           })
           .appendTo($('.thumbnail-wrapper', container))
           .attr('src', question.picture.url);
       } else {
         if (start_immediately) {
           Quiz.start_timer(question.seconds);
         }
       }
     },
    show_name: function (name) {
       $('.quiz-name', container).text(name);
     },
    show_intro: function(intro_html) {
      $('div.intro-text', container).html(intro_html);
    },
    load_next: function(category) {
      if (last_question) {
        _finish();
      } else {
        _load_next_question(category);
      }
    },
    teardown: function() {
      // reset everything!
      if (timer) clearTimeout(timer);
      last_question = false;
      in_pause = false;
      _next_is_first = true;
      $('.thumbnail-wrapper', container).hide();
      $('.thumbnail-wrapper img', container).remove();
      $('.results', container).hide();
      $.post(URL, {teardown: true});
    }
  }
})();

Plugins.start('quizzing', function(category) {
  // called every time this plugin is loaded
  Quiz.reset();
  Quiz.setup(category);
  Quiz.load_next(category);  // kick it off
});

Plugins.stop('quizzing', function() {
  Quiz.teardown();
});
