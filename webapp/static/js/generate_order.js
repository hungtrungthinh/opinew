var initialGenerateOrderAction = $('#update-product-form').attr('action');
$('#product-url-input').on('change', function () {
  var $form = $('#update-product-form');
  var filters = [{"name": "url", "op": "==", "val": $(this).val()}];
  $.ajax({
    type: 'get',
    url: initialGenerateOrderAction,
    data: {"q": JSON.stringify({"filters": filters})},
    dataType: "json",
    contentType: "application/json"
  }).done(function (r) {
    if (r.num_results == 1) {
      var productId = r.objects[0].id;
      var productName = r.objects[0].name;
      var productType = r.objects[0].product_type;
      var productReviewHelp = r.objects[0].review_help;

      $('#update-product-form').attr('method', 'patch').attr('action', initialGenerateOrderAction + '/' + productId);

      $('#product-id-input').val(productId);
      $('#product-name-input').val(productName);
      $('#product-type-input').val(productType);
      $('#product-review-help-input').val(productReviewHelp);
    } else {
      $('#update-product-form').attr('method', 'post').attr('action', initialGenerateOrderAction);
      $('#product-id-input').val('');
      $('#product-name-input').val('');
      $('#product-type-input').val('');
      $('#product-review-help-input').val('');
    }
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#product-post-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
});

$('#update-product-form').bind('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
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
    $('#product-post-status').slideUp();
    var productId = r.id;
    $('#product-id-input').val(productId);
    $('#generate-order-form').submit();
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#product-post-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});

$('#generate-order-form').bind('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
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
    $('#product-post-status').slideUp();
    $('#order-token').slideDown().html('Order token: <strong>' + r.token + '</strong>');
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#product-post-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});