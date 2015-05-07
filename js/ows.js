$('#myModal').on('loaded.bs.modal', function (e) {
  var table = $(this).find('#modal-table');
  table.DataTable({
    "bInfo" : false,
    "retrieve": true,
  //  "scrollY": "250px",
  //  "scrollCollapse": true,
    "paging": false,
  //  "jQueryUI": true,
    "bFilter": false,
    "ordering": false,
    "orderClasses": false,
  });
  var m = $(this);
  $(this).find("#modal-tab a").click(function(e){
    e.preventDefault();
    var href = $(this).attr("href");
    $(m).find(".collapse.in").collapse('hide');
    $(this).addClass('active');
    $(m).find(href).tab().show();
  });
  $(this).find('.reasons').click(function(e){
    e.preventDefault();
    var href = $(this).attr("href");
    $(m).find('#overview').tab().hide();
    $(m).find("#modal-tab a[href='#details']").tab('show');
    $(m).find(".collapse.in").collapse('hide');
    $(m).find(href).collapse('toggle');
  });
  $(this).find('.graph').click(function(e){
    e.preventDefault();
    var href = $(this).attr("href");
    $(m).find('#overview').tab().hide();
    $(m).find("#modal-tab a[href='#graph']").tab('show');
    $(m).find(".collapse.in").collapse('hide');
    $(m).find('#svgfile').svg({loadURL: href});
    $(m).find('#svgfile').collapse('toggle');
  });
  $(m).find('.package-backlink').click(function(e){
    e.preventDefault();
    var p = $(this).attr("href");
    m.removeData('bs.modal');
    $('#myModal').modal({ show: false, remote: p });
    $('#myModal').modal('show');
  });
  $(m).find('.version-backlink').click(function(e){
    e.preventDefault();
    var p = $(this).attr("href");
    var v = $(this).attr("version");
    // this does not do anything different from above. it should
    // select a specific version in the modal table
    m.removeData('bs.modal');
    $('#myModal').modal({ show: false, remote: p });
    $('#myModal').modal('show');
  });
});

// destroy the modal object when closed
$('body').on('hidden.bs.modal', '.modal', function () {
$(this).removeData('bs.modal');
});

$(document).ready(function() {
  // init the dataTables object in the main page
  $('#package-table').DataTable( {
    "stateSave": true,
    "ordering": false,
    "paging": false,
    "orderClasses": false,
  } );
  $('#summary-table-missing').DataTable( {
    "ordering": false,
    "stateSave": true,
    "paging": false,
    "orderClasses": false,
  } );
  $('#summary-table-conflicts').DataTable( {
    "ordering": false,
    "stateSave": true,
    "paging": false,
    "orderClasses": false,
  } );

  if (window.location.hash)
    document.getElementById(window.location.hash).click();

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

//  $("#myModal").on('hidden.bs.modal', function () {
//      $(this).data('bs.modal', null);
//  });

} );

