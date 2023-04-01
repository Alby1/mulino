function get_seller() {
    let ven = "/{{ venditore }}"
    if(ven == "/\{\{ venditore \}\}") return ""
    return ven
}

function base_uri() {
    const v = get_seller()
    return `${window.location.origin}${v}`
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

async function net_add_product(nome, costo, quantita, token) {
    return await fetch(`${base_uri()}/api/products/add`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"nome" : nome, "costo" : costo, "quantita" : quantita, "token" : token})
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

async function net_update_product(token, id, nome = null, costo = null, quantita = null) {
    return await fetch(`${base_uri()}/api/products/update`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"token" : token, "id" : id, "nome" : nome, "costo" : costo, "quantita" : quantita})
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

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function net_all_users(token) {
    return await fetch(`${base_uri()}/api/users?token=${token}`).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

async function net_delete_product(id, token) {
    return await fetch(`${base_uri()}/api/products/delete?token=${token}&id=${id}`).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

async function net_check_product_availability(id) {
    return await fetch(`${base_uri()}/api/products/availability?id=${id}`).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}

async function net_buy_products(cart) {
    return await fetch(`${base_uri()}/api/products/buy`, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(cart)
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

async function net_all_acquisti(token) {
    return await fetch(`${base_uri()}/api/fatture?token=${token}`).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}