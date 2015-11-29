$('.review-feature-form').on('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
  var $featureActionInput = $($form.children('.feature-action-input'));
  var $featureButton = $($form.children('.btn'));
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
    var curText = $featureButton.html();
    if (r.action == 1) {
      $featureActionInput.val(0);
      $featureButton.addClass('btn-warning').removeClass('btn-default').children('.feature-text');
    } else {
      $featureActionInput.val(1);
      $featureButton.addClass('btn-default').removeClass('btn-warning').children('.feature-text');
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