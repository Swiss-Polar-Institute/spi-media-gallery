$(document).ready(function () {
    function filter_projects(ID) {
        $('#page-content').text('Loading...');
        var project_id = $("#project_id").val();
        var location_id = $("#location_id").val();
        var photographer_id = $("#photographer_id").val();
        var people_id = $("#people_id").val();
        var media_type = $("#media_type").val();
        var order_by_year = $("#order_by_year").val();
        $.ajax({
            url: '/medium/',
            type: 'GET',
            data: {
                project_id: project_id,
                location_id: location_id,
                photographer_id: photographer_id,
                people_id: people_id,
                media_type: media_type,
                order_by_year: order_by_year,
            },
            success: function (response) {
                $('#page-content').html(response.html);
                $('#medium_count').html(response.count);
            }
        });
    }

    function order_by_projects(ID) {
        $('#page-content').text('Loading...');
        $.ajax({
            url: '/medium/',
            type: 'GET',
            data: {orderby: ID},
            success: function (response) {
                $('#page-content').html(response.html);
                $('#medium_count').html(response.count);
            }
        });
    }

    function order_by_projects_selection() {
        $('#page-content').text('Loading...');
        order_by = $("#order_by_id_selection").val()
        archive_type = $("#archive_id_selection").val()
        $.ajax({
            url: '/selection/',
            type: 'GET',
            data: {orderby: order_by, archive_type: archive_type},
            success: function (response) {
                $('#page-content-selection').html(response.html);
                $('#medium_count').html(response.count);
            }
        });
    }

    function order_search_all() {
        $('#page-content').text('Loading...');
        var order_by = $("#order_search_all").val();
        var search_term = $("#search_term").val();
        $.ajax({
            url: '/search_all/',
            type: 'GET',
            data: {orderby: order_by, search_term: search_term},
            success: function (response) {
                $('#page-content').html(response.html);
                $('#medium_count').html(response.count);
                $('#search_term').html(response.search_term);
            }
        });
    }

    $("#project_id").on('change', function () {
        filter_projects()
    });
    $("#location_id").on('change', function () {
        filter_projects()
    });
    $("#photographer_id").on('change', function () {
        filter_projects()
    });
    $("#people_id").on('change', function () {
        filter_projects()
    });
    $("#media_type").on('change', function () {
        filter_projects()
    });
    $("#order_by_year").on('change', function () {
        filter_projects()
    });
    $("#order_by_id").on('change', function () {
        var the_id = $(this).val();
        order_by_projects(the_id)
    });
    $("#order_by_id_selection").on('change', function () {
        order_by_projects_selection()
    });
    $("#archive_id_selection").on('change', function () {
        order_by_projects_selection()
    });
    $("#order_search_all").on('change', function () {
        order_search_all();
    });

    $("#search_load_more_id").on('click', function () {
        console.log("this is test");
        $('#page-content').text('Loading...');
        page = $("#page_id").val();
        var search_term = $("#search_term").val();
        $.ajax({
            url: '/search_all/',
            type: "get",
            data: {page: page, search_term: search_term},
            dataType: 'json',
            success: function (response) {
                $("#page-content").html(response.html);
                $("#page_id").val(response.page_number);
                $("#seach_term").val(response.search_term);
            }
        });
    });

    $(document).on("click", ".updatemediumModal_btn", function () {
        var fileId = $(this).data('file-id');
        var fileTitle = $(this).data('file-title');
        var fileDesc = $(this).data('file-desc');
        var date_archived = $(this).data('file-datearchived');
        var is_archive = $(this).data('file-archive');
        var order = $(this).data('file-order');
        console.log(date_archived);
        $(".modal-body-spi #fileid").val(fileId);
        $(".modal-body-spi #title").val(fileTitle);
        $(".modal-body-spi #description").val(fileDesc);
        $(".modal-body-spi #datearchived").val(date_archived);
        if(order != "None" ) {
            $(".modal-body-spi #order").val(order);
        }else{
            $(".modal-body-spi #order").val(0);
        }
        $(".modal-body-spi #is_archive").val(is_archive);
        if(is_archive == "True"){
            $('.modal-body-spi #is_archive').prop('checked', true);
        }else{
            $('.modal-body-spi #is_archive').prop('checked', false);
        }
    });
    $("#search_all").change(function () {
        var search_term = $(this).val();


    });
    $(document).on("change", ".is_image_of_the_week", function () {
        if ($(this).is(":checked")) {
            $(this).val("True");
        } else if ($(this).not(":checked")) {
            $(this).val("False");
        }
        var is_image_of_the_week = $(this).val();
        var mfileid = $(this).data('mfile-id');
        console.log("test");
        $.ajax({
            url: '/medium/',
            type: 'GET',
            data: {is_image_of_the_week: is_image_of_the_week, id: mfileid},
            cache: false,
            beforeSend:function(){
                if(confirm("Are you sure?")){

                    } else {
                        location.reload(true);
                        return false;
                    }
            },
            success: function (response) {
                console.log("True");
            }
        });
    });
    $(document).on("change", ".is_archive", function () {
        if ($(this).is(":checked")) {
            $(this).val("True");
        } else if ($(this).not(":checked")) {
            $(this).val("False");
        }
    });
});
