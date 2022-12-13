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

document.getElementById("medium_form").addEventListener("submit", function(event) {
    event.preventDefault();
    let file_input = document.getElementById("file_input");
    // let medium_type_input = document.getElementById("medium_type_input").value;
    let tags = document.getElementById("tags").childNodes;
    console.log(tags);
    console.log(tags.length);

    let data = new FormData();
    data.append("file", file_input.files[0]);
    data.append("medium_type", "P");

    for(var i = 0; i < tags.length; i++) {
        console.log(tags[i].value);
        data.append("tag" + i, tags[i].value);
    }
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
