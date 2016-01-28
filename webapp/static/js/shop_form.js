$('#shop-form').bind('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
  var btn = $form.find('.btn-primary')[0];
  btn.disabled = true;
  var formData = {};

  $form.find(".form-serialize").each(function () {
    formData[this.name] = $(this).val();
  });
  $.ajax({
    type: $form.attr('method'),
    url: $form.attr('action'),
    data: JSON.stringify(formData),
    contentType: 'application/json'
  }).done(function (r) {
    window.location.href = "/dashboard";
  }).fail(function (r) {
    btn.disabled = false;
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#product-post-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});