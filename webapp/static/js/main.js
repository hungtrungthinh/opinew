var csrftoken = $('meta[name=csrf-token]').attr('content');

var ASYNC_SCRIPTS = ASYNC_SCRIPTS || [];

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

function loadAsync() {
  for (var i = 0; i < ASYNC_SCRIPTS.length; i++) {
    $.getScript(ASYNC_SCRIPTS[i]);
  }
}

function showMoreReview(el) {
  var reviewId = $(el).data('review-id');
  $(el).hide();
  $("#review-less-" + reviewId).hide();
  $("#review-more-" + reviewId).slideDown();
  return false;
}

$('#modal-lightbox').on('show.bs.modal', function (event) {
  var button = $(event.relatedTarget);
  var imageUrl = button.data('image-url');
  var modal = $(this);
  modal.find('#lightbox-img').attr('src', imageUrl).css('height', Math.max(document.documentElement.clientHeight, window.innerHeight || 0) - 60 + 'px');
});

function shareReview(reviewId) {
  var dataReviewEl = $('#data-review-' + reviewId);
  var reviewBody = dataReviewEl.find('.review-body').text();
  var reviewShopName = dataReviewEl.find('.review-shop-name').text();
  var productUrl = dataReviewEl.find('.review-product-url').text();
  console.log('TODO: share id: ' + reviewId + '\n' +
              'product_url' + productUrl + '\n' +
              'body: ' + reviewBody + '\n' +
              'shop_name: ' + reviewShopName);
  //https://developers.facebook.com/docs/sharing/reference/feed-dialog/v2.5
  FB.ui({
    method: 'feed',
    link: 'https://opinew.com/review/' + reviewId,
  }, function (response) {
  });
}

$(document).ready(function () {
  $('.review-more-btn').click(function (e) {
    e.preventDefault();
    showMoreReview(this);
  });

  $('.review-body-content').each(function () {
    var finalText = $(this).html();
    for (var property in EMOJIS) {
      if (EMOJIS.hasOwnProperty(property)) {
        finalText = finalText.replace(property, "<img style='height: 1.2em' src='https://twemoji.maxcdn.com/36x36/" + EMOJIS[property] + "' />")
      }
    }
    $(this).html(finalText);
  });
  loadAsync();

});
