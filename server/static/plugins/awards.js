var Awards = (function() {
  var container = $('#awards');
  var URL = '/awards.json';
  var loaded = {};
  var thumbnail = $('img.thumbnail-template', container);
  var _once = false;

  function _display_award(award) {
    var c = $('.index-outer', container);
    loaded[award.id] = award;
    var d = $('<div>')
      .addClass('award')
        .addClass('type-' + award.type);
    function make_a(award_id) {
      return $('<a href="#awards,">')
        .attr('href', '#awards,' + award_id)
          .data('id', award_id).click(function() {
            Awards.load_award($(this).data('id'));
            //return false;
          });
    }
    var ta = make_a(award.id);
    thumbnail.clone().show().appendTo(ta);
    ta.appendTo(d);
    d.append(make_a(award.id).text(award.description).addClass('title'));
    if (!award.read) {
      d.append($('<span class="label label-success new-award">New!</span>')
                .data('id', award.id));
    }
    d.append($('<p>').text("Awarded to you on " + award.date));
    c.append(d);
  }

  function _display_modal_award(award) {
    var c = $('.wrapper', container);
    $.each(['title', 'type', 'description'], function(i, prefix) {
      $('.' + prefix, c).hide();
      if ($('.' + prefix + '-' + award.type, c).size()) {
        $('.' + prefix + '-' + award.type, c).show();
      } else {
        $('.' + prefix + '-generic', c).show();
      }
    });
    $('.category', c).text(award.category);
    $('.location', c).text(award.location);
    $('.name', c).text(award.name);
    $('.date', c).text(award.date);
    $('.signature', c).text(award.ambassador);
    Utils.update_title(award.description);
    if (award.long_description) {
      $('.long-description span', container).text(award.long_description);
      $('.long-description', container).show();
    } else {
      $('.long-description', container).hide();
    }
    if (STATE.user.anonymous) {
      $('.login-push', container).show();
    } else {
      $('.login-push', container).hide();
    }
  }

  function setup_once() {
    $('a.return', container).click(function() {
      $('.wrapper-outer', container).hide();
      $('.index-outer', container).show();
      Utils.update_title();
      if (location.hash != '#awards') {
        location.hash = '#awards';
      }
      return false;
    });
  }

  return {
     load: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
       Utils.update_title();
       var _has_preloaded = false;
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         $('.index-outer .award', container).remove();
         loaded = {};
         $.each(response.awards, function(i, award) {
           if (!award.read && !_has_preloaded) {
             sounds.preload('applause');
             _has_preloaded = true;
           }
           _display_award(award);
           $('.index-outer .explanation-' + award.type).addClass('done');
         });
         if (!response.awards.length) {
           $('.none', container).show();
         } else {
           $('.none', container).hide();
         }
       });
     },
    load_award: function(id, callback) {
      $.getJSON(URL, {id: id}, function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
        if (response.error == 'INVALIDAWARD') {
          alert('Error! Invalid award');
          return;
        }
        if (response.award.was_unread) {
          sounds.play('applause');
        }
        //loaded = {};
        _display_modal_award(response.award);
        $('.wrapper-outer', container).show();
        $('.index-outer', container).hide();

        $('.new-award', container).each(function() {
          if ($(this).data('id') == response.award.id) {
            $(this).remove();
          }
        });

        if (typeof Mousetrap !== 'undefined') {
          // not necessarily loaded in mobile
          Mousetrap.bind('esc', function() {
            $('.return:visible', container).click();
          });
        }
        State.update();
        if (callback) callback();
      });
    },
    teardown: function() {
      if (typeof Mousetrap !== 'undefined') {
        Mousetrap.reset();
      }
    }
  }
})();

Plugins.start('awards', function(id) {
  if (id) {
    Awards.load_award(id);
  }
  Awards.load();
});


Plugins.stop('awards', function() {
  Awards.teardown();
});
