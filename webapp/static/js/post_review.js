function inIframe () {
    try {
        return window.self !== window.top;
    } catch (e) {
        return true;
    }
}

$('input[type=file]').change(function (e) {
  $('#review-image').attr('src', "/static/img/ajax-loader.gif");
  e.preventDefault(); // Prevent the form from submitting via the browser.
  // select the form and submit
  var form = $(this).parent()[0];
  var $form = $(form);
  var formData = new FormData(form);
  $.ajax({
    type: $form.attr('method'),
    url: $form.attr('action'),
    data: formData,
    cache: false,
    contentType: false,
    processData: false
  }).done(function (r) {
    var image_url = r.image_url;
    $('#image_url').val(image_url);
    $('#review-image').attr('src', image_url).show();
  }).fail(function () {
    // Optionally alert the user of an error here...
  });
});

$('#review-form').bind('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
  var formData = {};

  $form.find(".form-serialize").each(function () {
    formData[this.name] = $(this).val();
  });
  formData['star_rating'] = $('input:radio[name=star_rating]:checked').val();
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
        .html('<p>Thank you for posting review</p>')
        .slideDown();
    if (inIframe) {
      document.location.href = document.location.href;
    }
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#ajax-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});