var shop_id = document.location.pathname.split('/')[2];
var pages = ["products", "orders", "reviews"];

function getPage(page) {
  $.ajax("/dashboard/" + shop_id + "/" + page, {
    success: function (r) {
      $('#' + page).html(r);
    }
  });
}

for (var i = 0; i < pages.length; i++) {
  var page = pages[i];
  getPage(page);
}
