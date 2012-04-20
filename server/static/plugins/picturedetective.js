var PictureDetective = (function() {
  var URL = '/picturedetective.json';
  var container = $('#picturedetective');
  var _can_begin = false;
  var _left_to_load;
  var _total_to_load;
  var _indexes = [];
  var _on_index;
  return {
     begin_load: function() {
       $('.pre-finish', container).show();
       $('.intro', container).hide();
       $('.loading', container).show();

       _indexes = [];
       $.getJSON(URL, function(response) {
         _left_to_load = response.pictures.length;
         _total_to_load = response.pictures.length;
         $('.question .questiontext', container).text(response.question);
         var _was_first = true;
         var _index;
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
      $('.loading', container).hide();
      $('.question', container).fadeIn(700);
      $('.timeleft', container).text(_indexes.length - 1);
      _on_index = _indexes.length - 1;
      L($('img.alternative'));
      //_next_picture_id = _indexes[_indexes.length - 1];
      $('img.playbutton')
        .css('width', $('img.alternative').eq(0).css('width'))
          .on('click', function() {
            PictureDetective.tick();
          });

      // perhaps this can wait
      $('img.alternative:visible')
        .on('click', function() {
          PictureDetective.pause();
        });
    },
    tick: function() {
      $('input[name="answer"]', container).val('').focus();
      $('input[name="continue"]', container).hide();
      $('img.playbutton').hide();
      L("_on_index", _on_index);
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
    submit: function(timedout) {
      alert("work harder");
    },
    setup: function() {
       //_can_begin = false;
      $('img.alternative', container).remove();
      $('.begin a', container).off('click');
      $('img.playbutton').off('click');
      $('.question', container).hide();
      $('.intro', container).show();
      $('.pre-finish', container).hide();
      $('.begin a', container).click(function() {
        PictureDetective.begin_load();
        return false;
      });
      Utils.update_title();
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
