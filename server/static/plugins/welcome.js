var Welcome = (function() {
  var URL = '/welcome.json';
  var LOGIN_URL = '/auth/anonymous/';
  var container = $('#welcome');
  var _once = false;
  var _loading = false;

  function setup_once() {
    $('a.login-shortcut', container).click(function() {
      if (_loading) return;
      _loading = true;
      $('.login', container).hide();
      $('.loading', container).show();
      $.post(LOGIN_URL, function() {
        State.update(function() {
          $('.loading:visible', container).hide();
          _loading = false;

          Welcome.update();
        });
      });
      return false;
    });
  }

  return {
     update: function() {
       if (!_once) {
         setup_once();
         _once = true;
       }
       $('.not-logged-in .loading', container).hide();
       $('.not-logged-in .login', container).show();
       /*
       if (map && !STATE.location) {
         var t0 = new Date().getTime();
         $.getJSON('/iplookup/', function(response) {
           if (response.lat && response.lng) {
             var t1 = new Date().getTime();
             // if it took a really long time, (more than 1 second)
             // then don't bother because it would just look weird
             if ((t1 - t0) < 1000) {
               map.setCenter(new google.maps.LatLng(response.lat, response.lng));
               map.setZoom(5);
             }
           }
         });
       }
       */
       $('.alternative', container).hide();
       if (!STATE.user) {
         $('.not-logged-in', container).show();
         if (STATE.invites_pending) {
           var names = [];
           $.each(STATE.invites_pending, function(i, each) {
             names.push(each.from + "'s");
           });
           $('.pending-invites .names', container).text(names.join(' and '));
           $('.pending-invites', container).show();
         } else {
           $('.pending-invites', container).hide();
         }
       } else if (STATE.location && STATE.location.nomansland) {
         $('.nomansland', container).show();

       } else if (!STATE.location) {
         $('.not-chosen-location', container).show();
         $.getJSON('/location.json', function(response) {
           var c = $('select[name="id"]', container);
           var text;
           $.each(response.locations, function(i, each) {
             text = each.name;
             if (each.distance) {
               text += ' (' + Utils.formatMiles(each.distance) + ' miles from you)';
             }
             $('<option>')
               .attr('value', each.id)
                 .text(text)
                   .appendTo(c);
           });
           c.on('change', function() {
             $(this).parent('form').submit();
           });
           $('.not-chosen-location form', container).on('submit', function() {
             var id = $('select[name="id"] option:selected', container).attr('value');
             $.post('/location.json', {id:id}, function(response) {
               State.update();
               Loader.load_hash('#city');
             });
             return false;
           });
         });

       } else {
         $('.welcome-back', container).show();
         var c = $('.welcome-back', container);
         $('.current-location', c).html(STATE.location.name);
         $.getJSON(URL, {get: 'stats'}, function(response) {
           var c = $('.stats ul', container);
           $('li', c).hide();
           // totals
           $('li.totals', c).show();
           $('li.totals .total-coins', c).text(Utils.formatCost(response.coins_total, true));
           $('li.totals .total-miles', c).text(Utils.formatMiles(response.miles_total, true));
           // visited cities
           $('li.visited-cities', c).show();
           $('li.visited-cities .visited', c).text(response.visited_cities);
           $('li.visited-cities .visited-total', c).text(response.cities_max);
           // earned
           $('li.earned', c).show();
           $('li.earned .earned-total', c).text(Utils.formatCost(response.earned_total, true));
           $('li.earned .earned-jobs', c).text(Utils.formatCost(response.earned_jobs, true));
           $('li.earned .earned-questions', c)
             .text(Utils.formatCost(response.earned_questions, true));
           // answered
           $('li.answered', c).show();
           $('li.answered .answered-total', c).text(response.question_answers);
           $('li.answered .answered-right', c).text(response.question_answers_right);
           // authored questions
           if (response.authored_questions) {
             $('li.authored', c).show();
             $('li.authored .authored-submitted', c).text(response.authored_questions);
             $('li.authored .authored-published', c).text(response.authored_questions_published);
           }
           // invitations
           if (response.invitations) {
             $('li.invitations', c).show();
             $('li.invitations .invitations-sent', c).text(response.invitations);
             $('li.invitations .invitations-signedup', c).text(response.invitations_signedup);
           }

           $('.stats', container).show(300);

         });
       }
     }
  };
})();

Plugins.start('welcome', function() {
  // called every time this plugin is loaded
  Welcome.update();
});
