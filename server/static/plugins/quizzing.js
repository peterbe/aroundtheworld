var Quiz = (function() {
  var URL = '/quizzing.json';
  var container = $('#quizzing');
  var countdown;
  var timer;
  return {
     answer: function (value) {
       Quiz.stop_timer();
       $('ul.question', container).css('opacity', 0.5);
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
             alert(response);
          }
       });
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
       delete timer;
       L('STOP TIMER!');
     },
     show_question: function(question) {
       $('p.question span', container).remove();
       $('ul.question li', container).remove();
       $('ul.question', container).css('opacity', 1.0);
       $('.pleasewait:visible', container).hide();
       $('input[name="id"]', container).val(question.id);
       $('<span>')
         .addClass('question')
           .html(question.text)
             .appendTo($('p.question', container));
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
     }
  }
})();

$.getJSON('/quizzing.json', function(response) {
  if (response.quiz_name) {
    Quiz.show_name(response.quiz_name);
  }
  if (response.question) {
    Quiz.show_question(response.question);
  }
});
