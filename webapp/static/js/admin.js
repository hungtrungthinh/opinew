
function hookRenderButton(){
    $('#submit-render-form').bind('click', function (e) {
      renderEmail();
      return false;
    });
}


function renderEmail(){
    $form = $('#render-form');
    var templateName = $("#template-name").val();
    $.ajax({
    type: $form.attr('method'),
    url: $form.attr('action'),
    data: {"template_name":templateName},
  }).done(function (data) {
        $('#email-render-container').html(data)
  }).fail(function (r) {

  });
}


$(document).ready(function () {
    hookRenderButton();
});
