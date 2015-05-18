// destroy the modal object when closed
$('body').on('hidden.bs.modal', '.modal', function () {
$(this).removeData('bs.modal');
});

jQuery.validator.setDefaults({
  debug: true,
  success: "valid"
});

$( "#compareForm" ).validate({
  rules: {
      commit2: {
          required: function(element) {
              return $("#patch").is(':empty');
          }
      },
      patch: {
          required: function(element) {
              return $("#commit2").is(':empty');
          }
      }
  }
});

$(document).ready(function() {
  $("form#compare").submit(function(e){
      $.ajax({
          type: "POST",
          url: "submit",
          data: $(this).serialize(),
          beforeSend: function(){
            $('.modal-content', '#myModal').html($("#loaderDiv"));
            console.log($("#loaderDiv"));
            $("#loaderDiv").collapse('show');
          },
          success: function(data){
            $("#loaderDiv").hide();
            $("#loaderDiv").collapse('hide');
            $('.modal-content', '#myModal').html(data);
          },
          error: function(msg){
            console.log(msg);
            $('#myModal').modal('hide');
          }
      })
      .done(function(data) {
      });
      e.preventDefault();
      return false; // avoid to execute the actual submit of the form.
  });
} );

