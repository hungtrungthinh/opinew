var ELEMENT = document.getElementById('opinew-plugin');

var IS_GLIMPSED = false;
var IS_FULLY_SEEN = false;
var IS_MOUSE_HOVER = false;
var IS_MOUSE_SCROLL = false;
var IS_MOUSE_CLICK = false;

function isElementGlimpsed(el) {
  var rect = el.getBoundingClientRect();
  return (
      rect.width > 0 &&
      rect.height > 0 &&
      rect.top <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.left <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

function isElementFullyVisible(el) {
  var rect = el.getBoundingClientRect();
  return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.width > 0 &&
      rect.height > 0 &&
      rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

function onVisibilityChange(el, callback) {
  var old_fully_visible;
  var old_glimpsed;
  return function () {
    var visible = isElementFullyVisible(el);
    var glimpsed = isElementGlimpsed(el);
    if (visible != old_fully_visible || glimpsed != old_glimpsed) {
      old_fully_visible = visible;
      old_glimpsed = glimpsed;
      if (typeof callback == 'function') {
        callback();
      }
    }
  }
}

var visibilityHandler = onVisibilityChange(ELEMENT, function () {
  if (FUNNEL_STREAM_ID) {
    if (isElementGlimpsed(ELEMENT) && !IS_GLIMPSED) {
      sendUpdate('glimpse');
      IS_GLIMPSED = true;
    }
    if (isElementFullyVisible(ELEMENT) && !IS_FULLY_SEEN) {
      sendUpdate('fully_seen');
      IS_FULLY_SEEN = true;
    }
  }
});

function onMouseClicked() {
  if (!IS_MOUSE_CLICK) {
    sendUpdate('mouse_click');
    IS_MOUSE_CLICK = true;
  }
}

function onMouseHovered() {
  if (!IS_MOUSE_HOVER) {
    sendUpdate('mouse_hover');
    IS_MOUSE_HOVER = true;
  }
}

function onMouseScrolled() {
  if (!IS_MOUSE_SCROLL) {
    sendUpdate('mouse_scroll');
    IS_MOUSE_SCROLL = true;
  }
}

// register handlers
if (window.addEventListener) {
  addEventListener('DOMContentLoaded', visibilityHandler, false);
  addEventListener('load', visibilityHandler, false);
  addEventListener('scroll', visibilityHandler, false);
  addEventListener('resize', visibilityHandler, false);
} else if (window.attachEvent) {
  attachEvent('onDOMContentLoaded', visibilityHandler); // IE9+ :(
  attachEvent('onload', visibilityHandler);
  attachEvent('onscroll', visibilityHandler);
  attachEvent('onresize', visibilityHandler);
}


function sendUpdate(action) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/update-funnel?funnel_stream_id=' + FUNNEL_STREAM_ID + '&action=' + action);
  xhr.send(null);
}