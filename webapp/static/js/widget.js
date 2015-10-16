var OPINEW_PLUGIN_URL = "http://localhost:5000/plugin";

var pluginElement = window.document.getElementById("opinew-plugin");
var opinewShopId = pluginElement.getAttribute('data-opinew-shop-id');
var productLocation = window.location.href;

function insertPlugin(url) {
  pluginElement.innerHTML =
      '<iframe style="border:0; width:100%; height:500px;"' +
            'src="' + url + '">' +
      '</iframe>'
}

function loadPlugin() {
  insertPlugin(OPINEW_PLUGIN_URL + '?shop_id=' + opinewShopId + '&product_location=' + productLocation);
}

loadPlugin();