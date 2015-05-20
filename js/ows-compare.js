// destroy the modal object when closed
$('body').on('hidden.bs.modal', '.modal', function () {
  $(this).removeData('bs.modal');
});

$(document).ready(function() {
  jQuery.validator.setDefaults({
    debug: true,
    success: "valid"
  });

  $("form#compare").validate({
    rules: {
      commit2: {
        required: "#patch:empty"
      },
      patch: {
        required: "#commit2:blank"
      }
    },
    messages: {
       commit2: "Please enter either a commit ref or a patch file.",
       patch: "Please enter either a commit ref or a patch file."
    },
    submitHandler: function(form) {
      var data = new FormData(form);    
      console.log("submit");
      console.log(data);
      console.log(form);

      form.submit(function(e){
        $.ajax({
          type: "POST",
          url: "submit",
          contentType: false,
          processData: false,
          data: data,
          //mimeType: 'multipart/form-data',
          //enctype: 'multipart/form-data',
          beforeSend: function(){
            $('.modal-content', '#myModal').html($("#loaderDiv"));
            $('#myModal').modal('show');
            $("#loaderDiv").collapse('show');
          },
          success: function(data){
            $("#loaderDiv").hide();
            $("#loaderDiv").collapse('hide');
            $('.modal-content', '#myModal').html(data);
          },
          error: function(msg){
            $('#myModal').modal('hide');
          }
        }).done(function(data) {});
        e.preventDefault();
        return false; // avoid to execute the actual submit of the form.
      });
    }
  });

});

