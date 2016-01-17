var ELEMENT = document.getElementById('opinew-plugin-html');

var IS_MOUSE_HOVER = false;
var IS_MOUSE_SCROLL = false;
var IS_MOUSE_CLICK = false;

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

window.onclick = onMouseClicked;
window.onmouseover = onMouseHovered;
window.onwheel = onMouseScrolled;


function sendUpdate(action) {
  if (FUNNEL_STREAM_ID) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/update-funnel?funnel_stream_id=' + FUNNEL_STREAM_ID + '&action=' + action);
    xhr.send(null);
  }
}