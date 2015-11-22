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