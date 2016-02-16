var OPINEW_URL = "https://www.opinew.com";
var OPINEW_PLUGIN_URL = OPINEW_URL + "/plugin";
var OPINEW_STAR_PLUGIN_URL = OPINEW_URL + "/plugin-stars";
var FUNNEL_STREAM_ID;

var pluginElement = window.document.getElementById("opinew-plugin");

if (pluginElement) {
  var opinewShopId = pluginElement.getAttribute('data-opinew-shop-id');
  var opinewProductPlatformId = pluginElement.getAttribute('data-platform-product-id');
  var productLocation = window.location.protocol + '//' + window.location.host + window.location.pathname;
  loadPlugin();
}

function insertPlugin(url) {
  pluginElement.innerHTML =
      '<iframe style="border:0; width:100%; height:700px;" src="' + url + '" id="opinew-plugin-iframe">' + '</iframe>';
}

function loadPlugin() {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', OPINEW_URL + '/get-next-funnel-stream');
  xhr.send(null);
  xhr.onreadystatechange = function () {
    if (xhr.readyState == XMLHttpRequest.DONE) {
      FUNNEL_STREAM_ID = xhr.responseText;
      var finalUrl = OPINEW_PLUGIN_URL + '?shop_id=' + opinewShopId + '&funnel_stream_id=' + FUNNEL_STREAM_ID;
      if (opinewProductPlatformId) {
        finalUrl = finalUrl + '&get_by=platform_id&platform_product_id=' + opinewProductPlatformId;
      } else {
        finalUrl = finalUrl + '&get_by=url&product_url=' + productLocation;
      }
      insertPlugin(finalUrl);
    }
  }

}


var IS_GLIMPSED = false;
var IS_FULLY_SEEN = false;

var ELEMENT = document.getElementById('opinew-plugin');

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
  if (el) {
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
  xhr.open('GET', OPINEW_URL + '/update-funnel?funnel_stream_id=' + FUNNEL_STREAM_ID + '&action=' + action);
  xhr.send(null);
}

function loadStarPlugin() {
  var finalStarUrl = OPINEW_STAR_PLUGIN_URL;
  var starPluginElements = document.getElementsByClassName('opinew-plugin-stars');
  for (var i = 0; i < starPluginElements.length; i++) {
    var starPluginElement = starPluginElements[i];
    var opinewShopId = starPluginElement.getAttribute('data-opinew-shop-id');
    finalStarUrl = finalStarUrl + '?shop_id=' + opinewShopId;
    var opinewStarProductPlatformId = starPluginElement.getAttribute('data-platform-product-id');
    if (opinewStarProductPlatformId) {
      finalStarUrl = finalStarUrl + '&get_by=platform_id&platform_product_id=' + opinewStarProductPlatformId;
      starPluginElement.innerHTML = '<iframe style="border:0; width:100%; height:60px;" src="' + finalStarUrl + '">' + '</iframe>';
    }
  }
}

loadStarPlugin();
