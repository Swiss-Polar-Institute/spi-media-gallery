function add() {
    var element = document.createElement("input");

    //Assign different attributes to the element.
    element.setAttribute("type", "text");
    element.setAttribute("name", "tag_input");
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
    let photographer = document.getElementById("photographer").value;
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

    // let medium_type_input = document.getElementById("medium_type_input").value;
    /*let tags = document.getElementById("tags").childNodes;
    console.log(tags);
    console.log(tags.length);*/

    let data = new FormData();
    data.append("file", file_input.files[0]);
    data.append("medium_type", "P");
    data.append("people", people);
    data.append("location_value", location);
    data.append("photographer", photographer);
    data.append("project", project);
    data.append("copyright", copyright);
    data.append("license", license);
    data.append("datetime_taken", datereceived);
    data.append("medium_type", medium_type);

    /*for(var i = 0; i < tags.length; i++) {
        console.log(tags[i].value);
        data.append("tag" + i, tags[i].value);
    }*/
    fetch("/api/v1/medium/", {
        method: "POST",
        body: data
    }).then(function(response){
        return response.json();
    }).then(function(data) {
        console.log(data);
    }).catch(function(error) {
        console.error("Error:", error);
    });
});
