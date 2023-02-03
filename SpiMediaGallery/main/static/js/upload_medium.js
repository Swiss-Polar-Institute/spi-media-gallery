function add() {
    var element = document.createElement("input");

    //Assign different attributes to the element.
    element.setAttribute("type", "text");
    element.setAttribute("name", "tag_input[]");
    element.setAttribute("class", "form-control col-sm-6 pd-2");

    var tags = document.getElementById("tags");

    //Append the element in page (in span).
    tags.appendChild(element);
}

function validateFileExtension(fld) {
    if(!/(\.png|\.jpg|\.jpeg|\.mp4|\.mov|\.mkv|\.heic)$/i.test(fld.value)) {
        alert("Invalid file type.");
        fld.form.reset();
        fld.focus();
        return false;
    }
    const fileSize = fld.files[0].size / 1024 / 1024;
     if (fileSize > 5) {
        alert('File size exceeds 5 MiB');
        fld.form.reset();
        fld.focus();
        return false;
     }
     const file = fld.files[0];
     const  fileType = file['type'];
     const validImageTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/heic'];
     const validVideoTypes = ['video/mp4', 'video/mov', 'video/mkv'];
     if (validImageTypes.includes(fileType)) {
        document.getElementById("medium_type").value = "P";
     }
     if (validVideoTypes.includes(fileType)) {
        document.getElementById("medium_type").value = "V";
     }
     console.log(fileType);
    return true;
 }

document.getElementById("medium_form").addEventListener("submit", function(event) {
    event.preventDefault();
    let file_input = document.getElementById("file_input");
    let location = "";
    if(document.getElementById("location").value) {
       location = "Location/" + document.getElementById("location").value;
    }
    let photographer = "";
    if(document.getElementById("photographer").value) {
       photographer = document.getElementById("photographer").value;
    }
    let people = "";
    if(document.getElementById("people").value) {
        people = "People/" + document.getElementById("people").value;
    }
    let project = "";
    if(document.getElementById("project").value) {
        project = "Project/" + document.getElementById("project").value;
    }
    let copyright = document.getElementById("copyright").value;
    let license = document.getElementById("license").value;
    let datereceived = document.getElementById("datereceived").value;
    let medium_type = document.getElementById("medium_type").value;
    let tags = document.getElementsByName("tag_input[]");
    // let medium_type_input = document.getElementById("medium_type_input").value;
    //let tags = document.getElementById("tags").childNodes;
    let tags_length = tags.length;
    /*console.log(tags);
    console.log(tags.length);*/

    let data = new FormData();
    data.append("file", file_input.files[0]);
    data.append("medium_type", "P");
    data.append("people", people);
    data.append("location_value", location);
    data.append("photographer_value", photographer);
    data.append("project", project);
    data.append("copyright", copyright);
    data.append("license", license);
    data.append("datetime_taken", datereceived);
    data.append("medium_type", medium_type);
    var fields = [];
    for(var i = 0; i < tags.length; i++) {
        /*console.log(tags[i].value);*/
        fields.push(tags[i].value);
        data.append("tag" + i, tags[i].value);
    }
    let tags_m = fields.join(",");
    data.append("tags_value", tags_m);
    fetch("/api/v1/medium/", {
        method: "POST",
        body: data
    }).then(function(response){
        return response.json();
    }).then(function(data) {
        console.log(data);
        document.getElementById("medium_form").reset();
        document.getElementById('close_mu').click();
        document.getElementById('medium_success_msg').style.display="block";
    }).catch(function(error) {
        console.error("Error:", error);
        document.getElementById('medium_error_msg').style.display="block";
    });
});
