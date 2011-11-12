var _slides_setup = [];
function setupSlides() {

  // facts slider
  var id = '#facts-slider';
  if ($.inArray(id, _slides_setup) == -1) {
    $(id).bxSlider({
       auto: false,
      autoControls: false, pager:true
    });
    _slides_setup.push(id);
  }
}
