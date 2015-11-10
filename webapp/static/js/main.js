var csrftoken = $('meta[name=csrf-token]').attr('content');

var EMOJIS = {
  ":joy:": "1f602.png",
  ":hearts:": "2665.png",
  ":heart:": "2764.png",
  ":heart_eyes:": "1f60d.png",
  ":unamused:": "1f612.png",
  ":blush:": "1f60a.png",
  ":sob:": "1f62d.png",
  ":kissing_heart:": "1f618.png",
  ":relaxed:": "263a.png",
  ":two_hearts:": "1f495.png",
  ":ok_hand:": "1f44c.png",
  ":weary:": "1f629.png",
  ":pensive:": "1f614.png",
  ":smirk:": "1f60f.png",
  ":grin:": "1f601.png",
  ":pray:": "1f64f.png",
  ":+1:": "1f44d.png",
  ":wink:": "1f609.png",
  ":raised_hands:": "1f64c.png",
  ":flushed:": "1f633.png"
};

$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken)
    }
  }
});

$('.review-like-form').on('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
  var $likeActionInput = $($form.children('.like-action-input'));
  var $likeButton = $($form.children('.btn'));
  var $likeCountEl = $($likeButton.children('.like-count'));
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
    if ($form.attr('method') == 'post') {
      var formAction = $form.attr('action');
      $form.attr('method', 'patch').attr('action', formAction + '/' + r.id);
    }

    if (r.action == 1) {
      $likeActionInput.val(0);
      $likeButton.addClass('btn-success').removeClass('btn-default');
      $likeCountEl.text(parseInt($likeCountEl.text()) + 1);
    } else {
      $likeActionInput.val(1);
      $likeButton.addClass('btn-default').removeClass('btn-success');
      $likeCountEl.text(parseInt($likeCountEl.text()) - 1);
    }

  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#product-post-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});

// Javascript to enable link to tab
var url = document.location.toString();
if (url.match('#')) {
    $('.nav-pills a[href=#'+url.split('#')[1]+']').tab('show') ;
}

// Change hash for page-reload
$('.nav-pills a').on('shown.bs.tab', function (e) {
    window.location.hash = e.target.hash;
});

$(document).ready(function () {
  $('.review-body-content').each(function () {
    var finalText = $(this).text();
    for (var property in EMOJIS) {
      if (EMOJIS.hasOwnProperty(property)) {
        finalText = finalText.replace(property, "<img style='height: 1.2em' src='http://twemoji.maxcdn.com/36x36/" + EMOJIS[property] + "' />")
      }
    }
    $(this).html(finalText);
  })
});
