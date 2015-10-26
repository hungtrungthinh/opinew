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