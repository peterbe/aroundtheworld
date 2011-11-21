function Soundplayer(definitions) {
  this.definitions = definitions;
}

Soundplayer.prototype.preload = function(key) {
  var id = 'sound-' + key;
  if (!document.getElementById(id)) {
    if (!this.definitions[key]) {
      //throw "Sound for '" + key + "' not defined";
      console.warn("Sound for '" + key + "' not defined");
      return;
    } else if (this.definitions[key].search(/\.ogg/i) == -1) {
      throw "Sound for '" + key + "' must be .ogg URL";
    }
    var a = document.createElement('audio');
    a.setAttribute('id', id);
    a.setAttribute('src', this.definitions[key]);
    document.body.appendChild(a);
  }
  return id;
};

Soundplayer.prototype.play = function(key, callback) {
  document.getElementById(preload_sound(key)).play();
  if (callback) {
    callback();
  }
};

///* Call to create and partially download the audo element.
// * You can all this as much as you like. */
//function preload_sound(key) {
//  var id = 'sound-' + key;
//  if (!document.getElementById(id)) {
//    if (!SOUND_URLS[key]) {
//      throw "Sound for '" + key + "' not defined";
//    } else if (SOUND_URLS[key].search(/\.ogg/i) == -1) {
//      throw "Sound for '" + key + "' must be .ogg URL";
//    }
//    var a = document.createElement('audio');
//    a.setAttribute('id', id);
//    a.setAttribute('src', SOUND_URLS[key]);
//    document.body.appendChild(a);
//  }
//  return id;
//}
//
//function play_sound(key, callback) {
//  document.getElementById(preload_sound(key)).play();
//  if (callback) {
//    callback();
//  }
//}
