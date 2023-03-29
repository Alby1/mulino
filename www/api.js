async function request_products() {
    const uri = `${window.location.origin}/api/products/`
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
    return await fetch(`${window.location.origin}/api/users/login?user=${user}&password=${password}`).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        return data
    })
}