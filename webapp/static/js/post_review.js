function inIframe() {
  try {
    return window.self !== window.top;
  } catch (e) {
    return true;
  }
}

var gifsLoaded = false;

$('#giphy-button').on('click', function () {
  if (!gifsLoaded) {
    getGiphyImages($('#review-giphy-form'));
  }
  $('#giphy-container').slideToggle();
});

$('#image-button').on('click', function () {
  $('#review-img-upload-input').trigger('click');
});

$('#review-img-upload-input').change(function (e) {
  e.preventDefault(); // Prevent the form from submitting via the browser.
  // select the form and submit
  var form = $(this).parent()[0];
  var $form = $(form);
  var formData = new FormData(form);
  var progressBar = $('.progress-bar');
  $.ajax({
    beforeSend: function () {
      progressBar.parent().show();
    },
    xhr: function () {
      var xhr = new window.XMLHttpRequest();
      xhr.upload.addEventListener("progress", function (evt) {
        if (evt.lengthComputable) {
          var percentComplete = evt.loaded / evt.total;
          percentComplete = parseInt(percentComplete * 100);
          var percent = percentComplete.toString() + '%';
          progressBar.html(percent);
          progressBar.css('width', percent);

        }
      }, false);

      return xhr;
    },
    type: $form.attr('method'),
    url: $form.attr('action'),
    data: formData,
    cache: false,
    contentType: false,
    processData: false
  }).done(function (r) {
    progressBar.parent().hide();
    progressBar.css('width', '5%');
    var image_url = r.image_url;
    setImageUrl(image_url);
  }).fail(function () {
    // Optionally alert the user of an error here...
  });
});

function setImageUrl(imageUrl) {
  $('#review-img-container').addClass('col-md-4');
  $('#review-body-container').removeClass('col-md-10').addClass('col-md-6');
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
      var imageUrl = r.data[i].images.fixed_height.url.replace('http://', 'https://');
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
  setImageUrl("/static/img/ajax-loader.gif");
  e.preventDefault(); // Prevent the form from submitting via the browser.
  // select the form and submit
  var $form = $(this);
  getGiphyImages($form);
});


$('#submit-review-form').bind('click', function (e) {
  var $form = $("#review-form");
  var formData = getReviewFormData($form);
  checkIfUserExists(formData['user_email']);
  return false;
});

function getReviewFormData(formSelector) {
  var $form = formSelector;
  var formData = {};

  $form.find(".form-serialize").each(function () {
    formData[this.name] = $(this).val();
  });
  formData['star_rating'] = $('input:radio[name=star_rating]:checked').val();
  if ($('#g-recaptcha-response')) {
    formData['g-recaptcha-response'] = $('#g-recaptcha-response').val();
  }
  if ($('#input-user-name')) {
    formData['user_name'] = $('#input-user-name').val();
  }
  if ($('#input-user-email')) {
    formData['user_email'] = $('#input-user-email').val();
  }
  if ($('#user-legacy-email')) {
    formData['user_legacy_email'] = $('#user-legacy-email').val();
  }
  if ($('#input-user-password') && !$('#input-user-password').is('[disabled=disabled]')) {
    formData['user_password'] = $('#input-user-password').val();
  }

  return formData
}

function postReview() {
  // Check if the session cookie is set.
  var sessionCookie = getCookie('session');
  var sessionCookieExists = true;
  // In case it is not, 3rd party cookies are probably disabled. Retrieve and then try to post
  if (!sessionCookie) {
    sessionCookieExists = false;
    var sessionJson = $.ajax({
      type: "GET",
      url: '/api/v1/session',
      async: false
    }).responseJSON;
    sessionCookie = sessionJson['session'];
    csrftoken = sessionJson['token'];
  }
  var $form = $("#review-form");
  var formData = getReviewFormData($form);
  $.ajax({
    type: $form.attr('method'),
    beforeSend: function (request) {
      request.setRequestHeader("X-CSRFToken", csrftoken);
      if (!sessionCookieExists) {
        request.setRequestHeader("x-session", sessionCookie);
      }
    },
    url: $form.attr('action'),
    data: JSON.stringify(formData),
    contentType: 'application/json'
  }).done(function (r) {
    $('#product-review').hide();
    $('#ajax-status')
        .removeClass('alert-danger')
        .addClass('alert-success')
        .html('<p>Thank you for posting review. Redirecting you to product page...</p>')
        .slideDown();
    if ($('#in-mobile-next')) {
      document.location.href = $('#in-mobile-next').val();
    }
    if (inIframe()) {
      document.location.href = document.location.href;
    } else {
      document.location.href = '/product/' + r.product.id;
    }

  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message) || r.responseJSON.error;
    $('#ajax-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();
    grecaptcha.reset();
  });
}

$.emojiarea.path = 'https://twemoji.maxcdn.com/36x36/';
$.emojiarea.icons = EMOJIS;
$('#textarea-body').emojiarea({button: '#emoji-button'});

function checkIfUserExists(userEmail) {
  $.ajax({
    url: "/api/v1/check-user-exists",
    data: {user_email: userEmail},
    success: function (r) {
      if (r.message == "exists") {
        if ($('#input-user-password').is('[disabled=disabled]')) {
          $('#input-user-password').removeAttr("disabled");
          $('#input-user-password-container').slideDown("slow");
        } else {
          postReview();
        }
      } else if (r.message == "newuser") {
        postReview();
      }
    }
  });
}

function hookEmojiAreaPlaceholder() {
  var wysiwygDiv = $('.emoji-wysiwyg-editor');
  var placeholder_text = $('#textarea-body').attr('placeholder');
  wysiwygDiv.css('white-space', 'pre-wrap');
  wysiwygDiv.text(placeholder_text);
  wysiwygDiv.css('color', 'grey');
  wysiwygDiv.css('font-size', '1em');
  wysiwygDiv.addClass('not-clicked-yet');
  $('.not-clicked-yet').click(function () {
        $(this).empty();
        $(this).focus();
        $(this).css('color', 'black');
        $(".not-clicked-yet").unbind("click");
      }
  );

}

$(document).ready(function () {
  hookEmojiAreaPlaceholder();
});