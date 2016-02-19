function hookAnswerForm() {
  $('.answer-question-form').on("submit", function (e) {
    e.preventDefault(); // Prevent the form from submitting via the browser.
    // select the form and submit
    var $form = $(this);
    $.ajax({
      type: $form.attr('method'),
      url: $form.attr('action'),
      data: JSON.stringify($form.serializeObject()),
      contentType: 'application/json'
    }).done(function (r) {
      $('#your-answer').append(
          '<div class="row"><div class="col-xs-11">' +
          '<p>' + r.body + '</p>' +
          '</div>' +
          '<div class="col-xs-1">' +
          '<img src="' + r.user.image_url + '" class="img-circle img-responsive" alt="profile pic"/>' +
          '</div></div>'
      )
    }).fail(function (r) {
      var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
      $('#ajax-status')
          .addClass('alert-danger')
          .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
          .slideDown();

    });
  });
}


var shop_id = document.location.pathname.split('/')[2];
var callbacks = [null, null, hookAnswerForm];

function getPage(page, callback) {
  $.ajax("/dashboard/" + shop_id + "/" + page, {
    success: function (r) {
      $('#' + page).html(r);
      if (callback)
        callback();
    }
  });
}

$('#shop-form').bind('submit', function (e) {
  var $form = $(this);
  var formData = {};

  $form.find(".form-serialize").each(function () {
    formData[this.name] = $(this).val();
  });
  $('#ajax-status').hide()

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
        .html('<p>Shop changes saved!</p>')
        .slideDown();
  }).fail(function (r) {
    var errors = JSON.stringify(r.responseJSON.validation_errors) || JSON.stringify(r.responseJSON.message);
    $('#ajax-status')
        .addClass('alert-danger')
        .html('<p><strong>Something went wrong</strong>: ' + errors + '</p>')
        .slideDown();

  });
  return false;
});

// This identifies your website in the createToken call below
var STRIPE_PUBLISHABLE_API_KEY = $('#STRIPE_PUBLISHABLE_API_KEY').data('key');
Stripe.setPublishableKey(STRIPE_PUBLISHABLE_API_KEY);

$('#payment-form').submit(function (event) {
  var $form = $(this);

  // Disable the submit button to prevent repeated clicks
  $form.find('button').prop('disabled', true);
  $('#submiting-card').show();

  Stripe.card.createToken($form, stripeResponseHandler);

  // Prevent the form from submitting with the default action
  return false;
});

function stripeResponseHandler(status, response) {
  var $form = $('#payment-form');

  if (response.error) {
    // Show the errors on the form
    $form.find('.payment-errors').text(response.error.message).slideDown();
    $form.find('button').prop('disabled', false);
    $('#submiting-card').hide();
  } else {
    // response contains id and card, which contains additional card details
    var token = response.id;
    // Insert the token into the form so it gets submitted to the server
    $form.append($('<input type="hidden" name="stripe-token" />').val(token));
    // and submit
    $form.get(0).submit();
  }
}
