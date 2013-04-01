var Screenshots = (function() {
  var URL = '/screenshots.json';
  var container = $('#screenshots');
  var _once = false;
  var _loading = false;

  function _load_pictures(callback) {
    $.getJSON(URL, function(response) {
      var parent = $('#screenshot-carousel .carousel-inner', container);
      console.log('parent', parent.length);
      console.log('response', response);
      var no_pictures = response.pictures.length;
      $('div.item', parent).remove();
      $.each(response.pictures, function(i, each) {
        var item = $('<div>').addClass('item');
        $('<img>')
          .attr('src', this.src)
            .attr('alt', this.title)
              .appendTo(item);
        var index = '(' + (i + 1) + ' of ' + no_pictures + ') ';
        var caption = $('<div>')
          .addClass('carousel-caption')
            .append($('<h4>').text(index + this.title));
        if (this.description) {
          caption.append($('<p>').text(this.description));
        }
        caption.appendTo(item);
        if (!$('.active', parent).size()) {
          item.addClass('active');
        }
        item.appendTo(parent);
      });
      $('.carousel', container).carousel();
      callback();
    });
  }

  function setup_once() {
    _load_pictures(function() {
      $('.pictures', container).hide().fadeIn(300);
      console.log('post loaded');
    });
  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
     }
  };
})();

Plugins.start('screenshots', function() {
  Screenshots.setup();
});
