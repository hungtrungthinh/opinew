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
    $('#product-post-status')
        .removeClass('alert-danger')
        .addClass('alert-success')
        .html('<p>Thank you for posting review</p>')
        .slideDown();
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors);
    $('#product-post-status')
        .addClass('alert-danger')
        .html('<p>Something went wrong: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});

$('input[type=file]').change(function (e) {
  $('#review-photo-img').attr('src', "/static/img/ajax-loader.gif");
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
    var photo_url = r.photo_url;
    $('#review-photo-img').attr('src', '/media/review/' + photo_url);
    $('#photo_url').val(photo_url);
    $('#review-photo-img').show();

  }).fail(function () {
    // Optionally alert the user of an error here...
  });
});