function inIframe() {
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
    setImageUrl(image_url);
  }).fail(function () {
    // Optionally alert the user of an error here...
  });
});

function setImageUrl(imageUrl) {
  console.log('fdsafs');
  $('#image_url').val(imageUrl);
  $('#review-image').attr('src', imageUrl).show();
}

function getGiphyImages(form) {
  $.ajax({
    type: form.attr('method'),
    url: form.attr('action'),
    data: form.serialize(),
    cache: false,
    contentType: false,
    processData: false
  }).done(function (r) {
    $('#giphy-images').html("");
    for (var i = 0; i < r.data.length; i++) {
      var imageUrl = r.data[i].images.fixed_height.url;
      $('#giphy-images').append("<a href='javascript:setImageUrl(\"" + imageUrl + "\");'><img style='margin: 0 10px 0 0' class=' img-thumbnail' src='" + imageUrl + "' /></a>");
    }
  }).fail(function () {
    // Optionally alert the user of an error here...
  });
}

function giphyLabel(button) {
  var query = $(button).text();
  $('#review-giphy-search').val(query);
  $('#review-giphy-form').submit()
}

$('#review-giphy-form').on("submit", function (e) {
  $('#giphy-images').attr('src', "/static/img/ajax-loader.gif");
  e.preventDefault(); // Prevent the form from submitting via the browser.
  // select the form and submit
  var $form = $(this);
  getGiphyImages($form);
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
    if ($('#in-mobile-next')) {
      console.log($('#in-mobile-next').val());
      document.location.href = $('#in-mobile-next').val();
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

$.emojiarea.path = 'http://twemoji.maxcdn.com/36x36/';
$.emojiarea.icons = EMOJIS;
$('textarea').emojiarea({button: '#emoji-button'});

$(document).ready(function () {
  getGiphyImages($('#review-giphy-form'));
});