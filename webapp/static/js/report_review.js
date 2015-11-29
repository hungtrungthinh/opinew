$('.review-report-form').on('submit', function (e) {
  e.preventDefault();
  var $form = $(this);
  var $reportActionInput = $($form.children('.report-action-input'));
  var $reportButton = $($form.children('.btn'));
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
    var curText = $reportButton.html();
    if (r.action == 1) {
      $reportActionInput.val(0);
      $reportButton.addClass('btn-danger').removeClass('btn-default').children('.report-text');
    } else {
      $reportActionInput.val(1);
      $reportButton.addClass('btn-default').removeClass('btn-danger').children('.report-text');
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