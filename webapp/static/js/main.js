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

function renderMessageTemplate(message, category) {
  return "<div class=\"alert alert-flash alert-" + category + "\"><button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\"><span aria-hidden=\"true\">&times;</span></button>" + message + "</div>"
}

function flashMessage(message, category) {
  $('#flashed-messages').append(renderMessageTemplate(message, category));
}

$.ajaxSetup({
  beforeSend: function (xhr, settings) {
    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken)
    }
  }
});

$.fn.serializeObject = function () {
  var o = {};
  var a = this.serializeArray();
  $.each(a, function () {
    if (o[this.name]) {
      if (!o[this.name].push) {
        o[this.name] = [o[this.name]];
      }
      o[this.name].push(this.value || '');
    } else {
      o[this.name] = this.value || '';
    }
  });
  return o;
};

// Javascript to enable link to tab
var url = document.location.toString();
if (url.match('#')) {
  $('.nav-tabs a[href=#' + url.split('#')[1] + ']').tab('show');
}

// Change hash for page-reload
$('.nav-tabs a').on('shown.bs.tab', function (e) {
  window.location.hash = e.target.hash;
});

function showMoreReview(el) {
  var reviewId = $(el).data('review-id');
  $(el).hide();
  $("#review-less-" + reviewId).hide();
  $("#review-more-" + reviewId).slideDown();
  return false;
}

function showMoreComments(el) {
  var reviewId = $(el).data('review-id');
  $(el).hide();
  $("#comments-more-" + reviewId).slideDown();
  return false;
}

$('#modal-lightbox').on('show.bs.modal', function (event) {
  var button = $(event.relatedTarget);
  var imageUrl = button.data('image-url');
  var modal = $(this);
  modal.find('#lightbox-img').attr('src', imageUrl);
});

function getCookie(cname) {
  var name = cname + "=";
  var ca = document.cookie.split(';');
  for (var i = 0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') c = c.substring(1);
    if (c.indexOf(name) == 0) return c.substring(name.length, c.length);
  }
  return "";
}

function sendAsync(url, successCallback) {
  $.ajax({
    url: url + '?async=1'
  }).done(function (r) {
    successCallback(r);
  }).fail(function (r) {
    var error = r.responseJSON.error;
    flashMessage(error, 'error');
  });
}

/* Change interaction button style and success callbacks */

function changeInteractionButtonStyle(response, el, trueActionClass) {
  var $el = $(el);
  if (response.action) {
    $el.addClass(trueActionClass).removeClass('btn-default');
  } else {
    $el.addClass('btn-default').removeClass(trueActionClass);
  }
  var $countEl = $el.find('.count'); if ($countEl) {
    $countEl.text(response.count);
  }
}

function shareReviewSuccess(response, el) {
  changeInteractionButtonStyle(response, el, 'btn-info');
}

function likeReviewSuccess(response, el) {
  changeInteractionButtonStyle(response, el, 'btn-success');
}

function reportReviewSuccess(response, el) {
  changeInteractionButtonStyle(response, el, 'btn-danger');
}

function featureReviewSuccess(response, el) {
  changeInteractionButtonStyle(response, el, 'btn-warning');
}

/* Interaction buttons asyncrounous actions */

function likeReview(el, reviewId) {
  sendAsync('/review-like/' + reviewId, function (response) {
    likeReviewSuccess(response, el);
  });
}

function reportReview(el, reviewId) {
  sendAsync('/review-report/' + reviewId, function (response) {
    reportReviewSuccess(response, el);
  });
}

function featureReview(el, reviewId) {
  sendAsync('/review-feature/' + reviewId, function (response) {
    featureReviewSuccess(response, el);
  });
}

function shareReview(el, reviewId) {
  FB.ui({
    method: 'feed',
    link: 'https://opinew.com/review/' + reviewId
  }, function (response) {
    if (response && !response.error_code) {
      // Log a share on our side
      sendAsync('/review-share/' + reviewId, function () {
        shareReviewSuccess(el);
      });
    }
  });
}

/* Replace emojis */
function replaceEmojis() {
  $('.review-body-content').each(function () {
    var finalText = $(this).html();
    for (var property in EMOJIS) {
      if (EMOJIS.hasOwnProperty(property)) {
        finalText = finalText.replace(property, "<img style='height: 1.2em' src='https://twemoji.maxcdn.com/36x36/" + EMOJIS[property] + "' />")
      }
    }
    $(this).html(finalText);
  });
}

$(document).ready(function () {
  replaceEmojis();
});
