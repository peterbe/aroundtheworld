var Diploma = (function() {
  var container = $('#diploma');
  return {
     load: function() {

     }
  }
})();

Plugins.start('diploma', function() {
  Diploma.load();
});


Plugins.stop('diploma', function() {
  //Airport.teardown();
});
