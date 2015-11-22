var shop_id = document.location.pathname.split('/')[2];
var pages = ["orders", "reviews"];

function getPage(page) {
  $.ajax("/dashboard/" + shop_id + "/" + page, {
    success: function (r) {
      $('#' + page).html(r);
      loadAsync();
    }
  });
}

for (var i = 0; i < pages.length; i++) {
  var page = pages[i];
  getPage(page);
}

$('#shop-form').bind('submit', function (e) {
  var $form = $(this);
  var formData = {};

  $form.find(".form-serialize").each(function () {
    formData[this.name] = $(this).val();
  });
  $('#ajax-status').hide()

  $.ajax({
    type: $form.attr('method'),
    url: $form.attr('action'),
    data: JSON.stringify(formData),
    contentType: 'application/json'
  }).done(function (r) {
    $('#product-review').hide();
    $('#ajax-status')
        .removeClass('alert-danger')
        .addClass('alert-success')
        .html('<p>Shop changes saved!</p>')
        .slideDown();
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#ajax-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});


