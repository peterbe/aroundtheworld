var City = (function() {
  var URL = '/city.json';
  var AIRPORT_URL = '/airport.json';
  var container = $('#city');
  var _message_form_setup = false;

  function _load_jobs(callback) {
    $.getJSON(URL, {get: 'jobs'}, function(response) {
      $('.day-number', container).text(response.day_number);
      $('ul.jobs li', container).remove();
      var c = $('ul.jobs', container);
      $.each(response.jobs, function(i, each) {
        var hash = '#' + each.type;
        if (each.category) {
          hash += ',' + each.category.replace(' ','+');
        }
        var li = $('<li>')
        $('<a>')
          .attr('href', hash)
            .text(each.description)
              .click(function() {
                Loader.load_hash($(this).attr('href'));
                return true;
              }).appendTo($('<p>').appendTo(li));
        if (each.experience) {
          $('<p>')
            .addClass('experience')
              .text(each.experience)
                .appendTo(li);
        }
        li.appendTo(c)
      });
      callback();
    });
  }

  function _load_pictures(callback) {
    $.getJSON(URL, {get: 'pictures'}, function(response) {
      var parent = $('#picture-carousel .carousel-inner');
      var no_pictures = response.pictures.length;
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
        if (this.copyright || this.copyright_url) {
          var copyright_text;
          if (this.copyright) {
            copyright_text = 'Copyright: ' + this.copyright;
          } else {
            copyright_text = 'Copyright';
          }
          if (this.copyright_url) {
            caption.append($('<p>')
                           .addClass('copyright')
                           .append($('<a>')
                                   .attr('href', this.copyright_url)
                                   .text(copyright_text)
                                   .click(function() {
                                     window.open($(this).attr('href'));
                                     return false;
                                   })
                                   )
                          );
          } else {
            caption.append($('<p>')
                           .addClass('copyright')
                           .text(copyright_text)
                          );
          }
        }
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

  function _load_embassy(callback) {
    $.getJSON(URL, {get: 'ambassadors'}, function(response) {
      if (response.ambassadors) {
        $('.embassy .none:visible', container).hide();
        $('.embassy .html-container', container).html(response.ambassadors);
      } else {
        $('.embassy .none:hidden', container).show();
      }
      callback();
    });
  }

  function _load_intro(callback) {
    $.getJSON(URL, {get: 'intro'}, function(response) {
      if (response.intro) {
        $('.intro .none:visible', container).hide();
        $('.intro .html-container', container).html(response.intro);
      } else {
        $('.intro .none:hidden', container).show();
      }
      callback();
    });
  }

  function _load_messages(callback) {
    $.getJSON(URL, {get: 'messages'}, function(response) {
      $('.messages-outer .message', container).remove();
      _append_messages(response.messages);
    });
    if (STATE.user.anonymous) {
      $('form.post-message:visible', container).hide();
      $('form.cant-post-message:hidden', container).show();
    } else {
      $('form.post-message:hidden', container).show();
      $('form.cant-post-message:visible', container).hide();
    }
    callback();
  }
  function _append_messages(messages) {
    $.each(messages, function(i, each) {
      var c = $('<blockquote>').appendTo($('<div>').addClass('message'));
      var html = '<b>' + this.username + '</b>';
      html += ' (' + Utils.formatMiles(this.miles, true);
      html += ' currently in ' + this.current_location + ')';
      html += ' ' + this.time_ago + ' ago';
      $('<p>')
        .text(this.message)
          .appendTo(c);
      $('<small>')
        .html(html)
          .appendTo(c);
      c.appendTo($('.messages-outer', container));
    });
  }

  return {
     load: function(page) {
       Utils.loading_overlay_reset();
       $('.section:visible', container).hide();
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         Utils.loading_overlay_stop();
         if (response.state) {
           STATE = response.state;
         }
         $('h2 strong', container).text(response.name);
         if (map && map.getZoom() < 15) {
           var p = new google.maps.LatLng(response.lat, response.lng);
           if (p != map.getCenter()) {
             map.setCenter(p);
           }
           map.setZoom(15);
         }
         if (response.name) {
           $('.location-name', container).text(response.name);
         }
         if (response.count_pictures) {
           $('.pictures-link', container).show();
         } else {
           $('.pictures-link', container).hide();
         }
         if (page == 'embassy') {
           _load_embassy(function() {
             $('.embassy .none', container).hide();
             $('.embassy', container).show();
             Utils.update_title();
           });
         } else if (page == 'intro') {
           _load_intro(function() {
             $('.intro .none', container).hide();
             $('.intro', container).show();
             Utils.update_title();
           });
         } else if (page == 'jobs') {
           _load_jobs(function() {
             $('.jobs', container).show();
             Utils.update_title();
           });
         } else if (page == 'pictures') {
           _load_pictures(function() {
             //$('.pictures .none', container).hide();
             $('.pictures', container).show();
             Utils.update_title();
           });
         } else if (page == 'messages') {
           _load_messages(function() {
             $('.messages', container).show();
             Utils.update_title();
           });
         } else {
           if (STATE.location.nomansland) {
             $('.tutorial', container).show();
             $.getJSON(AIRPORT_URL, {only_affordable: true}, function(response) {
               if (!response.destinations.length) return;

               $('.tutorial .start-jobs', container).css('opacity', 0.3);
               $('.tutorial .start-airport', container).fadeIn(500);
               var c = $('.start-airport ul', container);
               $('li', c).remove();
               $.each(response.destinations, function(i, each) {
                 $('<li>')
                   .append($('<strong>').text(each.name))
                     .append($('<span>').text(Utils.formatCost(each.cost, true)))
                       .appendTo(c);
               });
             });
           } else {
             $('.home', container).show();
             // introduction?
             if (response.has_introduction) {
               $('li.intro-link', container).show();
             } else {
               $('li.intro-link', container).hide();
             }
             // ambassadors?
             if (response.has_ambassadors) {
               $('li.ambassadors-link', container).show();
             } else {
               $('li.ambassadors-link', container).hide();
             }
           }
           Utils.update_title();
         }
         //State.update();
       });
     },
    setup_message_post: function() {
      if (STATE.user && STATE.user.anonymous) {
        $('form.message-teaser', container).hide();
      } else {
        $('form.message-teaser:hidden', container).show();
      }

      if (_message_form_setup) return;
      $('.messages form', container).submit(function() {
        $('textarea', this).val($.trim($('textarea', this).val()));
        var message = $('textarea', this).val();
        if (message.length) {
          var self = this;
          $.post(URL, {message: message}, function(response) {
            $('textarea', self).val('');
            _append_messages(response.messages);
          });
        }
        return false;
      });
      $('input[name="teaser"]', container).on('focus', function() {
        window.location.hash = '#city,messages';
        City.load('messages');
        setTimeout(function() {
          $('.messages textarea', container).focus();
        }, 500);
      });
      _message_form_setup = true;
    },
    teardown: function() {
      $('.pictures-link', container).hide();
    }
  };
})();

Plugins.start('city', function(page, callback) {
  City.setup_message_post();
  City.load(page);
});


Plugins.stop('city', function() {
  City.teardown();
});
