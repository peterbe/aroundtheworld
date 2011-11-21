function Soundplayer(definitions) {
  this.definitions = definitions;
  return this;
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
  document.getElementById(this.preload(key)).play();
  if (callback) {
    callback();
  }
};
