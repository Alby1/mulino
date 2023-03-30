function get_seller() {
    return "{{ venditore }}"
}

function base_uri() {
    const v = get_seller()
    return `${window.location.origin}/${v}`
}

async function request_products() {
    const uri = `${base_uri()}/api/products/`
    return await fetch(uri).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

async function net_login(user, password) {
    user = encodeURI(user)
    password = encodeURI(password)
    return await fetch(`${base_uri()}/api/users/login`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"user" : user, "password" : password})
    }).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

async function net_check_session(token) {
    return await fetch(`${base_uri()}/api/users/check_session`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"token" : token})
    }).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return (data['status'] == "ok" ? true : false)
    })
}

async function net_register(user, password) {
    user = encodeURI(user)
    password = encodeURI(password)
    return await fetch(`${base_uri()}/api/users/register`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"user" : user, "password" : password})
    }).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

async function net_already_exists(user) {
    user = encodeURI(user)
    return await fetch(`${base_uri()}/api/users/already_exists?user=${user}`).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}