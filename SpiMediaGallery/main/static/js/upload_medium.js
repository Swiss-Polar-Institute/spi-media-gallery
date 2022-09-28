document.getElementById('medium_form').addEventListener('submit', function(event) {
    event.preventDefault();
    let file_input = document.getElementById('file_input');
    let medium_type_input = document.getElementById('medium_type_input').value;

    let data = new FormData();
    data.append('file', file_input.files[0]);
    data.append('medium_type', medium_type_input);

    fetch('/api/v1/medium/', {
        method: 'POST',
        body: data
    }).then(function(response){
        return response.json();
    }).then(function(data) {
        console.log(data);
    }).catch(function(error) {
        console.error('Error:', error);
    });
});
