var Quiz = (function() {
  var URL = '/quizzing.json';
  var container = $('#quizzing');
  var countdown;
  var timer;
  var in_pause = false;
  var last_question = false;
  return {
     answer: function (value) {
       Quiz.stop_timer();
       $('.pleasewait', container).show();
       $.ajax({
          url: URL,
         type: 'POST',
         cache: false,
         data: {
            id: $('input[name="id"]', container).val(),
             answer: value
         },
         dataType: 'json',
         success: function (response) {
           $('.pleasewait:visible', container).hide();
           if (response.correct) {
             $('.correct', container).show('fast');
             if (response.points_value) {
               var v = parseInt($('.points-total', container).text());
               $('.points-total', container).text(v + response.points_value);
             }
           } else {
             if (response.correct_answer) {
               $('.correct-answer', container).text(response.correct_answer);
             }
             $('.wrong', container).show('fast');
           }
           Quiz.restart_timer(3);
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
        $('.next-timer', container).hide();
      }
      seconds = seconds || 4;  // 4 is the default
      Quiz.start_timer(seconds);
      in_pause = true;
    },
    start_timer: function(seconds) {
      countdown = seconds;
      $('.timer', container).text(countdown);
      $('.timer:hidden', container).show();
      timer = setTimeout(function() {
        Quiz.tick_timer();
      }, 1000);
    },
    tick_timer: function() {
       countdown--;
       $('.timer', container).text(countdown);
       if (countdown == 0) {
         Quiz.stop_timer(true);
       } else {
         timer = setTimeout(function() {
           Quiz.tick_timer();
         }, 1000);
       }

     },
     stop_timer: function(timedout) {
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
           $('.tooslow', container).show('fast');
           Quiz.restart_timer();
         }
       }


     },
     show_question: function(question) {
       $('p.question span', container).remove();
       $('ul.question li', container).remove();
       $('ul.question', container).css('opacity', 1.0);
       $('.pleasewait:visible', container).hide();
       $('input[name="id"]', container).val(question.id);

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
           .click(function () {
             Quiz.answer(each);
             return false;
           }).appendTo($('<li>')
                       .appendTo($('.alternatives', container)));
       });
       Quiz.start_timer(question.seconds);
     },
    show_name: function (name) {
       $('.quiz-name', container).text(name);
     },
    load_next: function() {
      $.getJSON('/quizzing.json', function(response) {
        if (response.quiz_name) {
          Quiz.show_name(response.quiz_name);
        }
        if (response.question) {
          Quiz.show_question(response.question);
        }
      });
    }
  }
})();

Quiz.load_next();  // kick it off
