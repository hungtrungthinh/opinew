//var OPINEW_URL = "http://localhost:5000";
var OPINEW_URL = "https://opinew.com";
var OPINEW_PLUGIN_URL = OPINEW_URL + "/plugin";
var FUNNEL_STREAM_ID;

var pluginElement = window.document.getElementById("opinew-plugin");
var opinewShopId = pluginElement.getAttribute('data-opinew-shop-id');
var opinewProductPlatformId = pluginElement.getAttribute('data-platform-product-id');
var productLocation = window.location.host + window.location.pathname;

function insertPlugin(url) {
  pluginElement.innerHTML =
      '<iframe style="border:0; width:100%; height:500px;" src="' + url + '" id="opinew-plugin-iframe">' + '</iframe>';
  var frame = document.getElementById('opinew-plugin-iframe');
  frame.addEventListener('load', function () { // only access when loaded
    FUNNEL_STREAM_ID = frame.contentWindow.FUNNEL_STREAM_ID; // get reference to iframe's `window`
  });
  // add funnel js
  js = document.createElement("script");
  js.type = "text/javascript";
  js.src = OPINEW_URL + '/static/js/funnel.js';

  document.body.appendChild(js);
}

function loadPlugin() {
  var finalUrl;
  if (opinewProductPlatformId) {
    finalUrl = OPINEW_PLUGIN_URL + '?shop_id=' + opinewShopId + '&get_by=platform_id&platform_product_id=' + opinewProductPlatformId;
  } else {
    finalUrl = OPINEW_PLUGIN_URL + '?shop_id=' + opinewShopId + '&get_by=url&product_url=' + productLocation;
  }
  insertPlugin(finalUrl);
}

loadPlugin();