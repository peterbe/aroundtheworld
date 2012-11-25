var News = (function() {
  var container = $('#news');
  var URL = '/news.json';
  var _once = false;

  function _item_clicked() {
    load_item($(this).parents('div').data('id'));
    return true;
  }

  function load_item(id) {
    $.getJSON(URL, {id: id}, function(response) {
      var item = response.newsitem;
      var c = $('.item', container);
      $('h3', c).text(item.title);
      $('.body', c).html(item.body_html);
      $('.metadata strong', c).text(item.age + ' ago');
      $('.item-' + item.id).removeClass('unread').addClass('read');
      $('.items', container).hide();
      c.hide().fadeIn(300);
    });
  }

  function load() {
    $.getJSON(URL, function(response) {
      var c = $('.items', container);
      $('div', c).remove();
      $.each(response.newsitems, function(i, item) {
        var d = $('<div>')
          .data('id', item.id)
            .addClass('item-' + item.id);

        if (item.read) {
          d.addClass('read');
        } else {
          d.addClass('unread');
        }
        $('<h4>')
          .append($('<a href="#news,' + item.id + '"></a>')
                  .text(item.title)
                  .click(_item_clicked)
                 )
            .appendTo(d);
        var body = item.body;
        if (body.length > 50) {
          body = body.substring(0, 50) + '...';
        }
        $('<p>')
          .addClass('body')
          .text(body)
          .appendTo(d);

        $('<p>')
          .addClass('metadata')
          .text('Posted ' + item.age + ' ago')
          .appendTo(d);

        d.appendTo(c);
      });
      c.show();
      if (response.newsitems.length) {
        $('.no-news', container).hide();
      } else {
        $('.no-news', container).show();
      }
    });
  }
  function setup_once() {
    $('.item a.closer', container).click(function() {
      $('.item', container).hide();
      $('.items', container).fadeIn(300);
      return true;
    });
  }

  return {
     setup: function(id) {
       if (!_once) {
         setup_once();
         _once = true;
       }
       load();
       if (id) {
         load_item(id);
       }
     },
    teardown: function() {
    }
  };
})();

Plugins.start('news', function(id) {
  News.setup(id);
});


Plugins.stop('news', function() {
  News.teardown();
});
