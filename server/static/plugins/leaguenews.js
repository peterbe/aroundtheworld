var LeagueNews = (function() {
  var container = $('#leaguenews');
  var URL = '/leaguenews.json';
  var _once = false;
  var LIMIT = 10;
  var last = null;
  var latest = null;

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

  function load(since) {
    since = since || null;
    $.getJSON(URL, {limit: LIMIT, since: since}, function(response) {
      var c = $('.items', container);
      $('div', c).remove();
      $.each(response.news.items, function(i, item) {
        $('<div>').html(item).appendTo(c);
      });
      c.show();
      $('.load-more', container).hide();
      $('.rewind', container).hide();

      if (response.news.items.length) {
        $('.no-news', container).hide();
        if (response.news.items.length == LIMIT) {
          if (response.news.last != last) {
            $('.load-more', container).show();
          } else if (since) {
            $('.rewind', container).show();
          }
        }
      } else {
        $('.no-news', container).show();
      }

      if (response.news.last) {
        last = response.news.last;
      }
      if (response.news.latest) {
        latest = response.news.latest;
      }

    });
  }
  function setup_once() {
    $('.item a.closer', container).click(function() {
      $('.item', container).hide();
      $('.items', container).fadeIn(300);
      return true;
    });
    $('.load-more a', container).click(function() {
      load(last);
      return false;
    });
    $('.rewind a', container).click(function() {
      load(null);
      return false;
    });
  }

  return {
     setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
       load();
     },
    teardown: function() {
    }
  };
})();

Plugins.start('leaguenews', function() {
  LeagueNews.setup();
});


Plugins.stop('leaguenews', function() {
  LeagueNews.teardown();
});
