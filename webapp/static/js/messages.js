$('#ask-question-form').on("submit", function (e) {
  e.preventDefault(); // Prevent the form from submitting via the browser.
  // select the form and submit
  var $form = $(this);
  $.ajax({
    type: $form.attr('method'),
    url: $form.attr('action'),
    data: JSON.stringify($form.serializeObject()),
    contentType: 'application/json'
  }).done(function (r) {
    $('#your-question').append(
        '<div class="row"><div class="col-xs-1">' +
            '<img src="/media/user/default_user.png" class="img-circle img-responsive" alt="default user profile pic"/>' +
        '</div>' +
        '<div class="col-xs-11 message-bubble">' +
            '<p>' + r.body + '</p>' +
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