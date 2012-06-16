var Awards = (function() {
  var container = $('#awards');
  var URL = '/awards.json';
  var loaded = {};
  var thumbnail = $('img.thumbnail-template', container);

  function _display_award(award) {
    var c = $('.index', container);
    loaded[award.id] = award;
    var d = $('<div>').addClass('award');
    var a = $('<a href="#awards,">')
      .attr('href', '#awards,' + award.id)
      .data('id', award.id).click(function() {
        L($(this).data('id'));
        return false;
        L('LOAD', $(this).data('id'));
        Awards.load_award($(this).data('id'), function() {
          $('.wrapper-outer').show();
        });
      return false;
    });
    thumbnail.clone().show().appendTo(a);
    a.appendTo(d);
    d.append(a.clone().text(award.description).addClass('title'));
    d.append($('<p>').text("Awarded to you on " + award.date));
    c.append(d);
  }

  function _display_modal_award(award) {
    var c = $('.wrapper', container);
    $('.category', c).text(award.category);
    $('.location', c).text(award.location);
    $('.name', c).text(award.name);
    $('.date', c).text(award.date);
    $('.signature', c).text(award.ambassador);
  }

  return {
     load: function() {
       Utils.update_title();
       $.getJSON(URL, function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         $('.index .award', container).remove();
         loaded = {};
         $.each(response.awards, function(i, award) {
           _display_award(award);
         });
       });
     },
    load_award: function(id, callback) {
      $.getJSON(URL, {id: id}, function(response) {
        if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
        if (response.error == 'INVALIDAWARD') {
          alert('Error! Invalid award');
          return;
        }
        //loaded = {};
        _display_modal_award(response.award);
        if (callback) callback();
      });
    }
  }
})();

Plugins.start('awards', function(id) {
  if (id) {
    Awards.load_award(id, function() {
      $('.wrapper-outer').show();
    });
  }
  Awards.load();
});


Plugins.stop('awards', function() {
  //Airport.teardown();
});
