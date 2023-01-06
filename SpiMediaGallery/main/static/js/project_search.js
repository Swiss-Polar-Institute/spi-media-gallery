$(document).ready(function () {
    function filter_projects(ID) {
        $('#page-content').text('Loading...');
        var project_id = $("#project_id").val();
        var location_id = $("#location_id").val();
        var photographer_id = $("#photographer_id").val();
        var people_id = $("#people_id").val();
        $.ajax({
            url: '/medium/',
            type: 'GET',
            data: {
                project_id: project_id,
                location_id: location_id,
                photographer_id: photographer_id,
                people_id: people_id
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

    function order_by_projects_selection(ID) {
        $('#page-content').text('Loading...');
        $.ajax({
            url: '/selection/',
            type: 'GET',
            data: {orderby: ID},
            success: function (response) {
                $('#page-content').html(response.html);
                $('#medium_count').html(response.count);
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
    $("#order_by_id").on('change', function () {
        var the_id = $(this).val();
        order_by_projects(the_id)
    });

    $("#order_by_id_selection").on('change', function () {
        var the_id = $(this).val();
        order_by_projects_selection(the_id)
    });

    $("#load_more_id").on('click', function () {
        $('#page-content').text('Loading...');
        page = $("#page_id").val();
        var project_id = $("#project_id").val();
        var location_id = $("#location_id").val();
        var photographer_id = $("#photographer_id").val();
        var people_id = $("#people_id").val();
        $.ajax({
            url: '/medium/',
            type: "get",
            data: {
                page: page,
                project_id: project_id,
                location_id: location_id,
                photographer_id: photographer_id,
                people_id: people_id
            },
            dataType: 'json',
            success: function (response) {
                $("#page-content").html(response.html);
                $("#page_id").val(response.page_number);
            }
        });
    });

    $("#load_more_id_selection").on('click', function () {
        $('#page-content').text('Loading...');
        page = $("#page_id").val();
        var project_id = $("#project_id").val();
        var location_id = $("#location_id").val();
        var photographer_id = $("#photographer_id").val();
        var people_id = $("#people_id").val();
        $.ajax({
            url: '/selection/',
            type: "get",
            data: {
                page: page,
                project_id: project_id,
                location_id: location_id,
                photographer_id: photographer_id,
                people_id: people_id
            },
            dataType: 'json',
            success: function (response) {
                $("#page-content").html(response.html);
                $("#page_id").val(response.page_number);
            }
        });
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
        $(".modal-body-spi #fileid").val(fileId);
        $(".modal-body-spi #title").val(fileTitle);
        $(".modal-body-spi #description").val(fileDesc);
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
            success: function (response) {
                console.log("True");
            }
        });
    });
});