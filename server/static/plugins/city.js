var City = (function() {
  var URL = '/city.json';
  var AIRPORT_URL = '/airport.json';
  var container;
  var _message_form_setup = false;
  var _has_loaded_home = false;
  var _once = false;

  function setup_once() {
    container = $('#city');
    $('.affordable-tickets .show-more a', container).click(function() {
      $('.affordable-tickets .destination:hidden', container).fadeIn(200);
      $('.affordable-tickets .show-more').hide();
      return false;
    });
  }

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
        var li = $('<li>');
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
        li.appendTo(c);
      });
      callback();
    });
  }

  function _load_pictures(callback) {
    $.getJSON(URL, {get: 'pictures'}, function(response) {
      var parent = $('#picture-carousel .carousel-inner');
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
      var c = $('.intro', container);
      if (response.intro) {
        $('.none', c).hide();
        $('.html-container', c).html(response.intro).show();
      } else {
        $('.none', c).show();
        $('.html-container', c).hide();
      }
      callback();
    });
  }

  function _load_messages(callback) {
    $.getJSON(URL, {get: 'messages'}, function(response) {
      $('.messages-outer blockquote', container).remove();
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
       if (_has_loaded_home && !page) {
         Utils.loading_overlay_stop();
         $('.home', container).show();
       }
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         Utils.loading_overlay_stop();
         if (response.state) {
           STATE = response.state;
         }
         $('h2 strong', container).text(response.name);
         if (map && map.getZoom() < 15 && response.name.search('Tutorial') === -1) {
           var p = new google.maps.LatLng(response.lat, response.lng);
           if (p != map.getCenter()) {
             map.setCenter(p);
           }
           map.setZoom(15);
         }
         if (response.name) {
           $('.location-name', container).text(response.name);
         }

         $('.about-jobs', container).html(response.about_jobs);
         $('.about-flights', container).html(response.about_flights);
         $('.about-writings', container).html(response.about_writings);
         $('.about-question-writing', container).html(response.about_question_writing);
         $('.about-pictures', container).html(response.about_pictures);
         $('.about-banks', container).html(response.about_banks);
         $('.about-league', container).html(response.about_league);
         if (response.flag) {
           $('a.flag img', container).attr('src', response.flag);
           var loc = response.locality || response.country;
           $('a.flag', container)
             .attr('href', 'http://en.wikipedia.org/wiki/' + loc.replace(' ', '_'))
             .show();
         } else {
           $('a.flag', container).hide();
         }
         if (response.newsitem) {
           $('.news-teaser a', container)
             .attr('href', '#news,' + response.newsitem.id)
               .text(response.newsitem.title);
           $('.news-teaser', container).show();
         } else {
           $('.news-teaser', container).hide();
         }

         if (page == 'embassy') {
           _load_embassy(function() {
             $('.embassy .none', container).hide();
             $('.embassy', container).hide().fadeIn(300);
             Utils.update_title();
           });
         } else if (page == 'intro') {
           _load_intro(function() {
             $('.intro', container).hide().fadeIn(300);
             Utils.update_title();
           });
         } else if (page == 'jobs') {
           _load_jobs(function() {
             $('.jobs', container).hide().fadeIn(300);
             Utils.update_title();
           });
         } else if (page == 'pictures') {
           _load_pictures(function() {
             $('.pictures', container).hide().fadeIn(300);
             Utils.update_title();
           });
         } else if (page == 'messages') {
           _load_messages(function() {
             $('.messages', container).hide().fadeIn(300);
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
                     .append($('<span>').text(Utils.formatCost(each.cost.economy, true)))
                       .appendTo(c);
               });
             });
           } else {
             if (!_has_loaded_home) {
               $('.home', container).hide().fadeIn(300);
             }
             _has_loaded_home = true;

             $.getJSON(AIRPORT_URL, {ticket_progress: true}, function(response) {
               if (!response.destinations.length) {
                 $('.affordable-tickets:visible', container).hide();
                 return;
               }
               var c = $('.affordable-tickets', container);

               if (c.data('for_amount') === response.for_amount) {
                 // for_amount hasn't changed
                 return;
               }
               c.data('for_amount', response.for_amount);
               $('.destination', c).remove();
               var d_container = $('.destinations', container);
               var count = 0;
               $.each(response.destinations, function(i, destination) {
                 var d = $('<div>').addClass('destination');

                 var dd = $('<div>')
                   .addClass('progress').addClass('progress-striped');
                 if (destination.canafford) {
                   dd.addClass('progress-success')
                     .append($('<div>').addClass('bar').css('width', '100%'));
                 } else {
                   dd.append($('<div>').addClass('bar').css('width', destination.percentage + '%'));
                 }
                 $('<p>')
                   .append($('<a href=""></a>')
                           .addClass('overlay-changer')
                           .addClass(destination.canafford ? 'can-afford' : 'cant-afford')
                           .attr('href', '#airport,' + destination.code)
                           .click(function() {
                             Loader.load_hash('#airport,' + destination.code);
                           })
                           .text(destination.name))
                   .append($('<span>')
                           .addClass('ticket-info')
                           .text(Utils.formatCost(destination.cost.economy, true)))
                   .appendTo($('.bar', dd));
                 if (count >= 4) {
                   d.hide();
                 }
                 count++;
                 d.append(dd);
                 d_container.append(d);
               });
               if (count >= 4) {
                 $('.show-more', c).show();
               } else {
                 $('.show-more', c).hide();
               }
               c.show();
               $('.affordable-tickets:hidden', container).show();
             });
           }
           Utils.update_title();
         }
       });
     },
    setup: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
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
      //$('.pictures-link', container).hide();
    }
  };
})();

Plugins.start('city', function(page, callback) {
  City.setup();
  City.setup_message_post();
  City.load(page);

});


Plugins.stop('city', function() {
  City.teardown();
});
