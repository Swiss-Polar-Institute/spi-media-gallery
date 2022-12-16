$(document).ready(function() {
    function filter_projects(ID){
        $('#page-content').text('Loading...');
        var project_id = $("#project_id").val();
        var location_id = $("#location_id").val();
        var photographer_id = $("#photographer_id").val();
        var people_id = $("#people_id").val();
        $.ajax({
          url: '/medium/',
          type: 'GET',
          data: {project_id: project_id, location_id: location_id, photographer_id: photographer_id, people_id: people_id },
          success: function(response) {
              $('#page-content').html(response.html);
              $('#medium_count').html(response.count);
          }
        });
    }
    function order_by_projects(ID){
        $('#page-content').text('Loading...');
        $.ajax({
          url: '/medium/',
          type: 'GET',
          data: {orderby: ID},
          success: function(response) {
            $('#page-content').html(response.html);
            $('#medium_count').html(response.count);
          }
        });
    }
    $("#project_id").on('change', function(){
        filter_projects()
     });
    $("#location_id").on('change', function(){
        filter_projects()
     });
    $("#photographer_id").on('change', function(){
        filter_projects()
     });
    $("#people_id").on('change', function(){
        filter_projects()
     });
    $("#order_by_id").on('change', function(){
         var the_id = $(this).val();
         order_by_projects(the_id)
     });

    $("#load_more_id").on('click', function(){
        $('#page-content').text('Loading...');
        page = $("#page_id").val();
        var project_id = $("#project_id").val();
        var location_id = $("#location_id").val();
        var photographer_id = $("#photographer_id").val();
        var people_id = $("#people_id").val();
        $.ajax({
            url: '/medium/',
            type: "get",
            data: {page: page, project_id: project_id, location_id: location_id, photographer_id: photographer_id, people_id: people_id },
            dataType: 'json',
            success: function (response) {
                $("#page-content").html(response.html);
                $("#page_id").val(response.page_number);
            }
        });
    });
});