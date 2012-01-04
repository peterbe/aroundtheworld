$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


var Settings = (function() {
  var container = $('#settings');

  function _set_form_data(data) {
    var f = $('form', container);
    if (data.disable_sound) {
      $('input[name="disable_sound"]', f).attr('checked', 'checked');
    } else {
      $('input[name="disable_sound"]', f).removeAttr('checked');
    }
  }

  return {
     setup_form: function() {
       var f = $('form', container);

       $.getJSON('/settings.json', function(response) {
         if (response.error == 'NOTLOGGEDIN') return State.redirect_login();
         _set_form_data(response);
       });

       $('input', f).on('change', function() {
         f.submit();
       });
       f.submit(function() {
         $.post('/settings.json', $(this).serializeObject(), function(response) {
           $('.saved-notification:hidden', container).show();
           _set_form_data(response);
           State.update();
           setTimeout(function() {
             $('.saved-notification:visible', container).fadeOut(500);
           }, 2 * 1000);
         });
         return false;
       });

     }
  };
})();

//Quiz.load_next();  // kick it off

Plugins.start('settings', function() {
  // called every time this plugin is loaded
  Settings.setup_form();
});
